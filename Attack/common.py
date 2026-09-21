"""Shared utilities for the rule-based attack engine.

All 14 rule-based attacks are pure Python (no LLM / no external packages
beyond the standard library). This module provides the grapheme-aware
Unicode helpers required by the attack descriptions, plus the standard
output-record builder used by every attack.
"""

from __future__ import annotations

import re
import random
import sys
import unicodedata

SUPPORTED_LANGUAGES = {"hi", "mni", "te", "ur", "pa", "ta", "or", "ml"}

ATTACK_ID_PREFIX = "CA_"
DEFAULT_LANGUAGE = "hi"
DEFAULT_SEED = 42

# Grapheme-extend category names; see UAX #29.
_GRAPHEME_EXTEND = {
    "Mn",   # non-spacing marks (matras: aa/ee/o/au kar, anusvara, etc.)
    "Mc",   # spacing combining marks (Devanagari vowel signs i / ii ...)
    "Me",   # enclosing marks
    "Cf",   # format chars (ZWJ/ZWNJ — keep with base so conjuncts stay intact)
    "Cc",   # control chars (ZWS U+200B)
    "Sk",   # modifier symbols (chandrabindu-ish edge cases)
}


def grapheme_clusters(text):
    """Split *text* into extended grapheme clusters (UAX #29, simplified).

    Conjuncts like क्ष (ka + virama + ssa) and matras like ि (vowel sign i)
    stay attached to their base consonant instead of being split at the
    byte/code-point level.
    """
    clusters = []
    current = ""
    for ch in text:
        cat = unicodedata.category(ch)
        if current and cat in _GRAPHEME_EXTEND:
            current += ch
        else:
            if current:
                clusters.append(current)
            current = ch
    if current:
        clusters.append(current)
    return clusters


def cluster_length(text):
    """Number of grapheme clusters in *text*."""
    return len(grapheme_clusters(text))


def cluster_is_mark(cluster):
    """True if a cluster is only a combining mark / virama (no base char)."""
    return all(unicodedata.category(ch) in _GRAPHEME_EXTEND for ch in cluster)


def cluster_contains_virama(cluster):
    """True if the cluster contains a virama (halant / pulli), i.e. is a conjunct."""
    for ch in cluster:
        name = unicodedata.name(ch, "")
        if "VIRAMA" in name or "HALANT" in name or "PULLI" in name:
            return True
    return False


def cluster_contains_zwj(cluster):
    return "\u200d" in cluster


def strip_mark(cluster):
    """Remove trailing combining marks from a cluster (keeps the base + conjunct part)."""
    if not cluster:
        return cluster
    end = len(cluster)
    while end > 0 and unicodedata.category(cluster[end - 1]) in _GRAPHEME_EXTEND:
        end -= 1
    return cluster[:end]


def _strip_trailing_punct(token):
    """Split a whitespace token into (core, leading_punct, trailing_punct)."""
    core = token
    lead = ""
    trail = ""
    while core and not (core[0].isalnum() or cluster_length(core[0]) > 0 and unicodedata.category(core[0]) not in {"Po", "Ps", "Pe", "Pi", "Pf", "Pc", "Pd"}):
        lead += core[0]
        core = core[1:]
    while core and unicodedata.category(core[-1]) in {"Po", "Ps", "Pe", "Pi", "Pf", "Pc", "Pd"}:
        trail = core[-1] + trail
        core = core[:-1]
    if not core:
        return token, "", ""
    return core, lead, trail


def tokenize(text):
    """Whitespace tokenization, keeping punctuation attached to its word.

    Returns (tokens, spans) where spans[i] = (start, end) of token i in *text*.
    """
    tokens = []
    spans = []
    for m in re.finditer(r"\S+", text):
        tokens.append(m.group(0))
        spans.append(m.span())
    return tokens, spans


def validate_language(language):
    """Return normalized language code or None if unsupported."""
    if language is None:
        return None
    lang = str(language).strip().lower()
    if lang in SUPPORTED_LANGUAGES:
        return lang
    if lang.startswith("hi"):
        return "hi"
    return None


def build_record(attack_id, language, original_claim, original_evidence,
                 adversarial_claim, adversarial_evidence, gold_label,
                 target_label, edit_granularity, technique_params,
                 validity_flags=None, skip_reason=None):
    """Build the standard JSON output record used by every attack.

    Returns a dict. If *skip_reason* is given the adversarial text fields are
    None and the record describes why the instance was skipped.
    """
    record = {
        "attack_id": attack_id,
        "language": language,
        "original_claim": original_claim,
        "original_evidence": original_evidence,
        "adversarial_claim": adversarial_claim,
        "adversarial_evidence": adversarial_evidence,
        "gold_label": gold_label,
        "target_label": target_label,
        "edit_granularity": edit_granularity,
        "technique_params": technique_params or {},
        "validity_flags": validity_flags or {
            "fluency_checked": False,
            "label_consistent": True,
            "meaning_preserved": False,
        },
        "skip_reason": skip_reason,
    }
    return record


def reseed(rng):
    """(Convenience) reseed the module-level random generator."""
    rng.seed(DEFAULT_SEED)


def new_rng():
    return random.Random(DEFAULT_SEED)


# -- dataset loading (CSV or XLSX) ------------------------------------------

_FIELD_ALIASES = {
    "claim": ("claim", "claim_text", "Claim", "claim1"),
    "evidence": ("evidence", "evidence_text", "Evidence"),
    "label": ("label", "gold_label", "Label", "goldLabel"),
    "language": ("language", "lang", "Language"),
    "domain": ("domain", "Domain"),
}


def _first(row, *aliases):
    for alias in aliases:
        if alias in row and row[alias] not in (None, ""):
            return str(row[alias]).strip()
    return ""


def load_dataset(path):
    """Load rows from a CSV or XLSX file into normalized dicts.

    Returns list of {"row_id", "claim", "evidence", "label", "language",
    "domain"}. XLSX cells are converted to str and NBSPs collapsed to normal
    spaces; label is uppercased. Empty-claim rows are skipped with a warning
    printed to stderr.
    """
    if path.lower().endswith((".xlsx", ".xlsm")):
        import openpyxl

        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = wb[wb.sheetnames[0]]
        header = None
        rows = []
        for row in ws.iter_rows(values_only=True):
            if header is None:
                header = [str(c).strip() if c is not None else "" for c in row]
                continue
            cell = {header[j]: row[j] for j in range(min(len(header), len(row)))}
            rows.append(cell)
    else:
        import csv

        with open(path, encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))

    out = []
    for i, row in enumerate(rows):
        claim = _first(row, *_FIELD_ALIASES["claim"]).replace("\xa0", " ").strip()
        evidence = _first(row, *_FIELD_ALIASES["evidence"]).replace("\xa0", " ").strip()
        label = _first(row, *_FIELD_ALIASES["label"]).upper()
        if not claim:
            print(f"[WARN] row {i}: empty claim, skipping", file=sys.stderr)
            continue
        out.append({
            "row_id": i,
            "claim": claim,
            "evidence": evidence,
            "label": label,
            "language": _first(row, *_FIELD_ALIASES["language"]) or "hi",
            "domain": _first(row, *_FIELD_ALIASES["domain"]),
        })
    return out
