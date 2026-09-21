"""CA_WORD_13 — Phonetic Perturbation.

Replaces one word of the claim with a phonetically similar but differently
spelled variant from a curated phonetic dictionary (default: 1 substitution).

Ref: FactEval benchmark (Mamta & Cocarascu, 2025).
"""

from __future__ import annotations

import common

from resources.hi_phonetic import HINDI_PHONETIC_DICTIONARY

ATTACK_ID = "CA_WORD_13_PhoneticPerturbation"
EDIT_GRANULARITY = "word"

_PHONETIC_DICTIONARIES = {
    "hi": HINDI_PHONETIC_DICTIONARY,
}


def apply(record, perturbation_budget=1, rng=None):
    claim = record.get("claim") or record.get("claim_text") or ""
    language = common.validate_language(record.get("language"))
    gold_label = record.get("gold_label") or record.get("label")

    if not claim or language is None:
        return common.build_record(
            ATTACK_ID, language, claim, record.get("evidence"), None, None,
            gold_label, "same_as_gold", EDIT_GRANULARITY, None,
            skip_reason="missing_claim_or_unsupported_language",
        )

    dictionary = _PHONETIC_DICTIONARIES.get(language)
    if not dictionary:
        return common.build_record(
            ATTACK_ID, language, claim, record.get("evidence"), None, None,
            gold_label, "same_as_gold", EDIT_GRANULARITY, None,
            skip_reason=f"missing_phonetic_dictionary_for_{language}",
        )

    rng = rng or common.new_rng()
    tokens, _ = common.tokenize(claim)
    result_tokens = list(tokens)

    candidates = []
    for idx, tok in enumerate(tokens):
        core, _, _ = common._strip_trailing_punct(tok)
        if core in dictionary:
            candidates.append((idx, core, dictionary[core]))

    if not candidates:
        return common.build_record(
            ATTACK_ID, language, claim, record.get("evidence"), None, None,
            gold_label, "same_as_gold", EDIT_GRANULARITY, None,
            skip_reason="no_applicable_words",
        )

    rng.shuffle(candidates)
    applied = 0
    original_word = None
    phonetic_variant = None
    for idx, core, variants in candidates:
        variant = rng.choice(variants)
        _, lead, trail = common._strip_trailing_punct(tokens[idx])
        result_tokens[idx] = lead + variant + trail
        applied += 1
        original_word = core
        phonetic_variant = variant
        if applied >= perturbation_budget:
            break

    adversarial_claim = " ".join(result_tokens)
    return common.build_record(
        ATTACK_ID, language, claim, record.get("evidence"),
        adversarial_claim, None,
        gold_label, "same_as_gold", EDIT_GRANULARITY,
        {
            "substitution_type": "phonetic_variant",
            "original_word": original_word,
            "phonetic_variant": phonetic_variant,
            "perturbations_applied": applied,
        },
    )
