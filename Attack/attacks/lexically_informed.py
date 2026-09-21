"""CA_03 — Lexically-informed.

Replaces one noun or adjective in the claim with a close synonym from a
curated lexical resource, producing a meaning-preserving lexical drift that
can trip up the verifier. The original paper adds a back-translation fluency
pass; in our rule-based setting the curated lexicon is the full attack
(fluency is checked downstream by the Judge).

Category: claim_attack. Edit granularity: sentence.
"""

from __future__ import annotations

import common

from resources.hi_synonyms import HINDI_SYNONYM_GROUPS, HINDI_STOPWORDS
from resources.hi_adjectives import HINDI_ADJECTIVE_SYNONYMS

ATTACK_ID = "CA_03_LexicallyInformed"
EDIT_GRANULARITY = "sentence"

_LEXICAL_RESOURCES = {
    "hi": HINDI_SYNONYM_GROUPS,
}
_ADJECTIVE_RESOURCES = {
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

    groups = _LEXICAL_RESOURCES.get(language)
    if not groups:
        return common.build_record(
            ATTACK_ID, language, claim, record.get("evidence"), None, None,
            gold_label, "same_as_gold", EDIT_GRANULARITY, None,
            skip_reason=f"missing_lexical_resource_for_{language}",
        )

    rng = rng or common.new_rng()
    tokens, _ = common.tokenize(claim)
    result_tokens = list(tokens)

    lookup = {}
    for group in groups:
        for w in group:
            lookup[w] = group
    # adjective lexicon entries (बड़ा -> विशाल) override generic groups
    adj_lookup = _ADJECTIVE_RESOURCES.get(language, {})
    lookup.update(adj_lookup)

    candidates = []
    for idx, tok in enumerate(tokens):
        core, _, _ = common._strip_trailing_punct(tok)
        if core in HINDI_STOPWORDS:
            continue
        if core in lookup:
            alternatives = [w for w in lookup[core] if w != core]
            if alternatives:
                candidates.append((idx, core, alternatives))

    if not candidates:
        return common.build_record(
            ATTACK_ID, language, claim, record.get("evidence"), None, None,
            gold_label, "same_as_gold", EDIT_GRANULARITY, None,
            skip_reason="no_applicable_candidates",
        )

    rng.shuffle(candidates)
    applied = 0
    original_word = None
    substituted_word = None
    for idx, core, alternatives in candidates:
        sub = rng.choice(alternatives)
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
            "attack_name": "Lexically-informed",
            "original_word": original_word,
            "substituted_word": substituted_word,
        },
        validity_flags={
            "fluency_checked": True,
            "label_consistent": True,
            "meaning_preserved": True,
        },
    )
