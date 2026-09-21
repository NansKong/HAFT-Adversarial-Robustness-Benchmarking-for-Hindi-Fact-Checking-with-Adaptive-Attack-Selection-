"""CA_WORD_12 — Synonyms (adjective-focused).

Replaces one adjective in the claim with a synonym from a curated adjective
synonym lexicon (default: 1 substitution). A POS tagger is not used; instead
the lexicon only lists adjectives, which is the spec's allowed fallback.

Ref: FactEval benchmark (Mamta & Cocarascu, 2025).
"""

from __future__ import annotations

import common

from resources.hi_adjectives import HINDI_ADJECTIVE_SYNONYMS

ATTACK_ID = "CA_WORD_12_Synonyms"
EDIT_GRANULARITY = "word"

_LEXICAL_RESOURCES = {
    "hi": HINDI_ADJECTIVE_SYNONYMS,
}


def apply(record, substitution_budget=1, rng=None):
    claim = record.get("claim") or record.get("claim_text") or ""
    language = common.validate_language(record.get("language"))
    gold_label = record.get("gold_label") or record.get("label")

    if not claim or language is None:
        return common.build_record(
            ATTACK_ID, language, claim, record.get("evidence"), None, None,
            gold_label, "same_as_gold", EDIT_GRANULARITY, None,
            skip_reason="missing_claim_or_unsupported_language",
        )

    lexicon = _LEXICAL_RESOURCES.get(language)
    if not lexicon:
        return common.build_record(
            ATTACK_ID, language, claim, record.get("evidence"), None, None,
            gold_label, "same_as_gold", EDIT_GRANULARITY, None,
            skip_reason=f"missing_lexical_resource_for_{language}",
        )

    rng = rng or common.new_rng()
    tokens, _ = common.tokenize(claim)
    result_tokens = list(tokens)

    candidates = []
    for idx, tok in enumerate(tokens):
        core, _, _ = common._strip_trailing_punct(tok)
        if core in lexicon:
            candidates.append((idx, core, lexicon[core]))

    if not candidates:
        return common.build_record(
            ATTACK_ID, language, claim, record.get("evidence"), None, None,
            gold_label, "same_as_gold", EDIT_GRANULARITY, None,
            skip_reason="no_adjectives_found",
        )

    rng.shuffle(candidates)
    applied = 0
    original_word = None
    substituted_word = None
    for idx, core, synonyms in candidates:
        sub = rng.choice(synonyms)
        _, lead, trail = common._strip_trailing_punct(tokens[idx])
        result_tokens[idx] = lead + sub + trail
        applied += 1
        original_word = core
        substituted_word = sub
        if applied >= substitution_budget:
            break

    adversarial_claim = " ".join(result_tokens)
    return common.build_record(
        ATTACK_ID, language, claim, record.get("evidence"),
        adversarial_claim, None,
        gold_label, "same_as_gold", EDIT_GRANULARITY,
        {
            "substitution_type": "adjective_synonym",
            "original_word": original_word,
            "substituted_word": substituted_word,
            "lexical_resource": "curated_hindi_adjective_lexicon",
        },
    )
