"""EA_OMITOMISSION_01 — Omission Generation Attack.

Deletes a specific syntactic construct (temporal/date modifier, number
expression, or parenthetical) from the evidence sentence, stripping essential
qualifiers while preserving surface stance. Pushes SUP/REF claims toward NEI.

Black-box simplification of Atanasova et al. (2022): the original uses a
dependency parser to identify optional constructs. We use curated Hindi
regex patterns (dates, years, number ranges, parentheticals) instead — no
external parser dependency.

Category: evidence_attack. Edit granularity: sentence.
"""

from __future__ import annotations

import re

import common

ATTACK_ID = "EA_OMITOMISSION_01_OmissionGeneration"
EDIT_GRANULARITY = "sentence"

# Devanagari + Western digits, year/date expressions, ranges, parentheses.
_DATE_PATTERN = re.compile(
    r"\([^)]*\)|"                          # parentheticals
    r"\d{4}\s*(?:से|तक|ई\.?|में|को)?\s*(?:से\s*\d{4}\s*तक)?"  # year / year range
    r"|\d{1,2}\s+\S+\s+\d{4}"             # e.g. 2 अक्टूबर 1869
    r"|\d{1,2}\s+(?:जनवरी|फ़रवरी|फरवरी|मार्च|अप्रैल|मई|जून|जुलाई|अगस्त|सितंबर|सितम्बर|अक्टूबर|अक्तूबर|नवंबर|नवम्बर|दिसंबर|दिसम्बर)(?:\s+\d{4})?"  # date mention
    r"|\d{4}"                             # bare year
)

# Temporal phrases: X से Y तक, X के बाद, X वर्षों तक, X साल, X महीने, X दिनों
_TEMPORAL_PHRASE = re.compile(
    r"(?:\d+\s*[-\u2013]\s*\d+)|"                              # numeric range 1998-2004
    r"(?:\d{4}\s*से\s*\d{4}\s*तक)|"                            # 1998 से 2004 तक
    r"(?:\d+\s*(?:वर्ष|साल|महीने|महीनों|दिन|दिनों|सप्ताह|हफ्ते|घंटे|घंटों)\s*तक)|"  # duration
    r"(?:\d+\s*(?:वर्षों|सालों)\s+(?:से|पहले|बाद))|"            # X वर्षों से
    r"(?:\d+\s*(?:बार|प्रतिशत|%|फ़ीसदी))"                       # counts/percentages
)

_ORDINAL_RANGE = re.compile(
    r"\d+\s*(?:वें|वीं|वां|वाँ|सबसे|के\s+बाद|से\s+\d+\s+तक|प्रतिशत|%|किमी|किलोमीटर|करोड़|लाख|हज़ार|हजार|मिलियन|अरब)"
)


def _find_deletable_span(evidence, rng):
    """Return (start, end) of a deletable construct, or None."""
    candidates = []
    for m in _DATE_PATTERN.finditer(evidence):
        start, end = m.span()
        snippet = evidence[start:end].strip()
        if snippet:
            candidates.append((start, end, snippet))
    for m in _TEMPORAL_PHRASE.finditer(evidence):
        start, end = m.span()
        snippet = evidence[start:end].strip()
        if snippet:
            candidates.append((start, end, snippet))
    for m in _ORDINAL_RANGE.finditer(evidence):
        start, end = m.span()
        snippet = evidence[start:end].strip()
        if snippet:
            candidates.append((start, end, snippet))
    if not candidates:
        return None
    return rng.choice(candidates)


def apply(record, rng=None):
    claim = record.get("claim") or record.get("claim_text") or ""
    evidence = record.get("evidence") or record.get("evidence_text") or ""
    language = common.validate_language(record.get("language"))
    gold_label = record.get("gold_label") or record.get("label")

    if not claim or not evidence or language is None:
        return common.build_record(
            ATTACK_ID, language, claim, evidence, None, None,
            gold_label, "NEI", EDIT_GRANULARITY, None,
            skip_reason="missing_claim_or_evidence_or_unsupported_language",
        )

    rng = rng or common.new_rng()
    span = _find_deletable_span(evidence, rng)
    if span is None:
        return common.build_record(
            ATTACK_ID, language, claim, evidence, None, None,
            gold_label, "NEI", EDIT_GRANULARITY, None,
            skip_reason="no_deletable_construct",
        )

    start, end, deleted = span
    adv_evidence = (evidence[:start] + evidence[end:]).strip()
    adv_evidence = re.sub(r"\s{2,}", " ", adv_evidence).strip(" ,-")

    if not adv_evidence or adv_evidence == evidence:
        return common.build_record(
            ATTACK_ID, language, claim, evidence, None, None,
            gold_label, "NEI", EDIT_GRANULARITY, None,
            skip_reason="deletion_produced_no_change",
        )

    return common.build_record(
        ATTACK_ID, language, claim, evidence,
        None, adv_evidence,
        gold_label, "NEI", EDIT_GRANULARITY,
        {
            "omitted_construct": "temporal_modifier_or_parenthetical",
            "deleted_tokens": [deleted],
        },
        validity_flags={
            "fluency_checked": True,
            "label_consistent": True,
            "meaning_preserved": False,
        },
    )
