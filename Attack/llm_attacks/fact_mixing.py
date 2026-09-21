"""CA_06 — Fact Mixing.

Blends facts from two evidence articles into one fluent-sounding claim that
conflates unrelated information, so no single source fully supports it. The
original paper uses two evidence articles; our dataset has one evidence per
row, so the runner passes a same-domain neighbor's evidence as the second
source (passed via record["neighbor_evidence"]).

Category: claim_attack. Edit granularity: sentence.
"""

from __future__ import annotations

from . import common_llm

ATTACK_ID = "CA_06_FactMixing"
EDIT_GRANULARITY = "sentence"

SYSTEM = (
    "You are an adversarial testing assistant for a fact-checking system. "
    "You write fluent Hindi. Output ONLY the requested sentence, no "
    "explanations."
)

PROMPT = (
    "You are given two evidence passages on related topics:\n\n"
    "Evidence A: \"{evidence_a}\"\n\n"
    "Evidence B: \"{evidence_b}\"\n\n"
    "Write ONE fluent Hindi claim that mixes one fact from Evidence A with "
    "one fact from Evidence B into a single natural-sounding sentence. The "
    "claim must be grammatically correct and read like a news headline, but "
    "must NOT be fully supported by either source alone.\n\n"
    "Output only the Hindi claim."
)


def apply(record, client, rng=None):
    evidence_a = common_llm.get_evidence(record)
    evidence_b = record.get("neighbor_evidence") or ""
    claim = common_llm.get_claim(record)

    if not claim or not evidence_a or not evidence_b:
        return common_llm.build_llm_record(
            ATTACK_ID, record, None, None, "NEI", EDIT_GRANULARITY, None,
            skip_reason="missing_evidence_pair",
        )

    prompt = PROMPT.format(evidence_a=evidence_a, evidence_b=evidence_b)
    text = common_llm.generate_text(client, prompt, SYSTEM, max_tokens=512)

    if not common_llm.is_usable(text):
        return common_llm.build_llm_record(
            ATTACK_ID, record, None, None, "NEI", EDIT_GRANULARITY,
            {"attack_name": "Fact Mixing"},
            skip_reason="llm_generation_failed",
        )

    return common_llm.build_llm_record(
        ATTACK_ID, record, text, None,
        "NEI", EDIT_GRANULARITY,
        {
            "attack_name": "Fact Mixing",
            "evidence_b_source": "same_domain_neighbor",
        },
    )
