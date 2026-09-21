"""EA_CLAIMREWRITE_01 — Claim-Aligned Re-Writing.

Rewrites the original evidence to appear as if it SUPPORTS the claim, so a
REF claim flips toward SUP. Black-box simplification of Abdelnabi & Fritz
(2023): the paper masks salient tokens and reconstructs with T5; we prompt
the LLM to perform the same rewrite. Only meaningful for REF claims (NEI
skipped per the survey's note).

Category: evidence_attack. Edit granularity: sentence.
"""

from __future__ import annotations

from . import common_llm

ATTACK_ID = "EA_CLAIMREWRITE_01_ClaimRewrite"
EDIT_GRANULARITY = "sentence"

SYSTEM = (
    "You are an adversarial testing assistant for a fact-checking system. "
    "You write fluent Hindi. Output ONLY the requested text, no explanations."
)

PROMPT = (
    "Claim: \"{claim}\"\n\n"
    "Original evidence: \"{evidence}\"\n\n"
    "Rewrite the evidence so it appears to SUPPORT the claim above, even "
    "though it currently contradicts it. Keep the sentence fluent, natural, "
    "and in Hindi. Keep a news/documentary style. Do not mention the claim "
    "or the word 'evidence'.\n\n"
    "Output only the rewritten evidence sentence."
)


def apply(record, client, rng=None):
    claim = common_llm.get_claim(record)
    evidence = common_llm.get_evidence(record)
    gold = common_llm.get_gold_label(record).upper()

    if not claim or not evidence:
        return common_llm.build_llm_record(
            ATTACK_ID, record, None, None, "SUP", EDIT_GRANULARITY, None,
            skip_reason="missing_claim_or_evidence",
        )
    if gold == "NEI":
        return common_llm.build_llm_record(
            ATTACK_ID, record, None, None, "SUP", EDIT_GRANULARITY, None,
            skip_reason="nei_claim_not_targeted",
        )

    prompt = PROMPT.format(claim=claim, evidence=evidence)
    text = common_llm.generate_text(client, prompt, SYSTEM, max_tokens=512)

    if not common_llm.is_usable(text):
        return common_llm.build_llm_record(
            ATTACK_ID, record, None, None, "SUP", EDIT_GRANULARITY,
            {"attack_name": "Claim-Aligned Re-Writing"},
            skip_reason="llm_generation_failed",
        )

    return common_llm.build_llm_record(
        ATTACK_ID, record, None, text,
        "SUP", EDIT_GRANULARITY,
        {"attack_name": "Claim-Aligned Re-Writing"},
    )
