"""EA_CTXREP_01 — Contextualized Replace.

Replaces a salient word in the evidence with a contextually plausible
alternative that flips the verifier's verdict. Black-box simplification of
Li et al. (2020): the paper computes gradient attribution and masks the top
words with a BERT MLM; we prompt the LLM to do the same replacement while
keeping the sentence fluent.

Category: evidence_attack. Edit granularity: word.
"""

from __future__ import annotations

from . import common_llm

ATTACK_ID = "EA_CTXREP_01_ContextualizedReplace"
EDIT_GRANULARITY = "word"

SYSTEM = (
    "You are an adversarial testing assistant for a fact-checking system. "
    "You write fluent Hindi. Output ONLY the requested text, no explanations."
)

PROMPT = (
    "Claim: \"{claim}\"\n\n"
    "Original evidence: \"{evidence}\"\n\n"
    "Identify the MOST important word in the evidence that determines whether "
    "it supports or refutes the claim. Replace ONLY that word with a "
    "contextually plausible Hindi word that changes the evidence's stance "
    "toward the claim (for example, replace the word that makes it "
    "support/refute with a word that makes it do the opposite). The sentence "
    "must stay grammatically correct and natural.\n\n"
    "Output only the rewritten evidence sentence."
)


def apply(record, client, rng=None):
    claim = common_llm.get_claim(record)
    evidence = common_llm.get_evidence(record)
    gold = common_llm.get_gold_label(record).upper()

    if not claim or not evidence:
        return common_llm.build_llm_record(
            ATTACK_ID, record, None, None, "REF", EDIT_GRANULARITY, None,
            skip_reason="missing_claim_or_evidence",
        )

    prompt = PROMPT.format(claim=claim, evidence=evidence)
    text = common_llm.generate_text(client, prompt, SYSTEM, max_tokens=512)

    if not common_llm.is_usable(text):
        return common_llm.build_llm_record(
            ATTACK_ID, record, None, None, "REF", EDIT_GRANULARITY,
            {"attack_name": "Contextualized Replace"},
            skip_reason="llm_generation_failed",
        )

    return common_llm.build_llm_record(
        ATTACK_ID, record, None, text,
        "REF", EDIT_GRANULARITY,
        {"attack_name": "Contextualized Replace"},
    )
