"""CA_WORD_03 — Jumbling.

Randomly shuffles the word order of the claim. Punctuation stays attached to
its word. Claims with fewer than 3 words are skipped.

Ref: FactEval benchmark (Mamta & Cocarascu, 2025).
"""

from __future__ import annotations

import common

ATTACK_ID = "CA_WORD_03_Jumbling"
EDIT_GRANULARITY = "word"


def apply(record, rng=None):
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
    if len(tokens) < 3:
        return common.build_record(
            ATTACK_ID, language, claim, record.get("evidence"), None, None,
            gold_label, "same_as_gold", EDIT_GRANULARITY,
            {"shuffle_type": "uniform_random", "word_order_preserved": True},
            skip_reason="claim_too_short",
        )

    shuffled = list(tokens)
    rng.shuffle(shuffled)
    if shuffled == tokens:
        rng.shuffle(shuffled)
        if shuffled == tokens:
            return common.build_record(
                ATTACK_ID, language, claim, record.get("evidence"), None, None,
                gold_label, "same_as_gold", EDIT_GRANULARITY,
                {"shuffle_type": "uniform_random", "word_order_preserved": True},
                skip_reason="shuffle_reproduced_original",
            )

    adversarial_claim = " ".join(shuffled)
    return common.build_record(
        ATTACK_ID, language, claim, record.get("evidence"),
        adversarial_claim, None,
        gold_label, "same_as_gold", EDIT_GRANULARITY,
        {"shuffle_type": "uniform_random", "word_order_preserved": False},
    )
