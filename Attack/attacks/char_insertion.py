"""CA_CHAR_03 — Character Insertion.

Inserts a copy of a randomly selected internal grapheme cluster immediately
after itself, inside a word of the claim (default: 1 insertion).

Ref: FactEval benchmark (Mamta & Cocarascu, 2025).
"""

from __future__ import annotations

import common

ATTACK_ID = "CA_CHAR_03_CharacterInsertion"
EDIT_GRANULARITY = "character"


def apply(record, insertion_budget=1, rng=None):
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
    tokens, _ = common.tokenize(claim)
    applied = 0
    affected_word = None
    result_tokens = list(tokens)

    word_indices = list(range(len(tokens)))
    rng.shuffle(word_indices)

    for idx in word_indices:
        core, lead, trail = common._strip_trailing_punct(tokens[idx])
        clusters = common.grapheme_clusters(core)
        if len(clusters) < 4:
            continue

        candidates = [
            i for i in range(1, len(clusters) - 1)
            if not common.cluster_is_mark(clusters[i])
            and not common.cluster_contains_virama(clusters[i])
        ]
        if not candidates:
            continue

        i = rng.choice(candidates)
        clusters.insert(i + 1, clusters[i])
        new_core = "".join(clusters)
        result_tokens[idx] = lead + new_core + trail
        applied += 1
        affected_word = core
        if applied >= insertion_budget:
            break

    if applied == 0:
        return common.build_record(
            ATTACK_ID, language, claim, record.get("evidence"), None, None,
            gold_label, "same_as_gold", EDIT_GRANULARITY,
            {"insertion_type": "self_character", "insertions_applied": 0,
             "grapheme_aware": True},
            skip_reason="no_valid_insertion_candidate",
        )

    adversarial_claim = " ".join(result_tokens)
    return common.build_record(
        ATTACK_ID, language, claim, record.get("evidence"),
        adversarial_claim, None,
        gold_label, "same_as_gold", EDIT_GRANULARITY,
        {
            "insertion_type": "self_character",
            "insertions_applied": applied,
            "affected_word": affected_word,
            "grapheme_aware": True,
        },
    )
