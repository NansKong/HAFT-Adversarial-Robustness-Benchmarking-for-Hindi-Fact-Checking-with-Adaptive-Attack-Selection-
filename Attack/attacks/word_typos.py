"""CA_WORD_04 — Typos.

Replaces one word of the claim with a common misspelling from a curated
typo dictionary (default: 1 substitution). Words without a dictionary entry
are left untouched.

Ref: FactEval benchmark (Mamta & Cocarascu, 2025).
"""

from __future__ import annotations

import common

from resources.hi_typos import HINDI_TYPO_DICTIONARY

ATTACK_ID = "CA_WORD_04_Typos"
EDIT_GRANULARITY = "word"

_TYPO_DICTIONARIES = {
    "hi": HINDI_TYPO_DICTIONARY,
}


def apply(record, typo_budget=1, rng=None):
    claim = record.get("claim") or record.get("claim_text") or ""
    language = common.validate_language(record.get("language"))
    gold_label = record.get("gold_label") or record.get("label")

    if not claim or language is None:
        return common.build_record(
            ATTACK_ID, language, claim, record.get("evidence"), None, None,
            gold_label, "same_as_gold", EDIT_GRANULARITY, None,
            skip_reason="missing_claim_or_unsupported_language",
        )

    dictionary = _TYPO_DICTIONARIES.get(language)
    if not dictionary:
        return common.build_record(
            ATTACK_ID, language, claim, record.get("evidence"), None, None,
            gold_label, "same_as_gold", EDIT_GRANULARITY, None,
            skip_reason=f"missing_typo_dictionary_for_{language}",
        )

    rng = rng or common.new_rng()
    tokens, _ = common.tokenize(claim)
    result_tokens = list(tokens)
    applied = 0
    original_word = None
    typo_variant = None

    candidates = []
    for idx, tok in enumerate(tokens):
        core, _, _ = common._strip_trailing_punct(tok)
        if core in dictionary:
            candidates.append((idx, core))
    if not candidates:
        return common.build_record(
            ATTACK_ID, language, claim, record.get("evidence"), None, None,
            gold_label, "same_as_gold", EDIT_GRANULARITY, None,
            skip_reason="no_applicable_words",
        )

    rng.shuffle(candidates)
    for idx, core in candidates:
        variants = dictionary[core]
        variant = rng.choice(variants)
        _, lead, trail = common._strip_trailing_punct(tokens[idx])
        result_tokens[idx] = lead + variant + trail
        applied += 1
        original_word = core
        typo_variant = variant
        if applied >= typo_budget:
            break

    adversarial_claim = " ".join(result_tokens)
    return common.build_record(
        ATTACK_ID, language, claim, record.get("evidence"),
        adversarial_claim, None,
        gold_label, "same_as_gold", EDIT_GRANULARITY,
        {
            "substitution_type": "typo_dictionary",
            "original_word": original_word,
            "typo_variant": typo_variant,
            "typos_applied": applied,
        },
    )
