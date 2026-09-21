"""Phase A runner: baseline pass + full verify/judge over all attacked rows.

Flow:
  1. Baseline pass — verify every row's CLEAN (claim, evidence). A row where
     the clean verdict != gold label is a baseline failure and is excluded
     from all attack success rates.
  2. Attack pass — for each attacked CSV produced by the attack engines,
     verify (honoring injected_evidence_workaround) then judge; 20 workers.
  3. Outputs — per-attack results CSV + summary.json (baseline accuracy,
     raw/gated ASR, skip reasons).

Checkpoint cache: every (attack_id, row_id) result is cached, so a crashed
run resumes without re-billing.

Usage:
    python run_verification.py --rule-dir output/... --llm-dir output_llm/...
        --output results_dir [--mock] [--max-rows N] [--workers 20]
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

import common
import judge
import verifier
from llm_client import LLMClient

CACHE_DIR = ".verify_cache"

OUTPUT_FIELDS = [
    "row_id", "attack_id",
    "original_claim", "original_evidence",
    "adversarial_claim", "adversarial_evidence",
    "gold_label", "verdict", "verdict_raw",
    "flipped", "reason",
    "fluency", "meaning_preserved", "excluded", "gate_reason",
]


def _sanitize(value):
    """Flatten newlines/tabs so CSV rows stay single-line."""
    if isinstance(value, str):
        return " ".join(value.split())
    return value


def parse_args():
    p = argparse.ArgumentParser(description="Phase A: verify + judge all attacked rows.")
    p.add_argument("--rule-dir", default="output", help="Dir with rule-based attack CSVs")
    p.add_argument("--llm-dir", default="output_llm", help="Dir with LLM attack CSVs")
    p.add_argument("--input", required=True, help="Original dataset CSV")
    p.add_argument("--output", default="results", help="Results directory")
    p.add_argument("--mock", action="store_true", help="Mock LLM (offline test)")
    p.add_argument("--max-rows", type=int, default=None, help="Row limit for testing")
    p.add_argument("--workers", type=int, default=20, help="Concurrent API calls")
    p.add_argument("--no-cache", action="store_true", help="Ignore checkpoint cache")
    return p.parse_args()


def load_rows(path):
    if path.lower().endswith((".xlsx", ".xlsm")):
        return common.load_dataset(path)
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = []
        for i, row in enumerate(reader):
            rows.append({
                "row_id": i,
                "claim": (row.get("claim") or row.get("claim_text") or "").strip(),
                "evidence": (row.get("evidence") or row.get("evidence_text") or "").strip(),
                "label": (row.get("label") or row.get("gold_label") or "").upper(),
            })
    return rows


def load_attacked_csv(path):
    """Return list of record dicts from an attacked-rows CSV (JSON cols parsed)."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        records = []
        for row in reader:
            for field in ("technique_params", "validity_flags"):
                if field in row and row[field]:
                    try:
                        row[field] = json.loads(row[field])
                    except json.JSONDecodeError:
                        pass
            records.append(row)
    return records


def attacked_files_from_dir(d):
    return [os.path.join(d, f) for f in sorted(os.listdir(d))
            if f.endswith(".csv") and f != "attacked_rows_all.csv"]


# -- mock helpers ----------------------------------------------------------

def mock_verifier_fn(prompt, system=None):
    """Deterministic mock: returns REF for attacked rows, gold for clean.

    Clean prompts contain 'Evidence: "..."\n\nLabels:' with the original
    evidence; attacked prompts contain the separator 'एक अन्य स्रोत'.
    """
    if "एक अन्य स्रोत" in prompt:
        return "REF"
    return "SUP"


def mock_judge_fn(prompt, system=None):
    return '{"fluency": 5, "meaning_preserved": true}'


# -- cache -----------------------------------------------------------------

def _cache_path(output_dir, key):
    return os.path.join(output_dir, CACHE_DIR, key + ".json")


def _cache_get(output_dir, key):
    path = _cache_path(output_dir, key)
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _cache_put(output_dir, key, value):
    path = _cache_path(output_dir, key)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False)
    os.replace(tmp, path)


# -- baseline --------------------------------------------------------------

def run_baseline(rows, client, output_dir, no_cache, workers):
    print(f"[baseline] verifying {len(rows)} clean rows...")
    results = {}
    failures = set()

    def work(row):
        key = f"baseline_{row['row_id']}"
        cached = None if no_cache else _cache_get(output_dir, key)
        if cached is not None:
            return row["row_id"], cached
        label, raw = verifier.verify(row["claim"], row["evidence"], client)
        entry = {"verdict": label, "raw": raw}
        _cache_put(output_dir, key, entry)
        return row["row_id"], entry

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(work, r) for r in rows]
        for fut in as_completed(futures):
            row_id, entry = fut.result()
            results[row_id] = entry
            if entry["verdict"] != rows[row_id]["label"]:
                failures.add(row_id)

    correct = sum(1 for rid, e in results.items()
                  if e["verdict"] == rows[rid]["label"])
    accuracy = correct / len(rows) if rows else 0.0
    print(f"[baseline] accuracy={accuracy:.2%} "
          f"({correct}/{len(rows)}), baseline failures={len(failures)}")
    return results, failures


# -- attack pass -----------------------------------------------------------

def run_attacks(attack_files, rows_by_id, baseline_failures, client,
                judge_client, output_dir, no_cache, workers):
    all_results = defaultdict(list)

    for path in attack_files:
        attack_id = os.path.splitext(os.path.basename(path))[0]
        records = load_attacked_csv(path)
        print(f"[attack] {attack_id}: {len(records)} rows")

        def work(rec):
            row_id = int(rec["row_id"])
            key = f"{attack_id}_{row_id}"
            cached = None if no_cache else _cache_get(output_dir, key)
            if cached is not None:
                return row_id, cached

            row = rows_by_id.get(row_id)
            if row is None:
                return row_id, {"reason": "missing_source_row", "skip": True}

            adv_claim = (rec.get("adversarial_claim") or "").strip()
            adv_evidence = (rec.get("adversarial_evidence") or "").strip()
            injected = rec.get("injected_evidence_workaround") in ("True", "true", True)

            if rec.get("skip_reason"):
                return row_id, {"reason": "attack_skipped", "skip": True}

            # attacked text: claim attacks feed claim, evidence attacks feed evidence
            if adv_claim:
                label, raw = verifier.verify(
                    adv_claim, row["evidence"], client,
                    injected=injected, injected_evidence=adv_evidence)
            elif adv_evidence:
                if injected:
                    # workaround: original + fabricated evidence together
                    label, raw = verifier.verify(
                        row["claim"], row["evidence"], client,
                        injected=True, injected_evidence=adv_evidence)
                else:
                    label, raw = verifier.verify(
                        row["claim"], adv_evidence, client)
            else:
                return row_id, {"reason": "no_attacked_text", "skip": True}

            baseline_failed = row_id in baseline_failures
            flipped, reason = judge.decide(attack_id, row["label"], label,
                                           baseline_failed=baseline_failed)

            # LLM quality gate: run judge only if the attack actually flipped the verdict
            if flipped:
                attacked_text = adv_claim or adv_evidence
                fluency, meaning = judge.judge_quality(judge_client, row["claim"], attacked_text)
                excluded, gate_reason = judge.apply_gate(attack_id, fluency, meaning)
            else:
                fluency, meaning = None, None
                excluded, gate_reason = False, None

            result = {
                "verdict": label, "verdict_raw": raw,
                "flipped": flipped, "reason": reason,
                "fluency": fluency, "meaning_preserved": meaning,
                "excluded": excluded, "gate_reason": gate_reason,
            }
            _cache_put(output_dir, key, result)
            return row_id, result

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(work, rec) for rec in records]
            for fut in as_completed(futures):
                row_id, result = fut.result()
                all_results[attack_id].append((row_id, result))

    return all_results


# -- outputs ---------------------------------------------------------------

def write_outputs(all_results, rows_by_id, attack_files, baseline_failures,
                  output_dir, baseline_accuracy):
    os.makedirs(output_dir, exist_ok=True)
    summary = {"baseline_accuracy": baseline_accuracy,
               "baseline_failures": len(baseline_failures),
               "per_attack": {}}

    for path in attack_files:
        attack_id = os.path.splitext(os.path.basename(path))[0]
        records = load_attacked_csv(path)
        results = dict(all_results.get(attack_id, []))

        asr = judge.compute_asr([
            {
                "flipped": r.get("flipped", False),
                "reason": r.get("reason"),
                "excluded": r.get("excluded", False),
                "skip": r.get("skip", False),
            }
            for r in results.values()
        ])
        summary["per_attack"][attack_id] = asr

        out_path = os.path.join(output_dir, f"{attack_id}_results.csv")
        with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS)
            writer.writeheader()
            for rec in records:
                rid = int(rec["row_id"])
                row = rows_by_id.get(rid, {})
                res = results.get(rid, {})
                writer.writerow({
                    "row_id": rid,
                    "attack_id": attack_id,
                    "original_claim": _sanitize(row.get("claim", "")),
                    "original_evidence": _sanitize(row.get("evidence", "")),
                    "adversarial_claim": _sanitize(rec.get("adversarial_claim") or ""),
                    "adversarial_evidence": _sanitize(rec.get("adversarial_evidence") or ""),
                    "gold_label": row.get("label", ""),
                    "verdict": res.get("verdict") or "",
                    "verdict_raw": _sanitize(res.get("verdict_raw") or ""),
                    "flipped": res.get("flipped", ""),
                    "reason": res.get("reason", ""),
                    "fluency": res.get("fluency", ""),
                    "meaning_preserved": res.get("meaning_preserved", ""),
                    "excluded": res.get("excluded", ""),
                    "gate_reason": res.get("gate_reason") or "",
                })

    with open(os.path.join(output_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\n[results] baseline accuracy: {baseline_accuracy:.2%}")
    for attack_id, asr in summary["per_attack"].items():
        raw = asr["raw_asr"]
        gated = asr["gated_asr"]
        raw_s = f"{raw:.2%}" if raw is not None else "n/a"
        gated_s = f"{gated:.2%}" if gated is not None else "n/a"
        print(f"  {attack_id}: raw ASR {raw_s} | gated ASR {gated_s} "
              f"(n={asr['gated_eligible']})")


def main():
    args = parse_args()
    os.makedirs(args.output, exist_ok=True)

    rows = load_rows(args.input)
    if args.max_rows is not None:
        rows = rows[: args.max_rows]
    rows_by_id = {r["row_id"]: r for r in rows}

    client = verifier.make_client(mock=args.mock, mock_fn=mock_verifier_fn)
    judge_client = LLMClient(mock=args.mock, mock_fn=mock_judge_fn,
                             log_path="judge_audit.jsonl")

    baseline_results, baseline_failures = run_baseline(
        rows, client, args.output, args.no_cache, args.workers)
    baseline_accuracy = sum(
        1 for rid, e in baseline_results.items()
        if e["verdict"] == rows_by_id[rid]["label"]) / len(rows) if rows else 0.0

    attack_files = []
    for d in (args.rule_dir, args.llm_dir):
        if d and os.path.isdir(d):
            attack_files.extend(attacked_files_from_dir(d))
    if not attack_files:
        print("[error] no attack CSVs found in rule-dir/llm-dir", file=sys.stderr)
        sys.exit(1)

    all_results = run_attacks(attack_files, rows_by_id, baseline_failures,
                              client, judge_client, args.output,
                              args.no_cache, args.workers)
    write_outputs(all_results, rows_by_id, attack_files, baseline_failures,
                  args.output, baseline_accuracy)
    print(f"\n[results] written to {args.output}/")


if __name__ == "__main__":
    main()
