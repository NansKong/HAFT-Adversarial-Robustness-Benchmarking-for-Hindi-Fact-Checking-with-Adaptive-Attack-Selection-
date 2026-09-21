"""CA_CHAR_05 — Homoglyph Perturbation.

Replaces one character in the claim with a visually identical/near-identical
homoglyph from a curated Unicode confusables table (default: 1 substitution).

The table is language-specific; for Hindi (Devanagari) we ship a small curated
mapping of visually confusable characters. If the language has no table, the
instance is skipped — the spec forbids fabricating homoglyphs heuristically.

Ref: FactEval benchmark; Unicode confusables per UTS #39.
"""

from __future__ import annotations

import common

ATTACK_ID = "CA_CHAR_05_HomoglyphPerturbation"
EDIT_GRANULARITY = "character"

_CONFUSABLES = {
    # Devanagari (Hindi) — visually near-identical pairs. Nukta additions use
    # real Hindi letters (ड़, ज़, फ़, ख़, ग़) that differ only by a dot below.
    "\u0921": "\u0921\u093c",  # ड -> ड़ (nukta, visually near-identical)
    "\u091c": "\u091c\u093c",  # ज -> ज़ (nukta)
    "\u092b": "\u092b\u093c",  # फ -> फ़ (nukta)
    "\u0916": "\u0916\u093c",  # ख -> ख़ (nukta)
    "\u0917": "\u0917\u093c",  # ग -> ग़ (nukta)
    "\u0932": "\u0933",        # ल -> ळ (retroflex la, near-identical glyph)
    # Zero-width confusable injection (invisible, tokenization-breaking)
    "\u093e": "\u093e\u200b",  # aa-matra + ZWS
    "\u093f": "\u093f\u200b",  # i-matra + ZWS
    "\u0940": "\u0940\u200b",  # ii-matra + ZWS
    "\u0941": "\u0941\u200b",  # u-matra + ZWS
    "\u0942": "\u0942\u200b",  # uu-matra + ZWS
    "\u0947": "\u0947\u200b",  # e-matra + ZWS
    "\u0948": "\u0948\u200b",  # ai-matra + ZWS
    "\u094b": "\u094b\u200b",  # o-matra + ZWS
    "\u094c": "\u094c\u200b",  # au-matra + ZWS
}

# Urdu (Perso-Arabic) — positional homoglyphs from Arabic/Persian script
_URDU_CONFUSABLES = {
    "\u06cc": "\u064a",  # yeh -> Arabic yeh
    "\u06a9": "\u0643",  # kaf -> Arabic kaf
    "\u06c1": "\u0647",  # chhoti he -> Arabic heh
}

_CONFUSABLES_BY_LANGUAGE = {
    "hi": _CONFUSABLES,
    "ur": _URDU_CONFUSABLES,
}


def apply(record, homoglyph_budget=1, rng=None):
    claim = record.get("claim") or record.get("claim_text") or ""
    language = common.validate_language(record.get("language"))
    gold_label = record.get("gold_label") or record.get("label")

    if not claim or language is None:
        return common.build_record(
            ATTACK_ID, language, claim, record.get("evidence"), None, None,
            gold_label, "same_as_gold", EDIT_GRANULARITY, None,
            skip_reason="missing_claim_or_unsupported_language",
        )

    table = _CONFUSABLES_BY_LANGUAGE.get(language)
    if not table:
        return common.build_record(
            ATTACK_ID, language, claim, record.get("evidence"), None, None,
            gold_label, "same_as_gold", EDIT_GRANULARITY, None,
            skip_reason=f"missing_confusables_table_for_{language}",
        )

    rng = rng or common.new_rng()
    tokens, _ = common.tokenize(claim)
    applied = 0
    affected_word = None
    result_tokens = list(tokens)

    word_indices = list(range(len(tokens)))
    rng.shuffle(word_indices)

    for idx in word_indices:
        core, lead, trail = common._strip_trailing_punct(tokens[idx])
        candidates = [(i, ch) for i, ch in enumerate(core) if ch in table]
        if not candidates:
            continue

        i, ch = rng.choice(candidates)
        new_core = core[:i] + table[ch] + core[i + 1:]
        result_tokens[idx] = lead + new_core + trail
        applied += 1
        affected_word = core
        if applied >= homoglyph_budget:
            break

    if applied == 0:
        return common.build_record(
            ATTACK_ID, language, claim, record.get("evidence"), None, None,
            gold_label, "same_as_gold", EDIT_GRANULARITY,
            {"substitution_type": "unicode_homoglyph", "substitutions_applied": 0,
             "confusables_source": "curated"},
            skip_reason="no_homoglyph_candidate",
        )

    adversarial_claim = " ".join(result_tokens)
    return common.build_record(
        ATTACK_ID, language, claim, record.get("evidence"),
        adversarial_claim, None,
        gold_label, "same_as_gold", EDIT_GRANULARITY,
        {
            "substitution_type": "unicode_homoglyph",
            "substitutions_applied": applied,
            "affected_word": affected_word,
            "confusables_source": "curated",
        },
    )
