"""Runner for the 8 LLM-based attacks.

Generates attacked text for every row and writes per-attack CSVs, a combined
CSV, and a summary JSON — same output contract as main.py. Generation
results are cached to <output>/.cache/ so re-runs never regenerate (they
only re-read cache), which matters because LLM calls cost money.

Fact Mixing needs two evidence sources per row; we pair each row with a
same-domain neighbor (highest token overlap when domains are missing).

Usage:
    python main_llm.py --input data.csv --output out_dir [--seed 42]
                       [--mock] [--max-rows N]

Env config (ignored in --mock mode):
    LLM_BASE_URL, LLM_API_KEY, LLM_MODEL
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib
import json
import os
import random
import sys
from collections import Counter, OrderedDict

import common
from llm_client import LLMClient

LLM_ATTACK_MODULES = OrderedDict([
    ("CA_07_AdvTrigger", "llm_attacks.adv_trigger"),
    ("CA_06_FactMixing", "llm_attacks.fact_mixing"),
    ("CA_16_Colloquial", "llm_attacks.colloquial"),
    ("EA_CLAIMREWRITE_01_ClaimRewrite", "llm_attacks.claim_rewrite"),
    ("EA_CTXREP_01_ContextualizedReplace", "llm_attacks.contextualized_replace"),
    ("EA_ADVADD_01_AdvAdd", "llm_attacks.adv_add"),
    ("EA_FACT2FICT_01_Fact2Fiction", "llm_attacks.fact2fiction"),
    ("EA_IMPRET_01_ImperceptibleRetrieval", "llm_attacks.imperceptible_ret"),
])

OUTPUT_FIELDS = [
    "row_id", "attack_id", "language",
    "original_claim", "original_evidence",
    "adversarial_claim", "adversarial_evidence",
    "gold_label", "target_label", "edit_granularity",
    "technique_params", "validity_flags", "skip_reason",
    "injected_evidence_workaround",
]

_CACHE_MISSES = Counter()


def _get(row, *aliases):
    for alias in aliases:
        if alias in row and row[alias] not in (None, ""):
            return row[alias]
    return ""


def parse_args():
    parser = argparse.ArgumentParser(description="Run all 8 LLM-based attacks.")
    parser.add_argument("--input", required=True, help="Input CSV file")
    parser.add_argument("--output", default="output_llm", help="Output directory")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--mock", action="store_true",
                        help="Use mock LLM responses (offline testing, no API key)")
    parser.add_argument("--max-rows", type=int, default=None, help="Row limit for testing")
    parser.add_argument("--no-cache", action="store_true", help="Ignore cache and regenerate")
    return parser.parse_args()


def load_rows(path):
    if path.lower().endswith((".xlsx", ".xlsm")):
        return common.load_dataset(path)
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = []
        for i, row in enumerate(reader):
            rows.append({
                "row_id": i,
                "claim": _get(row, "claim", "claim_text", "Claim", "claim1"),
                "evidence": _get(row, "evidence", "evidence_text", "Evidence"),
                "label": _get(row, "label", "gold_label", "Label", "goldLabel").upper(),
                "language": _get(row, "language", "lang", "Language") or "hi",
                "domain": _get(row, "domain", "Domain"),
            })
    return rows


def _overlap(a, b):
    ta, tb = set(a.split()), set(b.split())
    if not ta or not tb:
        return 0
    return len(ta & tb) / max(len(ta), len(tb))


def pair_neighbors(rows, rng):
    """Attach a same-domain neighbor's evidence to each row (for Fact Mixing)."""
    neighbors = [""] * len(rows)
    for i, row in enumerate(rows):
        candidates = [j for j in range(len(rows)) if j != i]
        if row["domain"]:
            same_domain = [j for j in candidates if rows[j]["domain"] == row["domain"]]
            if same_domain:
                candidates = same_domain
        if not candidates:
            continue
        best = max(candidates, key=lambda j: _overlap(row["evidence"], rows[j]["evidence"]))
        neighbors[i] = rows[best]["evidence"]
    for row, n in zip(rows, neighbors):
        row["neighbor_evidence"] = n
    return rows


def cache_path(output, attack_id, row_id, seed):
    digest = hashlib.md5(f"{seed}:{row_id}:{attack_id}".encode()).hexdigest()
    return os.path.join(output, ".cache", f"{attack_id}_{row_id}_{digest}.json")


def load_cache(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def save_cache(path, record):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False)
    for attempt in range(5):
        try:
            os.replace(tmp, path)
            break
        except OSError:
            import time
            time.sleep(0.1 * (attempt + 1))
            if attempt == 4:
                # Direct write fallback if atomic replace fails repeatedly
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(record, f, ensure_ascii=False)
                if os.path.exists(tmp):
                    try:
                        os.remove(tmp)
                    except OSError:
                        pass



def main():
    args = parse_args()
    random.seed(args.seed)
    os.makedirs(args.output, exist_ok=True)

    rows = load_rows(args.input)
    if args.max_rows is not None:
        rows = rows[: args.max_rows]
    pair_neighbors(rows, random.Random(args.seed))

    client = LLMClient(mock=args.mock)
    if not args.mock:
        print(f"[llm] provider={client.base_url} model={client.model}")

    modules = []
    for attack_id, module_name in LLM_ATTACK_MODULES.items():
        try:
            modules.append((attack_id, importlib.import_module(module_name)))
        except ImportError as exc:
            print(f"[WARN] could not import {module_name}: {exc}", file=sys.stderr)

    stats = Counter()
    skipped_by_reason = Counter()
    attack_outputs = {attack_id: [] for attack_id in LLM_ATTACK_MODULES}

    for row in rows:
        if not row["claim"]:
            print(f"[WARN] row {row['row_id']}: empty claim, skipping row entirely")
            continue

        for attack_id, module in modules:
            cpath = cache_path(args.output, attack_id, row["row_id"], args.seed)
            record = None if args.no_cache else load_cache(cpath)
            if record is None:
                _CACHE_MISSES[attack_id] += 1
                rng = random.Random(f"{args.seed}:{row['row_id']}:{attack_id}")
                record = module.apply(dict(row), client, rng=rng)
                save_cache(cpath, record)
            else:
                record.pop("_cached", None)

            out = {field: record.get(field) for field in OUTPUT_FIELDS}
            out["row_id"] = row["row_id"]
            if record.get("skip_reason"):
                stats["skipped"] += 1
                skipped_by_reason[record["skip_reason"]] += 1
            else:
                stats["applied"] += 1
            attack_outputs[attack_id].append(out)

    # 1) Per-attack CSV
    for attack_id, outputs in attack_outputs.items():
        path = os.path.join(args.output, f"{attack_id}.csv")
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS)
            writer.writeheader()
            for out in outputs:
                writer.writerow({
                    k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v)
                    for k, v in out.items()
                })

    # 2) Combined CSV
    combined_path = os.path.join(args.output, "attacked_rows_all.csv")
    with open(combined_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        for outputs in attack_outputs.values():
            for out in outputs:
                writer.writerow({
                    k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v)
                    for k, v in out.items()
                })

    # 3) Summary JSON
    summary = {
        "input_rows": len(rows),
        "attacks": len(modules),
        "seed": args.seed,
        "mock_mode": args.mock,
        "stats": {"applied": stats["applied"], "skipped": stats["skipped"]},
        "per_attack": {
            attack_id: {
                "applied": sum(1 for o in attack_outputs[attack_id] if not o["skip_reason"]),
                "skipped": sum(1 for o in attack_outputs[attack_id] if o["skip_reason"]),
            }
            for attack_id in LLM_ATTACK_MODULES
        },
        "skip_reasons": dict(skipped_by_reason),
        "cache_misses": dict(_CACHE_MISSES),
    }
    with open(os.path.join(args.output, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"Rows: {len(rows)} | Applied: {stats['applied']} | Skipped: {stats['skipped']}")
    for attack_id in LLM_ATTACK_MODULES:
        applied = summary["per_attack"][attack_id]["applied"]
        skipped = summary["per_attack"][attack_id]["skipped"]
        print(f"  {attack_id}: {applied} applied, {skipped} skipped")
    print(f"\nOutputs written to {args.output}/")


if __name__ == "__main__":
    main()
