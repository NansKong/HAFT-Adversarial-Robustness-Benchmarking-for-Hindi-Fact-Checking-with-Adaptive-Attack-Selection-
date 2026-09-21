"""CA_16 — Colloquial.

Rephrases a formal claim into casual, everyday Hindi (with code-mixing where
natural) so the wording drifts far from formal evidence text and retrieval
struggles to match it. Meaning must be preserved.

Category: claim_attack. Edit granularity: sentence.
"""

from __future__ import annotations

from . import common_llm

ATTACK_ID = "CA_16_Colloquial"
EDIT_GRANULARITY = "sentence"

SYSTEM = (
    "You are a native Hindi speaker. You rewrite formal Hindi sentences into "
    "casual, conversational Hindi that people use while chatting with friends. "
    "Output ONLY the rewritten sentence, with no explanations."
)

PROMPT = (
    "Rewrite this formal claim in very casual, everyday spoken Hindi "
    "(Hinglish/code-mixing with common English words is fine):\n\n"
    '"{claim}"\n\n'
    "Rules:\n"
    "1. Keep the factual meaning EXACTLY the same.\n"
    "2. Use informal words and sentence flow, like someone telling a friend.\n"
    "3. Do not add or remove any facts.\n\n"
    "Output only the casual Hindi sentence."
)


def apply(record, client, rng=None):
    claim = common_llm.get_claim(record)
    if not claim:
        return common_llm.build_llm_record(
            ATTACK_ID, record, None, None, "same_as_gold", EDIT_GRANULARITY, None,
            skip_reason="missing_claim",
        )

    prompt = PROMPT.format(claim=claim)
    text = common_llm.generate_text(client, prompt, SYSTEM, max_tokens=512)

    if not common_llm.is_usable(text):
        return common_llm.build_llm_record(
            ATTACK_ID, record, None, None, "same_as_gold", EDIT_GRANULARITY,
            {"attack_name": "Colloquial"},
            skip_reason="llm_generation_failed",
        )

    return common_llm.build_llm_record(
        ATTACK_ID, record, text, None,
        "same_as_gold", EDIT_GRANULARITY,
        {"attack_name": "Colloquial"},
    )
