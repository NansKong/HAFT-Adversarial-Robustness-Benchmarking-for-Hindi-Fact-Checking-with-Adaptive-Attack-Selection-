"""EA_ADVADD_01 — AdvAdd (Claim-Conditioned Article Generation).

Generates a synthetic, claim-conditioned evidence passage whose surface
wording matches the claim's entities but whose factual assertions contradict
the claim, so a retriever surfaces it and the verifier flips.

Our pipeline has no retrieval corpus, so the injected-evidence workaround
applies: the verifier stage sends the ORIGINAL evidence plus this fabricated
passage together (flagged via injected_evidence_workaround=True), simulating
small-scale corpus poisoning.

Category: evidence_attack. Edit granularity: sentence.
"""

from __future__ import annotations

from . import common_llm

ATTACK_ID = "EA_ADVADD_01_AdvAdd"
EDIT_GRANULARITY = "sentence"

SYSTEM = (
    "You are an adversarial testing assistant for a fact-checking system. "
    "You write fluent Hindi news-style text. Output ONLY the requested text, "
    "no explanations."
)

PROMPT = (
    "Claim: \"{claim}\"\n\n"
    "Write a short Hindi news-style evidence passage (2-3 sentences) that:\n"
    "1. Repeats the same key entities and keywords as the claim, so a search "
    "engine would rank it highly for this claim.\n"
    "2. States facts that CONTRADICT the claim.\n"
    "3. Reads like a genuine news report, in fluent Hindi.\n\n"
    "Output only the passage."
)


def apply(record, client, rng=None):
    claim = common_llm.get_claim(record)
    if not claim:
        return common_llm.build_llm_record(
            ATTACK_ID, record, None, None, "REF", EDIT_GRANULARITY, None,
            skip_reason="missing_claim",
        )

    prompt = PROMPT.format(claim=claim)
    text = common_llm.generate_text(client, prompt, SYSTEM, max_tokens=768)

    if not common_llm.is_usable(text):
        return common_llm.build_llm_record(
            ATTACK_ID, record, None, None, "REF", EDIT_GRANULARITY,
            {"generator_model": "llm", "top_k_candidates": 1},
            skip_reason="llm_generation_failed",
        )

    return common_llm.build_llm_record(
        ATTACK_ID, record, None, text,
        "REF", EDIT_GRANULARITY,
        {"generator_model": "llm", "top_k_candidates": 1},
        injected_evidence_workaround=True,
    )
