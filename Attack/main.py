"""Main runner for the rule-based attack engine.

Applies all 14 rule-based attacks to every row of the input CSV and writes
two artifacts:

  1. attacked rows CSV   — one row per (input row x attack), with the
                           adversarial text and all attack metadata
  2. results JSON        — per-attack applied/skipped counts

Input CSV columns (auto-detected aliases):
    claim | claim_text        claim (required)
    evidence | evidence_text  evidence (optional; needed by evidence attacks)
    label | gold_label        SUP / REF / NEI (optional)
    language                 ISO code, default 'hi' (optional)

Usage:
    python main.py --input data.csv --output out_dir [--seed 42]
"""

from __future__ import annotations

import argparse
import csv
import importlib
import json
import os
import random
import sys
from collections import Counter, OrderedDict

import common

ATTACK_MODULES = OrderedDict([
    ("CA_CHAR_01_CharacterSwapping", "attacks.char_swapping"),
    ("CA_CHAR_02_CharacterRepetition", "attacks.char_repetition"),
    ("CA_CHAR_03_CharacterInsertion", "attacks.char_insertion"),
    ("CA_CHAR_04_CharacterDeletion", "attacks.char_deletion"),
    ("CA_CHAR_05_HomoglyphPerturbation", "attacks.char_homoglyph"),
    ("CA_WORD_02_EntityDisambiguation", "attacks.word_entity_disambiguation"),
    ("CA_WORD_03_Jumbling", "attacks.word_jumbling"),
    ("CA_WORD_04_Typos", "attacks.word_typos"),
    ("CA_WORD_08_LexicalSubstitution", "attacks.word_lexical_substitution"),
    ("CA_WORD_12_Synonyms", "attacks.word_synonyms"),
    ("CA_WORD_13_PhoneticPerturbation", "attacks.word_phonetic"),
    ("CA_03_LexicallyInformed", "attacks.lexically_informed"),
    ("EA_IMP_01_ImperceptibleVerification", "attacks.evidence_imperceptible"),
    ("EA_OMITOMISSION_01_OmissionGeneration", "attacks.evidence_omission"),
])

OUTPUT_FIELDS = [
    "row_id", "attack_id", "language",
    "original_claim", "original_evidence",
    "adversarial_claim", "adversarial_evidence",
    "gold_label", "target_label", "edit_granularity",
    "technique_params", "validity_flags", "skip_reason",
]


def _get(row, *aliases):
    for alias in aliases:
        if alias in row and row[alias] not in (None, ""):
            return row[alias]
    return ""


def parse_args():
    parser = argparse.ArgumentParser(description="Run all 14 rule-based attacks.")
    parser.add_argument("--input", required=True, help="Input CSV file")
    parser.add_argument("--output", default="output", help="Output directory")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--max-rows", type=int, default=None,
                        help="Limit number of input rows (for testing)")
    return parser.parse_args()


def load_rows(path):
    if path.lower().endswith((".xlsx", ".xlsm")):
        return common.load_dataset(path)
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = []
        for i, row in enumerate(reader):
            normalized = {
                "row_id": i,
                "claim": _get(row, "claim", "claim_text", "Claim", "claim1"),
                "evidence": _get(row, "evidence", "evidence_text", "Evidence"),
                "label": _get(row, "label", "gold_label", "Label", "goldLabel").upper(),
                "language": _get(row, "language", "lang", "Language"),
                "domain": _get(row, "domain", "Domain"),
            }
            rows.append(normalized)
    return rows


def main():
    args = parse_args()
    random.seed(args.seed)

    os.makedirs(args.output, exist_ok=True)
    rows = load_rows(args.input)
    if args.max_rows is not None:
        rows = rows[: args.max_rows]

    modules = []
    for attack_id, module_name in ATTACK_MODULES.items():
        try:
            modules.append((attack_id, importlib.import_module(module_name)))
        except ImportError as exc:
            print(f"[WARN] could not import {module_name}: {exc}", file=sys.stderr)

    stats = Counter()
    skipped_by_reason = Counter()
    attack_outputs = {attack_id: [] for attack_id in ATTACK_MODULES}

    for row in rows:
        claim = row["claim"]
        evidence = row["evidence"]
        language = row["language"] or "hi"
        label = row["label"] or ""

        if not claim:
            print(f"[WARN] row {row['row_id']}: empty claim, skipping row entirely")
            continue

        for attack_id, module in modules:
            rng = random.Random(f"{args.seed}:{row['row_id']}:{attack_id}")
            record = module.apply(dict(row), rng=rng)
            out = {field: record.get(field) for field in OUTPUT_FIELDS}
            out["row_id"] = row["row_id"]
            if record.get("skip_reason"):
                stats["skipped"] += 1
                skipped_by_reason[record["skip_reason"]] += 1
            else:
                stats["applied"] += 1
            attack_outputs[attack_id].append(out)

    # 1) Per-attack CSV: <attack_id>.csv in the output dir
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

    # 2) Combined CSV: all attacks, all rows
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
        "stats": {
            "applied": stats["applied"],
            "skipped": stats["skipped"],
        },
        "per_attack": {
            attack_id: {
                "applied": sum(
                    1 for o in attack_outputs[attack_id] if not o["skip_reason"]),
                "skipped": sum(
                    1 for o in attack_outputs[attack_id] if o["skip_reason"]),
            }
            for attack_id in ATTACK_MODULES
        },
        "skip_reasons": dict(skipped_by_reason),
    }
    with open(os.path.join(args.output, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"Rows: {len(rows)} | Applied: {stats['applied']} | Skipped: {stats['skipped']}")
    for attack_id in ATTACK_MODULES:
        applied = summary["per_attack"][attack_id]["applied"]
        skipped = summary["per_attack"][attack_id]["skipped"]
        print(f"  {attack_id}: {applied} applied, {skipped} skipped")
    print(f"\nOutputs written to {args.output}/")
    print(f"  - per-attack CSVs, combined CSV, summary.json")


if __name__ == "__main__":
    main()
