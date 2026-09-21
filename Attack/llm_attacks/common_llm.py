"""Shared helpers for LLM-based attacks.

Every LLM attack file exposes apply(record, client, rng=None) and uses
generate_text() here so prompt plumbing, response cleanup, and record
building stay consistent.
"""

from __future__ import annotations

import re

import common


def generate_text(client, prompt, system, max_tokens=512, temperature=None):
    """Call the LLM and return cleaned text (code fences stripped).

    Returns "" on failure — callers then skip the instance, matching the
    rule-based pipeline's skip semantics.
    """
    try:
        text = client.complete(prompt, system=system, max_tokens=max_tokens,
                               temperature=temperature)
    except Exception as exc:  # noqa: BLE001 — caller decides how to handle
        return f"__ERROR__: {exc}"

    return clean_response(text)


def clean_response(text):
    if not text:
        return ""
    text = text.strip()
    # strip markdown code fences
    text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip().strip('"').strip()


def is_usable(text, min_chars=3):
    """Reject error markers, empties, and obviously broken output."""
    if not text:
        return False
    if text.startswith("__ERROR__"):
        return False
    if len(text) < min_chars:
        return False
    return True


def normalize_label(label):
    """Map free-form label strings to SUP/REF/NEI, else None."""
    if not label:
        return None
    label = label.strip().upper()
    if "SUP" in label:
        return "SUP"
    if "REF" in label:
        return "REF"
    if "NEI" in label or "NOT ENOUGH" in label:
        return "NEI"
    return None


def get_claim(record):
    return record.get("claim") or record.get("claim_text") or ""


def get_evidence(record):
    return record.get("evidence") or record.get("evidence_text") or ""


def get_gold_label(record):
    return record.get("gold_label") or record.get("label") or ""


def base_validity():
    return {
        "fluency_checked": False,
        "label_consistent": True,
        "meaning_preserved": False,
    }


def build_llm_record(attack_id, record, adversarial_claim, adversarial_evidence,
                     target_label, edit_granularity, technique_params,
                     injected_evidence_workaround=False, skip_reason=None):
    language = common.validate_language(record.get("language"))
    claim = get_claim(record)
    evidence = get_evidence(record)
    gold = get_gold_label(record)
    rec = common.build_record(
        attack_id, language, claim, evidence,
        adversarial_claim if not skip_reason else None,
        adversarial_evidence if not skip_reason else None,
        gold, target_label, edit_granularity,
        technique_params,
        skip_reason=skip_reason,
    )
    rec["injected_evidence_workaround"] = injected_evidence_workaround
    return rec
