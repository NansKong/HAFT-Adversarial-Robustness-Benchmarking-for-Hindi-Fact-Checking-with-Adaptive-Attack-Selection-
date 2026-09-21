"""CA_07 — Adv. Trigger (black-box approximation).

The paper's mechanism (HotFlip gradient search) needs white-box access to the
verifier's embeddings — unavailable in our black-box pipeline. Per the team's
decision, we approximate it: the LLM generates a short, fluent Hindi trigger
phrase that is prepended to the claim, designed to nudge the verifier toward
the target label while minimally disturbing the claim's surface meaning.

The approximation is flagged in technique_params.approximation.

Category: claim_attack. Edit granularity: sentence.
"""

from __future__ import annotations

from . import common_llm

ATTACK_ID = "CA_07_AdvTrigger"
EDIT_GRANULARITY = "sentence"

SYSTEM = (
    "You are an adversarial testing assistant for a fact-checking system. "
    "You generate short, fluent Hindi text. Output ONLY the requested text, "
    "with no explanations, quotes, or extra words."
)

PROMPT = (
    'Original claim (Hindi): "{claim}"\n'
    'Target verdict: {target_label}\n\n'
    "Write a short Hindi phrase (2-4 words) that, when placed BEFORE the claim, "
    "could nudge a fact-checking model toward the verdict {target_label} "
    "(e.g., phrases like \"दरअसल, यह सच है कि\" or \"विशेषज्ञों के अनुसार\"). "
    "The phrase must read naturally with the claim and must NOT change the "
    "claim's factual content.\n\n"
    "Output only the trigger phrase."
)


def apply(record, client, rng=None):
    claim = common_llm.get_claim(record)
    gold = common_llm.get_gold_label(record)
    language = record.get("language") or "hi"

    if not claim or not gold:
        return common_llm.build_llm_record(
            ATTACK_ID, record, None, None, "same_as_gold", EDIT_GRANULARITY, None,
            skip_reason="missing_claim_or_label",
        )

    prompt = PROMPT.format(claim=claim, target_label=gold)
    trigger = common_llm.generate_text(client, prompt, SYSTEM, max_tokens=64)

    if not common_llm.is_usable(trigger):
        return common_llm.build_llm_record(
            ATTACK_ID, record, None, None, "same_as_gold", EDIT_GRANULARITY,
            {"attack_name": "Adv. Trigger"},
            skip_reason="llm_generation_failed",
        )

    adversarial_claim = f"{trigger} {claim}".strip()
    return common_llm.build_llm_record(
        ATTACK_ID, record, adversarial_claim, None,
        "same_as_gold", EDIT_GRANULARITY,
        {
            "attack_name": "Adv. Trigger",
            "trigger_phrase": trigger,
            "approximation": "black_box_prompt_based",
        },
    )
