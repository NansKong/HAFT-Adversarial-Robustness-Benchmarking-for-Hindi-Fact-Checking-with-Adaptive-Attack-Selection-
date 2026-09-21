"""Smoke test: apply all 14 rule-based attacks to sample Hindi rows and print results."""

import random
import sys

import common
from attacks import (
    char_swapping, char_repetition, char_insertion, char_deletion, char_homoglyph,
    word_entity_disambiguation, word_jumbling, word_typos,
    word_lexical_substitution, word_synonyms, word_phonetic,
    lexically_informed, evidence_imperceptible, evidence_omission,
)

SAMPLES = [
    {
        "claim": "भारत की राजधानी दिल्ली है।",
        "evidence": "नई दिल्ली भारत की राजधानी है और यहाँ संसद भवन स्थित है।",
        "label": "SUP",
        "language": "hi",
    },
    {
        "claim": "चेन्नई 1996 में तमिलनाडु की राजधानी बनी थी।",
        "evidence": "चेन्नई 1996 से तमिलनाडु की राजधानी है।",
        "label": "SUP",
        "language": "hi",
    },
    {
        "claim": "भारत में हर साल बहुत बड़ा क्रिकेट मैच होता है।",
        "evidence": "भारत में क्रिकेट सबसे लोकप्रिय खेल है।",
        "label": "SUP",
        "language": "hi",
    },
    {
        "claim": "मोबाइल फोन सेहत के लिए अच्छा नहीं है।",
        "evidence": "विशेषज्ञों के अनुसार मोबाइल फोन का अत्यधिक उपयोग सेहत को नुकसान पहुँचा सकता है।",
        "label": "SUP",
        "language": "hi",
    },
    {
        "claim": "वाशिंगटन एक प्रसिद्ध शहर है।",
        "evidence": "वाशिंगटन डी.सी. संयुक्त राज्य अमेरिका की राजधानी है।",
        "label": "SUP",
        "language": "hi",
    },
]

ATTACKS = [
    char_swapping,
    char_repetition,
    char_insertion,
    char_deletion,
    char_homoglyph,
    word_entity_disambiguation,
    word_jumbling,
    word_typos,
    word_lexical_substitution,
    word_synonyms,
    word_phonetic,
    lexically_informed,
    evidence_imperceptible,
    evidence_omission,
]


def main():
    seed = 42
    applied = skipped = 0
    for i, row in enumerate(SAMPLES):
        print(f"\n=== Row {i} | {row['label']} | claim: {row['claim']}")
        for module in ATTACKS:
            rng = random.Random(f"{seed}:{i}:{module.ATTACK_ID}")
            record = module.apply(dict(row), rng=rng)
            if record["skip_reason"]:
                skipped += 1
                print(f"  [SKIP] {record['attack_id']}: {record['skip_reason']}")
                continue
            applied += 1
            adv = record.get("adversarial_claim") or record.get("adversarial_evidence")
            print(f"  [{record['attack_id']}] -> {adv}")
    print(f"\nTotal applied: {applied}, skipped: {skipped}")


if __name__ == "__main__":
    sys.exit(main())
