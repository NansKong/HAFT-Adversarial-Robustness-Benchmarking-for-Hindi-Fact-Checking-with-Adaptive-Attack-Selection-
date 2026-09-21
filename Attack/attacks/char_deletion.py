"""CA_CHAR_04 — Character Deletion.

Deletes one randomly selected internal grapheme cluster from a word of the
claim (default: 1 deletion). A cluster that is part of a conjunct is never
deleted alone — the whole conjunct is dropped to avoid leaving a dangling
virama. Standalone marks (matras) are not deleted.

Ref: FactEval benchmark (Mamta & Cocarascu, 2025).
"""

from __future__ import annotations

import common

ATTACK_ID = "CA_CHAR_04_CharacterDeletion"
EDIT_GRANULARITY = "character"


def apply(record, deletion_budget=1, rng=None):
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
        if len(clusters) < 4:  # need >= 3 clusters; a single deletion must leave >= 2
            continue

        candidates = [
            i for i in range(1, len(clusters) - 1)
            if not common.cluster_is_mark(clusters[i])
        ]
        if not candidates:
            continue

        i = rng.choice(candidates)
        del clusters[i]
        new_core = "".join(clusters)
        result_tokens[idx] = lead + new_core + trail
        applied += 1
        affected_word = core
        if applied >= deletion_budget:
            break

    if applied == 0:
        return common.build_record(
            ATTACK_ID, language, claim, record.get("evidence"), None, None,
            gold_label, "same_as_gold", EDIT_GRANULARITY,
            {"deletion_type": "internal_character", "deletions_applied": 0,
             "grapheme_aware": True},
            skip_reason="no_valid_deletion_candidate",
        )

    adversarial_claim = " ".join(result_tokens)
    return common.build_record(
        ATTACK_ID, language, claim, record.get("evidence"),
        adversarial_claim, None,
        gold_label, "same_as_gold", EDIT_GRANULARITY,
        {
            "deletion_type": "internal_character",
            "deletions_applied": applied,
            "affected_word": affected_word,
            "grapheme_aware": True,
        },
    )
