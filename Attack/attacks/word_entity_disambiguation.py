"""CA_WORD_02 — Entity Disambiguation (Entity Disamb.).

Replaces a specific named entity in the claim with an ambiguous alternative
name (a namesake with multiple referents) so retrieval pulls evidence about
the wrong sense. A curated cross-lingual gazetteer serves as the
disambiguation resource; no NER model is required — gazetteer keys are matched
directly against claim tokens (the spec's gazetteer fallback).

Ref: Kim & Allan (2019); Liu et al. (2025) Sec. 5.1.2.
"""

from __future__ import annotations

import common

from resources.hi_gazetteer import HINDI_AMBIGUOUS_ENTITIES

ATTACK_ID = "CA_WORD_02_EntityDisambiguation"
EDIT_GRANULARITY = "word"

_GAZETTEERS = {
    "hi": HINDI_AMBIGUOUS_ENTITIES,
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

    gazetteer = _GAZETTEERS.get(language)
    if not gazetteer:
        return common.build_record(
            ATTACK_ID, language, claim, record.get("evidence"), None, None,
            gold_label, "same_as_gold", EDIT_GRANULARITY, None,
            skip_reason=f"missing_gazetteer_for_{language}",
        )

    rng = rng or common.new_rng()
    tokens, _ = common.tokenize(claim)
    result_tokens = list(tokens)

    candidates = []
    for idx, tok in enumerate(tokens):
        core, _, _ = common._strip_trailing_punct(tok)
        if core in gazetteer:
            candidates.append((idx, core, gazetteer[core]))

    if not candidates:
        return common.build_record(
            ATTACK_ID, language, claim, record.get("evidence"), None, None,
            gold_label, "same_as_gold", EDIT_GRANULARITY, None,
            skip_reason="no_ambiguity_found",
        )

    rng.shuffle(candidates)
    applied = 0
    original_entity = None
    ambiguous_replacement = None
    possible_senses = None
    for idx, core, senses in candidates:
        replacement = rng.choice(senses)
        _, lead, trail = common._strip_trailing_punct(tokens[idx])
        result_tokens[idx] = lead + replacement + trail
        applied += 1
        original_entity = core
        ambiguous_replacement = replacement
        possible_senses = senses
        if applied >= substitution_budget:
            break

    adversarial_claim = " ".join(result_tokens)
    return common.build_record(
        ATTACK_ID, language, claim, record.get("evidence"),
        adversarial_claim, None,
        gold_label, "same_as_gold", EDIT_GRANULARITY,
        {
            "original_entity": original_entity,
            "ambiguous_replacement": ambiguous_replacement,
            "possible_senses": possible_senses,
            "disambiguation_source": "curated_hindi_gazetteer",
        },
    )
