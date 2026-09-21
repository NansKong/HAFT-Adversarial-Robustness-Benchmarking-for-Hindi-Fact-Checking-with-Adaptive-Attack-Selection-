"""CA_CHAR_01 — Character Swapping.

Swaps one randomly selected pair of adjacent grapheme clusters inside a word
of the claim (default: 1 swap). Conjuncts (virama sequences) are never split,
and identical adjacent clusters are never swapped (would be a no-op).

Ref: FactEval benchmark (Mamta & Cocarascu, 2025).
"""

from __future__ import annotations

import common

ATTACK_ID = "CA_CHAR_01_CharacterSwapping"
EDIT_GRANULARITY = "character"


def apply(record, swap_budget=1, rng=None):
    claim = record.get("claim") or record.get("claim_text") or ""
    language = common.validate_language(record.get("language"))
    gold_label = record.get("gold_label") or record.get("label")

    if not claim or language is None:
        return common.build_record(
            ATTACK_ID, language, claim, record.get("evidence"), None, None,
            gold_label, "same_as_gold", EDIT_GRANULARITY, None,
            skip_reason="missing_claim_or_unsupported_language",
        )

    rng = rng or common.new_rng()
    tokens, spans = common.tokenize(claim)
    applied = 0
    affected_word = None
    result_tokens = list(tokens)

    word_indices = list(range(len(tokens)))
    rng.shuffle(word_indices)

    for idx in word_indices:
        core, lead, trail = common._strip_trailing_punct(tokens[idx])
        clusters = common.grapheme_clusters(core)
        if len(clusters) < 3:
            continue

        candidates = []
        for i in range(len(clusters) - 1):
            a, b = clusters[i], clusters[i + 1]
            if a == b:
                continue  # no-op swap
            if common.cluster_is_mark(a) or common.cluster_is_mark(b):
                continue  # swapping a bare mark changes the cluster structure
            if common.cluster_contains_virama(a) or common.cluster_contains_virama(b):
                continue  # never split a conjunct
            candidates.append(i)
        if not candidates:
            continue

        i = rng.choice(candidates)
        clusters[i], clusters[i + 1] = clusters[i + 1], clusters[i]
        new_core = "".join(clusters)
        result_tokens[idx] = lead + new_core + trail
        applied += 1
        affected_word = core
        if applied >= swap_budget:
            break

    if applied == 0:
        return common.build_record(
            ATTACK_ID, language, claim, record.get("evidence"), None, None,
            gold_label, "same_as_gold", EDIT_GRANULARITY,
            {"swap_type": "adjacent", "swaps_applied": 0, "grapheme_aware": True},
            skip_reason="no_valid_swap_candidate",
        )

    adversarial_claim = " ".join(result_tokens)
    return common.build_record(
        ATTACK_ID, language, claim, record.get("evidence"),
        adversarial_claim, None,
        gold_label, "same_as_gold", EDIT_GRANULARITY,
        {
            "swap_type": "adjacent",
            "swaps_applied": applied,
            "affected_word": affected_word,
            "grapheme_aware": True,
        },
    )
