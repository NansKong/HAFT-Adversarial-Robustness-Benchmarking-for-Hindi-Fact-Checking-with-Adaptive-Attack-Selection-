"""EA_IMPRET_01 — Imperceptible Character-Level Retrieval Attack.

Injects imperceptible characters (zero-width space U+200B / zero-width
non-joiner U+200C) into entity mentions inside the evidence text so a
retriever's tokenizer fails to map them, dropping document recall.

Per the paper's taxonomy this is rule_based — no LLM call. It lives in the
LLM folder because the injected-evidence workaround groups it with the other
poisoning attacks at verification time (original + perturbed evidence
together).

Category: evidence_attack. Edit granularity: character.
"""

from __future__ import annotations

import common

from . import common_llm

ATTACK_ID = "EA_IMPRET_01_ImperceptibleRetrieval"
EDIT_GRANULARITY = "character"

ZWS = "\u200b"
ZWNJ = "\u200c"


def _perturb_word(text, rng):
    """Insert one invisible char at a random position inside a random word."""
    words = text.split()
    if not words:
        return text, 0
    idx = rng.randrange(len(words))
    word = words[idx]
    pos = rng.randrange(1, len(word) + 1)
    char = rng.choice([ZWS, ZWNJ])
    words[idx] = word[:pos] + char + word[pos:]
    return " ".join(words), 1


def apply(record, client=None, rng=None, edit_budget=2):
    # client accepted for interface uniformity but unused — this attack
    # performs no LLM call.
    claim = common_llm.get_claim(record)
    evidence = common_llm.get_evidence(record)

    if not claim or not evidence:
        return common_llm.build_llm_record(
            ATTACK_ID, record, None, None, "NEI", EDIT_GRANULARITY, None,
            injected_evidence_workaround=True,
            skip_reason="missing_claim_or_evidence",
        )

    rng = rng or common.new_rng()
    adv_evidence = evidence
    inserted = 0
    for _ in range(max(1, edit_budget)):
        adv_evidence, n = _perturb_word(adv_evidence, rng)
        inserted += n
        if n == 0:
            break

    if inserted == 0 or adv_evidence == evidence:
        return common_llm.build_llm_record(
            ATTACK_ID, record, None, None, "NEI", EDIT_GRANULARITY, None,
            injected_evidence_workaround=True,
            skip_reason="no_valid_perturbation",
        )

    return common_llm.build_llm_record(
        ATTACK_ID, record, None, adv_evidence,
        "NEI", EDIT_GRANULARITY,
        {
            "perturbed_entity": None,
            "char_injection": "U+200B/U+200C",
            "zero_width_insertions": inserted,
        },
        injected_evidence_workaround=True,
    )
