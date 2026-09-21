"""Judge: decides whether an attack succeeded, with fluency/meaning gates.

Two layers:
  1. Mechanical — verdict vs gold label -> flipped; excludes baseline
     failures, skips, errors, and unparseable verdicts.
  2. LLM gate — one call per attacked instance returning JSON
     {"fluency": 1-5, "meaning_preserved": bool}.

Attack-aware gating (by attack intent):
  - meaning-preserving attacks: exclude if meaning drifts OR fluency < 3.
  - jumbling: no gate (syntax broken by design, bag-of-words preserved).
  - meaning-drift attacks: fluency gate only (meaning change is the point).

ASR: raw (all flips / valid) and gated (flips / valid after exclusions).
"""

from __future__ import annotations

import json
import re

SYSTEM = (
    "You are a Hindi-language quality judge. Do not show any reasoning or "
    "thinking. Output ONLY valid JSON, no explanations."
)

PROMPT = (
    "Original claim: \"{original_claim}\"\n\n"
    "Attacked text: \"{attacked_text}\"\n\n"
    "Judge the attacked text:\n"
    "- fluency: 1-5 (5 = perfect natural Hindi, 1 = broken/garbled).\n"
    "- meaning_preserved: true if the attacked text still means the same as "
    "the original claim, false if the meaning changed.\n\n"
    'Respond as JSON: {{"fluency": <int>, "meaning_preserved": <true|false>}}'
)

FLUENCY_THRESHOLD = 3

# Attacks where changing the meaning is the entire point — no meaning gate.
MEANING_DRIFT_ATTACKS = {
    "CA_06_FactMixing",
    "EA_CLAIMREWRITE_01_ClaimRewrite",
    "EA_CTXREP_01_ContextualizedReplace",
    "EA_ADVADD_01_AdvAdd",
    "EA_FACT2FICT_01_Fact2Fiction",
    "EA_OMITOMISSION_01_OmissionGeneration",
}

# Attacks where broken word order is the point — no gate at all.
NO_GATE_ATTACKS = {
    "CA_WORD_03_Jumbling",
}


def gate_applies(attack_id):
    """Return ('meaning'|'fluency'|None) for what the gate should check."""
    if attack_id in NO_GATE_ATTACKS:
        return None
    if attack_id in MEANING_DRIFT_ATTACKS:
        return "fluency"
    return "meaning"


def judge_quality(client, original_claim, attacked_text):
    """Call the LLM judge. Returns (fluency, meaning_preserved) or (None, None)."""
    if not attacked_text:
        return None, None
    prompt = PROMPT.format(original_claim=original_claim, attacked_text=attacked_text)
    try:
        raw = client.complete(prompt, system=SYSTEM, max_tokens=512)
    except Exception:  # noqa: BLE001
        return None, None
    return parse_quality(raw)


def parse_quality(text):
    """Parse the judge's JSON reply; regex fallback for sloppy output."""
    if not text:
        return None, None
    fluency = None
    meaning = None
    try:
        data = json.loads(text)
        fluency = data.get("fluency")
        meaning = data.get("meaning_preserved")
    except (json.JSONDecodeError, AttributeError):
        m = re.search(r'"fluency"\s*:\s*(\d)', text)
        if m:
            fluency = int(m.group(1))
        m = re.search(r'"meaning_preserved"\s*:\s*(true|false)', text, re.I)
        if m:
            meaning = m.group(1).lower() == "true"
    if isinstance(fluency, str) and fluency.isdigit():
        fluency = int(fluency)
    if meaning is None:
        m = re.search(r"meaning[_ ]preserved[^a-z]*?(true|false)", text, re.I)
        if m:
            meaning = m.group(1).lower() == "true"
    return fluency, meaning


def decide(attack_id, gold_label, verdict, baseline_failed=False):
    """Mechanical layer. Returns (flipped, reason).

    reason is one of: flip, no_flip, baseline_failure, skip/error/unparseable.
    """
    if baseline_failed:
        return False, "baseline_failure"
    if verdict is None or gold_label in (None, ""):
        return False, "unusable_verdict"
    if verdict == gold_label:
        return False, "no_flip"
    return True, "flip"


def apply_gate(attack_id, fluency, meaning_preserved):
    """Return (excluded, reason) for the quality gate."""
    mode = gate_applies(attack_id)
    if mode is None:
        return False, None
    if fluency is None:
        return True, "judge_unavailable"
    if mode == "fluency":
        if fluency < FLUENCY_THRESHOLD:
            return True, "poor_fluency"
        return False, None
    # meaning mode
    if meaning_preserved is False:
        return True, "meaning_drift"
    if fluency < FLUENCY_THRESHOLD:
        return True, "poor_fluency"
    return False, None


def compute_asr(results):
    """Compute raw and gated ASR from a list of per-instance result dicts.

    Each result: {"flipped": bool, "reason": str, "excluded": bool}.
    """
    eligible = [r for r in results
                if r["reason"] not in ("baseline_failure", "unusable_verdict")
                and not r.get("skip")]
    errors = [r for r in results if r["reason"] == "unusable_verdict"]
    flips_raw = sum(1 for r in eligible if r["flipped"])
    gated_eligible = [r for r in eligible if not r.get("excluded")]
    flips_gated = sum(1 for r in gated_eligible if r["flipped"])

    raw_denom = len(eligible) or 0
    gated_denom = len(gated_eligible) or 0
    return {
        "raw_asr": flips_raw / raw_denom if raw_denom else None,
        "gated_asr": flips_gated / gated_denom if gated_denom else None,
        "flips_raw": flips_raw,
        "flips_gated": flips_gated,
        "eligible": raw_denom,
        "gated_eligible": gated_denom,
        "excluded": len(eligible) - gated_denom,
        "errors": len(errors),
    }
