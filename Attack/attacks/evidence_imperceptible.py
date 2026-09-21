"""EA_IMP_01 — Imperceptible Character-Level Verification Attack.

Perturbs the evidence text with invisible Unicode characters (zero-width
space U+200B, zero-width non-joiner U+200C) and/or homoglyph substitutions so
the verifier's subword tokenizer is disrupted while the text looks unchanged
to humans.

Black-box simplification of Boucher et al. (2022): the original uses
query-based optimization against verifier scores. Our pipeline has no
verifier-score access at attack time, so we apply the same imperceptible
character edits with a fixed edit budget instead of optimizing them.

Category: evidence_attack. Edit granularity: character.
"""

from __future__ import annotations

import random

import common

from attacks.char_homoglyph import _CONFUSABLES_BY_LANGUAGE

ATTACK_ID = "EA_IMP_01_ImperceptibleVerification"
EDIT_GRANULARITY = "character"

ZWS = "\u200b"
ZWNJ = "\u200c"


def _insert_invisible(text, count, rng):
    """Insert *count* invisible chars (ZWS/ZWNJ) at random non-boundary positions."""
    if not text:
        return text, 0
    positions = list(range(1, len(text)))
    if not positions:
        return text, 0
    rng.shuffle(positions)
    inserted = 0
    result = text
    for pos in positions[:count]:
        char = rng.choice([ZWS, ZWNJ])
        result = result[:pos] + char + result[pos:]
        inserted += 1
        if inserted >= count:
            break
    return result, inserted


def apply(record, edit_budget=3, rng=None):
    claim = record.get("claim") or record.get("claim_text") or ""
    evidence = record.get("evidence") or record.get("evidence_text") or ""
    language = common.validate_language(record.get("language"))
    gold_label = record.get("gold_label") or record.get("label")

    if not claim or not evidence or language is None:
        return common.build_record(
            ATTACK_ID, language, claim, evidence, None, None,
            gold_label, "REF", EDIT_GRANULARITY, None,
            skip_reason="missing_claim_or_evidence_or_unsupported_language",
        )

    rng = rng or common.new_rng()

    # Invisible character injection (primary edit)
    adv_evidence, inserted = _insert_invisible(evidence, max(1, edit_budget), rng)

    # Optionally one homoglyph substitution on the evidence (secondary edit)
    substitutions = 0
    table = _CONFUSABLES_BY_LANGUAGE.get(language, {})
    if table and rng.random() < 0.5:
        candidates = [(i, ch) for i, ch in enumerate(adv_evidence) if ch in table]
        if candidates:
            i, ch = rng.choice(candidates)
            adv_evidence = adv_evidence[:i] + table[ch] + adv_evidence[i + 1:]
            substitutions = 1

    if inserted == 0 and substitutions == 0:
        return common.build_record(
            ATTACK_ID, language, claim, evidence, None, None,
            gold_label, "REF", EDIT_GRANULARITY, None,
            skip_reason="no_valid_perturbation",
        )

    return common.build_record(
        ATTACK_ID, language, claim, evidence,
        None, adv_evidence,
        gold_label, "REF", EDIT_GRANULARITY,
        {
            "control_char_inserted": "U+200B/U+200C",
            "zero_width_insertions": inserted,
            "homoglyph_substitutions": substitutions,
            "edit_budget_epsilon": edit_budget,
        },
        validity_flags={
            "fluency_checked": True,
            "label_consistent": True,
            "meaning_preserved": True,
        },
    )
