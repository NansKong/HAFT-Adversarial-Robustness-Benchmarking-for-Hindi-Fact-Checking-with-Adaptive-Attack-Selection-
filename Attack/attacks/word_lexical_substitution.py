"""CA_WORD_08 — Lexical Substitution.

Replaces one content word of the claim with a synonym / hypernym / hyponym
from a curated lexical resource (default: 1 substitution, synonym-only).
Stopwords are excluded.

Ref: DeSePtion (Hidey et al., 2020); benchmarked in FactEval.
"""

from __future__ import annotations

import common

from resources.hi_synonyms import HINDI_SYNONYM_GROUPS, HINDI_STOPWORDS

ATTACK_ID = "CA_WORD_08_LexicalSubstitution"
EDIT_GRANULARITY = "word"

_LEXICAL_RESOURCES = {
    "hi": HINDI_SYNONYM_GROUPS,
}

# (optional) hypernym/hyponym pair tables, per language
_HYPERNYMS = {"hi": {}}
_HYPONYMS = {"hi": {}}


def apply(record, substitution_budget=1, relation="synonym", rng=None):
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
            "substitution_type": relation,
            "original_word": original_word,
            "substituted_word": substituted_word,
            "lexical_resource": "curated_hindi_lexicon",
        },
    )
