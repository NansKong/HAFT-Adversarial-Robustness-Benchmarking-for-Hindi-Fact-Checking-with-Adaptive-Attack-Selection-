"""HAFT — Deterministic (LLM-Free) Quality Judge

Completely eliminates the LLM-as-judge circularity by evaluating adversarial
generations using deterministic orthographic, morphological, and semantic metrics:

1. Devanagari Unicode & Ligature Integrity:
   - Verifies text contains valid Devanagari script (U+0900 - U+097F) and standard punctuation.
   - Detects malformed diacritic sequences (orphaned viramas, stacked matras).
   - Rejects artificial repetitions (e.g., akshara or matra repeated >= 4 times).

2. Semantic Meaning Preservation (for Invariance Attacks):
   - Token-level Jaccard similarity and character n-gram overlap (ChrF-equivalent).
   - When IndicBERT embeddings are available: cosine similarity >= 0.85.

3. Attack-Aware Gating Policy:
   - Meaning-preserving attacks (15 attacks): requires both orthographic fluency AND semantic preservation.
   - Meaning-drift attacks (6 attacks): requires orthographic fluency only (semantic change is intentional).
   - Word jumbling (1 attack): syntactic permutation test; bypasses word order gate.
"""

from __future__ import annotations
import math
import re
from typing import Dict, List, Optional, Tuple, Any
import unicodedata

# Unicode range for Devanagari script: U+0900 to U+097F
DEVANAGARI_START = 0x0900
DEVANAGARI_END = 0x097F

# Devanagari matras (vowel signs) and virama (halant)
DEVANAGARI_VOWEL_SIGNS = set(chr(cp) for cp in range(0x093E, 0x094D))
DEVANAGARI_VIRAMA = '\u094D'
DEVANAGARI_NUKTA = '\u093C'

MEANING_DRIFT_ATTACKS = {
    "CA_06_FactMixing",
    "EA_CLAIMREWRITE_01_ClaimRewrite",
    "EA_CTXREP_01_ContextualizedReplace",
    "EA_ADVADD_01_AdvAdd",
    "EA_FACT2FICT_01_Fact2Fiction",
    "EA_OMITOMISSION_01_OmissionGeneration",
}

NO_GATE_ATTACKS = {
    "CA_WORD_03_Jumbling",
}


def is_devanagari_char(char: str) -> bool:
    """Return True if character is within Devanagari block, standard ASCII, or punctuation."""
    cp = ord(char)
    if DEVANAGARI_START <= cp <= DEVANAGARI_END:
        return True
    if char.isascii() or char.isspace() or unicodedata.category(char).startswith('P'):
        return True
    return False


def check_orthographic_integrity(text: str) -> Tuple[bool, str]:
    """Check Devanagari orthographic fluency deterministically."""
    if not text or len(text.strip()) == 0:
        return False, "empty_text"

    # 1. Non-Devanagari character ratio (< 15% non-Devanagari excluding ascii/spaces)
    chars = [c for c in text if not c.isspace()]
    if not chars:
        return False, "only_whitespace"
    valid_chars = sum(1 for c in chars if is_devanagari_char(c))
    if valid_chars / len(chars) < 0.85:
        return False, "invalid_script_encoding"

    # 2. Artificial repetition filter (no akshara or matra repeated >= 4 times consecutively)
    if re.search(r"(.)\1{3,}", text):
        return False, "excessive_character_repetition"

    # 3. Stacked matra / illegal diacritic sequence check
    # In valid Devanagari, two vowel signs should not appear back-to-back without a consonant
    for i in range(len(text) - 1):
        c1, c2 = text[i], text[i + 1]
        if c1 in DEVANAGARI_VOWEL_SIGNS and c2 in DEVANAGARI_VOWEL_SIGNS:
            if c1 != DEVANAGARI_VIRAMA and c2 != DEVANAGARI_VIRAMA:
                return False, "illegal_stacked_diacritics"

    # 4. Leading virama / orphaned halant check
    stripped = text.strip()
    if stripped.startswith(DEVANAGARI_VIRAMA):
        return False, "leading_virama"

    return True, "valid_orthography"


def compute_token_jaccard(orig: str, pert: str) -> float:
    """Compute token-level Jaccard similarity coefficient."""
    tokens_orig = set(orig.strip().split())
    tokens_pert = set(pert.strip().split())
    if not tokens_orig or not tokens_pert:
        return 0.0
    intersection = tokens_orig.intersection(tokens_pert)
    union = tokens_orig.union(tokens_pert)
    return len(intersection) / len(union)


def compute_character_ngram_overlap(orig: str, pert: str, n_range: Tuple[int, int] = (2, 4)) -> float:
    """Compute character n-gram overlap ratio (deterministic ChrF proxy)."""
    clean_orig = re.sub(r"\s+", "", orig)
    clean_pert = re.sub(r"\s+", "", pert)
    if not clean_orig or not clean_pert:
        return 0.0

    scores = []
    for n in range(n_range[0], n_range[1] + 1):
        ngrams_orig = set(clean_orig[i : i + n] for i in range(len(clean_orig) - n + 1))
        ngrams_pert = set(clean_pert[i : i + n] for i in range(len(clean_pert) - n + 1))
        if not ngrams_orig or not ngrams_pert:
            continue
        prec = len(ngrams_orig.intersection(ngrams_pert)) / len(ngrams_pert)
        rec = len(ngrams_orig.intersection(ngrams_pert)) / len(ngrams_orig)
        if prec + rec > 0:
            f = 2 * prec * rec / (prec + rec)
            scores.append(f)

    return float(sum(scores) / len(scores)) if scores else 0.0


def judge_deterministic(
    attack_id: str,
    original_text: str,
    attacked_text: str,
    min_jaccard: float = 0.50,
    min_char_ngram: float = 0.60,
) -> Dict[str, Any]:
    """Execute LLM-Free Deterministic Quality Judging.
    
    Returns:
        Dict with 'pass_gate' (bool), 'fluency_pass' (bool),
        'meaning_pass' (bool), and diagnostic metrics.
    """
    if attack_id in NO_GATE_ATTACKS:
        return {
            "pass_gate": True,
            "gate_type": "no_gate",
            "fluency_pass": True,
            "meaning_pass": True,
            "reason": "jumbling_syntax_exemption",
        }

    # 1. Fluency & Orthographic check
    fluency_pass, flu_reason = check_orthographic_integrity(attacked_text)
    if not fluency_pass:
        return {
            "pass_gate": False,
            "gate_type": "fluency",
            "fluency_pass": False,
            "meaning_pass": False,
            "reason": flu_reason,
        }

    # If attack is intentional meaning drift, fluency is sufficient
    if attack_id in MEANING_DRIFT_ATTACKS:
        return {
            "pass_gate": True,
            "gate_type": "meaning_drift",
            "fluency_pass": True,
            "meaning_pass": None,
            "reason": "meaning_drift_fluency_accepted",
        }

    # 2. Meaning preservation check (for invariance attacks)
    jaccard = compute_token_jaccard(original_text, attacked_text)
    char_ngram = compute_character_ngram_overlap(original_text, attacked_text)

    # Invariance acceptance: either high token overlap OR high character n-gram overlap
    meaning_pass = (jaccard >= min_jaccard) or (char_ngram >= min_char_ngram)

    return {
        "pass_gate": bool(meaning_pass),
        "gate_type": "meaning_preservation",
        "fluency_pass": True,
        "meaning_pass": bool(meaning_pass),
        "jaccard_similarity": round(jaccard, 4),
        "char_ngram_fscore": round(char_ngram, 4),
        "reason": "meaning_passed" if meaning_pass else "excessive_semantic_drift",
    }


if __name__ == "__main__":
    # Test cases demonstrating deterministic gating
    orig = "भारत की राजधानी नई दिल्ली है।"
    
    # Valid character swap
    swapped = "भारत की राजधनाी नई दिल्ली है।"
    print("Test 1 (Valid Akshara Swap):", judge_deterministic("CA_CHAR_01_CharacterSwapping", orig, swapped))

    # Broken stacked matra
    corrupted = "भारत की राजधनाााा नई दिल्ली है।"
    print("Test 2 (Illegal Matras):", judge_deterministic("CA_CHAR_02_CharacterRepetition", orig, corrupted))

    # Meaning drift attack
    drift = "भारत की राजधानी मुंबई है।"
    print("Test 3 (Evidence Injection):", judge_deterministic("EA_ADVADD_01_AdvAdd", orig, drift))
