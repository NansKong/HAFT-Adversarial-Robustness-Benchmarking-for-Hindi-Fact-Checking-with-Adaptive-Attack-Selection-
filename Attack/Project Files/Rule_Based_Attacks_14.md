# Rule-Based Attack Descriptions (14 Attacks)

This file contains 14 rule-based adversarial attack descriptions targeting Automated Fact-Checking (AFC) systems. All attacks are implemented using pure Python code — no GPT/LLM calls needed for attack generation.

**Total attacks:** 14
**Strategy type:** `rule_based` (code only, no GPT)
**API calls per instance:** 2 (verify + judge)

---

# Adversarial Attack Description: Character Swapping

## 1. Metadata

| Field | Value |
|---|---|
| Attack ID | `CA_CHAR_01_CharacterSwapping` |
| Attack Name | Character Swapping |
| Category | `claim_attack` |
| Attack Target | `corrupted_verdict` |
| Edit Granularity | `character` |
| Strategy Type | `rule_based` |
| Access Assumption | black-box (verification + retrieval) |
| Source Paper | (Mamta & Cocarascu, 2025) — FactEval benchmark; catalogued in (Liu et al., 2025) Sec. 5.1.2 |

## 2. Description
This attack perturbs a claim by randomly swapping two adjacent characters within a word. The resulting text remains superficially readable but introduces low-level orthographic noise that can corrupt token representations, causing the fact-checking model to misclassify the claim. It targets the verdict prediction module without requiring access to model internals.

## 3. Preconditions / Required Inputs

| Input | Status | Description |
|---|---|---|
| `claim_text` | **required** | The original claim string to be perturbed. |
| `gold_label` | **required** | Original verdict label (`SUP`, `REF`, or `NEI`). |
| `language` | **required** | ISO 639-1/3 code (must be one of: `hi`, `mni`, `te`, `ur`, `pa`, `ta`, `or`, `ml`). |
| `swap_budget` | optional | Maximum number of adjacent swaps to perform (default: 1 per word). |
| `grapheme_cluster_tool` | optional | Library/tool for Unicode extended grapheme cluster segmentation (strongly recommended). |

## 4. Procedure

1. **Language Detection** — Confirm `language` is in the supported set. If not, skip and log.
2. **Tokenization** — Segment the claim into words (whitespace-delimited tokens).
3. **Candidate Selection** — For each word of length ≥ 3 grapheme clusters, identify all valid adjacent character pairs that can be swapped without producing a visually identical result (e.g., swapping two identical characters is a no-op; skip).
4. **Grapheme-Aware Swap** — Using grapheme-cluster-aware segmentation, select one adjacent pair uniformly at random and swap their positions. Reassemble the word.
   - For abugidas (Devanagari, Telugu, Gurmukhi, Tamil, Odia, Malayalam, Bengali/Meitei Mayek), ensure the swap does not split a conjunct consonant or virama sequence unless the resulting sequence is still valid Unicode. If the swap produces an invalid orthographic cluster, discard and resample.
   - For Urdu (RTL Perso-Arabic), ensure swaps respect cursive joining contexts (initial/medial/final/isolated forms). Do not swap a joining character with a non-joining boundary marker if it breaks word shaping.
5. **Reassembly** — Replace the original word with the swapped version in the claim string. Preserve original whitespace, punctuation, and casing where applicable.
6. **Validity Check (Lightweight)** — Verify the adversarial claim is non-empty and that at least one swap was successfully applied. If zero swaps succeeded, skip the instance.
7. **Output Packaging** — Populate the JSON output schema (Sec. 5) and flag for downstream fluency/label-consistency checks.

## 5. Output Schema (JSON)

```json
{
  "attack_id": "CA_CHAR_01_CharacterSwapping",
  "language": "hi",
  "original_claim": "भारत की राजधानी दिल्ली है।",
  "original_evidence": null,
  "adversarial_claim": "भातर की राजधानी दिल्ली है।",
  "adversarial_evidence": null,
  "gold_label": "SUP",
  "target_label": "same_as_gold",
  "edit_granularity": "character",
  "technique_params": {
    "swap_type": "adjacent",
    "swaps_applied": 1,
    "affected_word": "भारत",
    "grapheme_aware": true
  },
  "validity_flags": {
    "fluency_checked": false,
    "label_consistent": true,
    "meaning_preserved": false
  }
}
```

*Note:* `target_label` is set to `same_as_gold` because this is a *generic* corruption attack: it aims to induce any incorrect verdict flip, not a predetermined label. The evaluation pipeline checks whether `verdict_flipped` is true in Sec. 6B.

## 6A. Implementation Notes *(engineering constraints only)*

| Language | Script | Execution Blockers / Requirements (tooling only) |
|---|---|---|
| Hindi | Devanagari | **Grapheme-cluster-aware segmentation required.** Devanagari uses conjunct consonants (e.g., क्ष, ज्ञ) encoded as consonant + virama + consonant. A naive byte-level swap can split a conjunct, producing invalid orthography (e.g., क ् ष → meaningless glyphs). If `indic-nlp-library`, `regex` with `\X`, or equivalent is unavailable, the agent must **skip** the instance or fallback to a word-level `Typos` attack (CA_WORD_04). |
| Manipuri | Meitei Mayek / Bengali | **Grapheme clustering required.** Bengali script (used in some Manipuri corpora) has similar conjunct behavior to Devanagari. Meitei Mayek has its own conjunct rules. Without a cluster-aware segmenter, skip or fallback to word-level attack. |
| Telugu | Telugu | **Grapheme clustering required.** Telugu forms subscripted conjuncts (e.g., క్ష). Swapping adjacent characters across a subscript boundary can break the glyph cluster. Skip if no Telugu-aware grapheme library is available. |
| Urdu | Perso-Arabic (RTL) | **RTL-safe tokenization + grapheme clustering required.** Urdu is cursive: characters have contextual forms (initial/medial/final/isolated). Adjacent swaps must preserve joining logic. If the toolchain lacks Arabic-script shaping awareness (e.g., `python-bidi`, `pyarabic`, or ICU), **skip** the instance—naive swaps will produce visually broken or unjoining glyphs. |
| Punjabi | Gurmukhi | **Grapheme clustering required.** Gurmukhi uses addak, tippi, and conjuncts. A cluster-aware segmenter is needed to avoid splitting dependent signs from base consonants. Skip if unavailable. |
| Tamil | Tamil | **Grapheme clustering strongly recommended.** Tamil has fewer conjuncts than Devanagari but uses pulli (dot) to suppress inherent vowels. Swapping a pulli away from its consonant changes pronunciation drastically and may produce an invalid cluster. Use cluster segmentation if possible; otherwise skip. |
| Odia | Odia | **Grapheme clustering required.** Odia consonant conjuncts are formed similarly to Bengali/Devanagari. Naive byte swaps split conjuncts. Skip if no Odia-aware segmenter available. |
| Malayalam | Malayalam | **Grapheme clustering required.** Malayalam has complex chillu characters and stacked conjuncts. Chillu letters are atomic grapheme clusters that must not be split. Without `mltokenize` or ICU grapheme breaks, skip. |

### Generic Mechanical Checklist
- **Grapheme-cluster-aware segmentation available?** **REQUIRED** for all languages. If missing → skip or fallback to `CA_WORD_04` (Typos). Do not infer the attack is implausible; log the blocker in Sec. 6B.
- **RTL-safe tokenization/reassembly available?** **REQUIRED** for Urdu only. If missing → skip Urdu instances.
- **Morphological analyzer / stemmer?** Not required for this attack.
- **Synonym / paraphrase resource or LM?** Not required for this attack.
- **Script-specific confusables/homoglyph table?** Not required for this attack (needed for `CA_CHAR_05` and `CA_CHAR_06`).

## 6B. Empirical Outcome *(output — left blank in the template; filled in by the evaluation pipeline)*

```json
{
  "language": "",
  "attack_executed": true,
  "execution_notes": "",
  "verdict_flipped": null,
  "retrieval_disrupted": null,
  "fluency_score": null,
  "human_detectability": null,
  "attack_success_rate": null,
  "notes": ""
}
```

## 7. Success / Validity Criteria

An instance is considered successfully generated and usable for evaluation if and only if:

1. **Structural validity** — The adversarial claim differs from the original claim by exactly one or more adjacent character swaps; no words were added or deleted.
2. **Orthographic validity** — All swapped results produce valid Unicode strings in the target script. Invalid conjunct splits or broken RTL shaping constitute a failed execution, not a valid adversarial instance.
3. **Fluency preservation** — The claim remains a pronounceable/typable string (human detectability should be low; the change should look like a natural typo or OCR error).
4. **Label consistency (input side)** — The gold label of the original claim is preserved in the metadata; the attack does not presuppose a target verdict.
5. **Evaluation metrics** — Success is ultimately measured by:
   - **Potency / Attack Success Rate**: Did the FC model misclassify the swapped claim?
   - **Correctness Rate**: Is the perturbed claim still grammatically coherent and label-consistent from a human perspective?
   - **Resilience**: If the model is resilient, it should maintain the original verdict despite the swap.

## 8. Example

| Field | Original | Adversarial |
|---|---|---|
| Claim | भारत की राजधानी दिल्ली है। | भातर की राजधानी दिल्ली है। |
| Label | SUP → (any flip) | Gold retained as SUP in metadata; target is generic flip |
| Language | Hindi (hi) | Hindi (hi) |
| Edit detail | — | Adjacent swap of `र` and `त` in word `भारत` → `भातर` |

*Rationale:* The swap introduces a plausible orthographic error. A human reader can still infer the intended meaning, but tokenization-based FC models may map the corrupted word to an OOV or incorrect embedding, triggering a verdict flip.

## 9. Failure Modes / Skip Conditions

The agent must **skip** the instance (and log the reason in Sec. 6B `execution_notes`) under the following conditions:

1. **Claim too short** — If the claim contains no word with ≥ 3 grapheme clusters, no valid adjacent swap can be performed.
2. **All swap candidates are no-ops** — If every adjacent pair in every word consists of identical characters (e.g., `दिल्ली` has `ल्ल` but swapping them yields the same string), the attack cannot produce a change.
3. **Missing grapheme cluster support** — If the language requires grapheme-aware segmentation (all 8 languages) and the toolchain lacks it, do not perform a naive byte-level swap. Skip and note `execution_notes`: "Missing grapheme cluster segmenter for {language}."
4. **Invalid orthography after swap** — If the swap produces an invalid Unicode sequence or breaks a mandatory conjunct/RTL join, discard that candidate. If all candidates fail, skip the instance.
5. **Language not in target set** — If `language` is not one of `{hi, mni, te, ur, pa, ta, or, ml}`, skip immediately.

---

# Adversarial Attack Description: Character Repetition

## 1. Metadata

| Field | Value |
|---|---|
| Attack ID | `CA_CHAR_02_CharacterRepetition` |
| Attack Name | Character Repetition |
| Category | `claim_attack` |
| Attack Target | `corrupted_verdict` |
| Edit Granularity | `character` |
| Strategy Type | `rule_based` |
| Access Assumption | black-box (verification + retrieval) |
| Source Paper | (Mamta & Cocarascu, 2025) — FactEval benchmark; catalogued in (Liu et al., 2025) Sec. 5.1.2 |

## 2. Description
This attack duplicates a randomly selected non-initial, non-final character within a word in the claim. The resulting orthographic redundancy corrupts token boundaries and subword segmentation, potentially causing the fact-checking model to misclassify the claim while the text remains superficially readable.

## 3. Preconditions / Required Inputs

| Input | Status | Description |
|---|---|---|
| `claim_text` | **required** | The original claim string to be perturbed. |
| `gold_label` | **required** | Original verdict label (`SUP`, `REF`, or `NEI`). |
| `language` | **required** | ISO 639-1/3 code (must be one of: `hi`, `mni`, `te`, `ur`, `pa`, `ta`, `or`, `ml`). |
| `repetition_budget` | optional | Maximum number of characters to duplicate (default: 1 per claim). |
| `grapheme_cluster_tool` | optional | Library/tool for Unicode extended grapheme cluster segmentation (strongly recommended). |

## 4. Procedure

1. **Language Detection** — Confirm `language` is in the supported set. If not, skip and log.
2. **Tokenization** — Segment the claim into words (whitespace-delimited tokens).
3. **Candidate Selection** — For each word of length ≥ 3 grapheme clusters, identify all non-initial and non-final characters (grapheme clusters) that can be duplicated without producing a visually identical result.
4. **Grapheme-Aware Duplication** — Using grapheme-cluster-aware segmentation, select one candidate uniformly at random and duplicate it immediately after itself. Reassemble the word.
   - For abugidas (Devanagari, Telugu, Gurmukhi, Tamil, Odia, Malayalam, Bengali/Meitei Mayek), ensure the duplication does not split a conjunct consonant or virama sequence. If duplication produces an invalid orthographic cluster, discard and resample.
   - For Urdu (RTL Perso-Arabic), ensure duplication respects cursive joining contexts. Do not duplicate a joining character in a way that breaks word shaping.
5. **Reassembly** — Replace the original word with the duplicated version in the claim string. Preserve original whitespace, punctuation, and casing.
6. **Validity Check** — Verify the adversarial claim is non-empty and that at least one duplication was successfully applied. If zero duplications succeeded, skip the instance.
7. **Output Packaging** — Populate the JSON output schema and flag for downstream checks.

## 5. Output Schema (JSON)

```json
{
  "attack_id": "CA_CHAR_02_CharacterRepetition",
  "language": "hi",
  "original_claim": "भारत की राजधानी दिल्ली है।",
  "original_evidence": null,
  "adversarial_claim": "भार्रत की राजधानी दिल्ली है।",
  "adversarial_evidence": null,
  "gold_label": "SUP",
  "target_label": "same_as_gold",
  "edit_granularity": "character",
  "technique_params": {
    "duplication_type": "internal_character",
    "duplications_applied": 1,
    "affected_word": "भारत",
    "grapheme_aware": true
  },
  "validity_flags": {
    "fluency_checked": false,
    "label_consistent": true,
    "meaning_preserved": false
  }
}
```

## 6A. Implementation Notes *(engineering constraints only)*

| Language | Script | Execution Blockers / Requirements (tooling only) |
|---|---|---|
| Hindi | Devanagari | **Grapheme-cluster-aware segmentation required.** Duplicating a character inside a conjunct (e.g., क्ष → क्ष्ष) may produce invalid orthography. If no segmenter available, skip or fallback to `CA_WORD_04` (Typos). |
| Manipuri | Meitei Mayek / Bengali | **Grapheme clustering required.** Bengali conjuncts and Meitei Mayek clusters must not be split. Skip if no segmenter. |
| Telugu | Telugu | **Grapheme clustering required.** Subscripted conjuncts must remain intact. Skip if unavailable. |
| Urdu | Perso-Arabic (RTL) | **RTL-safe tokenization + grapheme clustering required.** Duplication must preserve joining logic. Skip if no Arabic-script shaping library available. |
| Punjabi | Gurmukhi | **Grapheme clustering required.** Addak, tippi, and conjuncts must not be split. Skip if unavailable. |
| Tamil | Tamil | **Grapheme clustering strongly recommended.** Pulli (dot) must stay attached to its consonant. Skip if no segmenter. |
| Odia | Odia | **Grapheme clustering required.** Conjunct consonants must not be split. Skip if unavailable. |
| Malayalam | Malayalam | **Grapheme clustering required.** Chillu characters and stacked conjuncts are atomic; must not be split. Skip if unavailable. |

### Generic Mechanical Checklist
- **Grapheme-cluster-aware segmentation available?** **REQUIRED** for all languages. If missing → skip or fallback to `CA_WORD_04` (Typos).
- **RTL-safe tokenization/reassembly available?** **REQUIRED** for Urdu only. If missing → skip Urdu instances.
- **Morphological analyzer / stemmer?** Not required.
- **Synonym / paraphrase resource or LM?** Not required.
- **Script-specific confusables/homoglyph table?** Not required (needed for `CA_CHAR_05`).

## 6B. Empirical Outcome *(output — left blank; filled by evaluation pipeline)*

```json
{
  "language": "",
  "attack_executed": true,
  "execution_notes": "",
  "verdict_flipped": null,
  "retrieval_disrupted": null,
  "fluency_score": null,
  "human_detectability": null,
  "attack_success_rate": null,
  "notes": ""
}
```

## 7. Success / Validity Criteria

1. **Structural validity** — The adversarial claim differs from the original by exactly one or more internal character duplications; no words added or deleted.
2. **Orthographic validity** — All duplications produce valid Unicode strings in the target script.
3. **Fluency preservation** — The claim remains pronounceable/typable (low human detectability).
4. **Label consistency (input side)** — Gold label preserved in metadata; attack does not presuppose a target verdict.
5. **Evaluation metrics** — Potency, Correctness Rate, Resilience (see Appendix C.2 of survey).

## 8. Example

| Field | Original | Adversarial |
|---|---|---|
| Claim | भारत की राजधानी दिल्ली है। | भार्रत की राजधानी दिल्ली है। |
| Label | SUP → (any flip) | Gold retained as SUP; target is generic flip |
| Language | Hindi (hi) | Hindi (hi) |
| Edit detail | — | Duplication of `र` in `भारत` → `भार्रत` |

## 9. Failure Modes / Skip Conditions

1. **Claim too short** — No word with ≥ 3 grapheme clusters.
2. **All candidates are no-ops** — Duplicating would produce identical string.
3. **Missing grapheme cluster support** — Skip and log: "Missing grapheme cluster segmenter for {language}."
4. **Invalid orthography after duplication** — If duplication breaks a conjunct/RTL join, discard candidate. If all fail, skip.
5. **Language not in target set** — Skip immediately.

---

# Adversarial Attack Description: Character Insertion

## 1. Metadata

| Field | Value |
|---|---|
| Attack ID | `CA_CHAR_03_CharacterInsertion` |
| Attack Name | Character Insertion |
| Category | `claim_attack` |
| Attack Target | `corrupted_verdict` |
| Edit Granularity | `character` |
| Strategy Type | `rule_based` |
| Access Assumption | black-box (verification + retrieval) |
| Source Paper | (Mamta & Cocarascu, 2025) — FactEval benchmark; catalogued in (Liu et al., 2025) Sec. 5.1.2 |

## 2. Description
This attack selects a non-initial, non-final character within a word and inserts a copy of it immediately after the selected position. The inserted grapheme creates local orthographic noise that can misalign tokenization and embeddings, leading to incorrect verdict predictions while the claim remains superficially readable.

## 3. Preconditions / Required Inputs

| Input | Status | Description |
|---|---|---|
| `claim_text` | **required** | The original claim string to be perturbed. |
| `gold_label` | **required** | Original verdict label (`SUP`, `REF`, or `NEI`). |
| `language` | **required** | ISO 639-1/3 code (must be one of: `hi`, `mni`, `te`, `ur`, `pa`, `ta`, `or`, `ml`). |
| `insertion_budget` | optional | Maximum insertions per claim (default: 1). |
| `grapheme_cluster_tool` | optional | Library/tool for Unicode extended grapheme cluster segmentation (strongly recommended). |

## 4. Procedure

1. **Language Detection** — Confirm `language` is in the supported set. If not, skip and log.
2. **Tokenization** — Segment the claim into words (whitespace-delimited tokens).
3. **Candidate Selection** — For each word of length ≥ 3 grapheme clusters, identify all non-initial and non-final characters.
4. **Grapheme-Aware Insertion** — Select one candidate uniformly at random and insert a copy of the same grapheme immediately after it. Reassemble the word.
   - For abugidas, ensure the insertion does not split a conjunct consonant or virama sequence. If the resulting cluster is invalid, discard and resample.
   - For Urdu, ensure insertion preserves cursive joining contexts.
5. **Reassembly** — Replace the original word in the claim string. Preserve whitespace, punctuation, and casing.
6. **Validity Check** — Verify at least one insertion was successfully applied. If none succeeded, skip.
7. **Output Packaging** — Populate the JSON output schema.

## 5. Output Schema (JSON)

```json
{
  "attack_id": "CA_CHAR_03_CharacterInsertion",
  "language": "te",
  "original_claim": "హైదరాబాద్ తెలంగాణ రాజధాని.",
  "original_evidence": null,
  "adversarial_claim": "హైదరాబాద్ తెలంగాణ రాజధాని.",
  "adversarial_evidence": null,
  "gold_label": "SUP",
  "target_label": "same_as_gold",
  "edit_granularity": "character",
  "technique_params": {
    "insertion_type": "self_character",
    "insertions_applied": 1,
    "affected_word": "రాజధాని",
    "grapheme_aware": true
  },
  "validity_flags": {
    "fluency_checked": false,
    "label_consistent": true,
    "meaning_preserved": false
  }
}
```

## 6A. Implementation Notes *(engineering constraints only)*

| Language | Script | Execution Blockers / Requirements (tooling only) |
|---|---|---|
| Hindi | Devanagari | **Grapheme-cluster-aware segmentation required.** Inserting inside a conjunct can break it. Skip if no segmenter. |
| Manipuri | Meitei Mayek / Bengali | **Grapheme clustering required.** Skip if unavailable. |
| Telugu | Telugu | **Grapheme clustering required.** Subscript conjuncts must stay intact. Skip if unavailable. |
| Urdu | Perso-Arabic (RTL) | **RTL-safe tokenization + grapheme clustering required.** Skip if no shaping library. |
| Punjabi | Gurmukhi | **Grapheme clustering required.** Skip if unavailable. |
| Tamil | Tamil | **Grapheme clustering strongly recommended.** Skip if no segmenter. |
| Odia | Odia | **Grapheme clustering required.** Skip if unavailable. |
| Malayalam | Malayalam | **Grapheme clustering required.** Skip if unavailable. |

### Generic Mechanical Checklist
- **Grapheme-cluster-aware segmentation available?** **REQUIRED** for all languages. If missing → skip or fallback to `CA_WORD_04` (Typos).
- **RTL-safe tokenization/reassembly available?** **REQUIRED** for Urdu only.
- **Morphological analyzer / stemmer?** Not required.
- **Synonym / paraphrase resource or LM?** Not required.
- **Script-specific confusables/homoglyph table?** Not required.

## 6B. Empirical Outcome *(output — left blank; filled by evaluation pipeline)*

```json
{
  "language": "",
  "attack_executed": true,
  "execution_notes": "",
  "verdict_flipped": null,
  "retrieval_disrupted": null,
  "fluency_score": null,
  "human_detectability": null,
  "attack_success_rate": null,
  "notes": ""
}
```

## 7. Success / Validity Criteria

1. **Structural validity** — The adversarial claim differs by one or more internal character insertions.
2. **Orthographic validity** — All insertions produce valid Unicode strings.
3. **Fluency preservation** — The claim remains pronounceable/typable.
4. **Label consistency (input side)** — Gold label preserved; no presupposed target verdict.
5. **Evaluation metrics** — Potency, Correctness Rate, Resilience.

## 8. Example

| Field | Original | Adversarial |
|---|---|---|
| Claim | హైదరాబాద్ తెలంగాణ రాజధాని. | హైదరాబాద్ తెలంగాణ రాజధాని. |
| Label | SUP → (any flip) | Gold retained as SUP; target is generic flip |
| Language | Telugu (te) | Telugu (te) |
| Edit detail | — | Insertion of `ధ` after itself in `రాజధాని` → `రాజధ్ధాని` |

## 9. Failure Modes / Skip Conditions

1. **Claim too short** — No word with ≥ 3 grapheme clusters.
2. **Missing grapheme cluster support** — Skip and log reason.
3. **Invalid orthography after insertion** — If insertion breaks a conjunct/RTL join, discard. If all candidates fail, skip.
4. **Language not in target set** — Skip immediately.

---

# Adversarial Attack Description: Character Deletion

## 1. Metadata

| Field | Value |
|---|---|
| Attack ID | `CA_CHAR_04_CharacterDeletion` |
| Attack Name | Character Deletion |
| Category | `claim_attack` |
| Attack Target | `corrupted_verdict` |
| Edit Granularity | `character` |
| Strategy Type | `rule_based` |
| Access Assumption | black-box (verification + retrieval) |
| Source Paper | (Mamta & Cocarascu, 2025) — FactEval benchmark; catalogued in (Liu et al., 2025) Sec. 5.1.2 |

## 2. Description
This attack randomly deletes a non-initial, non-final character within a word in the claim. The deletion truncates the word and alters its tokenization footprint, which can cause the fact-checking model to fail while human readers often still infer the intended meaning from context.

## 3. Preconditions / Required Inputs

| Input | Status | Description |
|---|---|---|
| `claim_text` | **required** | The original claim string to be perturbed. |
| `gold_label` | **required** | Original verdict label (`SUP`, `REF`, or `NEI`). |
| `language` | **required** | ISO 639-1/3 code (must be one of: `hi`, `mni`, `te`, `ur`, `pa`, `ta`, `or`, `ml`). |
| `deletion_budget` | optional | Maximum deletions per claim (default: 1). |
| `grapheme_cluster_tool` | optional | Library/tool for Unicode extended grapheme cluster segmentation (strongly recommended). |

## 4. Procedure

1. **Language Detection** — Confirm `language` is in the supported set. If not, skip and log.
2. **Tokenization** — Segment the claim into words (whitespace-delimited tokens).
3. **Candidate Selection** — For each word of length ≥ 3 grapheme clusters, identify all non-initial and non-final characters.
4. **Grapheme-Aware Deletion** — Select one candidate uniformly at random and remove it. Reassemble the word.
   - For abugidas, ensure deletion does not leave a dangling virama or broken conjunct. If the resulting sequence is invalid, discard and resample.
   - For Urdu, ensure deletion does not break cursive joining in a way that produces unrenderable text.
5. **Reassembly** — Replace the original word in the claim string. Preserve whitespace, punctuation, and casing.
6. **Validity Check** — Verify at least one deletion was successfully applied. If none succeeded, skip.
7. **Output Packaging** — Populate the JSON output schema.

## 5. Output Schema (JSON)

```json
{
  "attack_id": "CA_CHAR_04_CharacterDeletion",
  "language": "ta",
  "original_claim": "சென்னை தமிழ்நாட்டின் தலைநகரம்.",
  "original_evidence": null,
  "adversarial_claim": "சென்னை தமிழ்நாட்டின் தலநகரம்.",
  "adversarial_evidence": null,
  "gold_label": "SUP",
  "target_label": "same_as_gold",
  "edit_granularity": "character",
  "technique_params": {
    "deletion_type": "internal_character",
    "deletions_applied": 1,
    "affected_word": "தலைநகரம்",
    "grapheme_aware": true
  },
  "validity_flags": {
    "fluency_checked": false,
    "label_consistent": true,
    "meaning_preserved": false
  }
}
```

## 6A. Implementation Notes *(engineering constraints only)*

| Language | Script | Execution Blockers / Requirements (tooling only) |
|---|---|---|
| Hindi | Devanagari | **Grapheme-cluster-aware segmentation required.** Deleting a character from a conjunct may leave a dangling virama. Skip if no segmenter. |
| Manipuri | Meitei Mayek / Bengali | **Grapheme clustering required.** Skip if unavailable. |
| Telugu | Telugu | **Grapheme clustering required.** Skip if unavailable. |
| Urdu | Perso-Arabic (RTL) | **RTL-safe tokenization + grapheme clustering required.** Skip if no shaping library. |
| Punjabi | Gurmukhi | **Grapheme clustering required.** Skip if unavailable. |
| Tamil | Tamil | **Grapheme clustering strongly recommended.** Deleting a pulli leaves a bare consonant; this is valid but changes meaning. Skip if no segmenter. |
| Odia | Odia | **Grapheme clustering required.** Skip if unavailable. |
| Malayalam | Malayalam | **Grapheme clustering required.** Skip if unavailable. |

### Generic Mechanical Checklist
- **Grapheme-cluster-aware segmentation available?** **REQUIRED** for all languages. If missing → skip or fallback to `CA_WORD_04` (Typos).
- **RTL-safe tokenization/reassembly available?** **REQUIRED** for Urdu only.
- **Morphological analyzer / stemmer?** Not required.
- **Synonym / paraphrase resource or LM?** Not required.
- **Script-specific confusables/homoglyph table?** Not required.

## 6B. Empirical Outcome *(output — left blank; filled by evaluation pipeline)*

```json
{
  "language": "",
  "attack_executed": true,
  "execution_notes": "",
  "verdict_flipped": null,
  "retrieval_disrupted": null,
  "fluency_score": null,
  "human_detectability": null,
  "attack_success_rate": null,
  "notes": ""
}
```

## 7. Success / Validity Criteria

1. **Structural validity** — The adversarial claim differs by one or more internal character deletions.
2. **Orthographic validity** — No dangling viramas or broken RTL joins remain.
3. **Fluency preservation** — The claim remains partially readable; human detectability should be low-to-moderate.
4. **Label consistency (input side)** — Gold label preserved; no presupposed target verdict.
5. **Evaluation metrics** — Potency, Correctness Rate, Resilience.

## 8. Example

| Field | Original | Adversarial |
|---|---|---|
| Claim | சென்னை தமிழ்நாட்டின் தலைநகரம். | சென்னை தமிழ்நாட்டின் தலநகரம். |
| Label | SUP → (any flip) | Gold retained as SUP; target is generic flip |
| Language | Tamil (ta) | Tamil (ta) |
| Edit detail | — | Deletion of `ை` from `தலைநகரம்` → `தலநகரம்` |

## 9. Failure Modes / Skip Conditions

1. **Claim too short** — No word with ≥ 3 grapheme clusters.
2. **Missing grapheme cluster support** — Skip and log reason.
3. **Invalid orthography after deletion** — If deletion leaves dangling marks or broken joins, discard candidate. If all fail, skip.
4. **Language not in target set** — Skip immediately.

---

# Adversarial Attack Description: Homoglyph Perturbation

## 1. Metadata

| Field | Value |
|---|---|
| Attack ID | `CA_CHAR_05_HomoglyphPerturbation` |
| Attack Name | Homoglyph Perturbation |
| Category | `claim_attack` |
| Attack Target | `corrupted_verdict` |
| Edit Granularity | `character` |
| Strategy Type | `rule_based` |
| Access Assumption | black-box (verification + retrieval) |
| Source Paper | (Mamta & Cocarascu, 2025) — FactEval benchmark; catalogued in (Liu et al., 2025) Sec. 5.1.2. Unicode confusables reference: Unicode Security Mechanisms (UTS #39) |

## 2. Description
This attack replaces characters in the claim with visually identical or near-identical homoglyphs drawn from the Unicode Security dictionary. Because the substituted code points map to different tokens or are unrecognized by the model's tokenizer, the claim's representation is corrupted while appearing unchanged to human readers.

## 3. Preconditions / Required Inputs

| Input | Status | Description |
|---|---|---|
| `claim_text` | **required** | The original claim string to be perturbed. |
| `gold_label` | **required** | Original verdict label (`SUP`, `REF`, or `NEI`). |
| `language` | **required** | ISO 639-1/3 code (must be one of: `hi`, `mni`, `te`, `ur`, `pa`, `ta`, `or`, `ml`). |
| `homoglyph_budget` | optional | Maximum number of homoglyph substitutions (default: 1 per word). |
| `unicode_confusables_table` | **required** | A mapping from base characters to their Unicode confusable homoglyphs for the target script. |

## 4. Procedure

1. **Language Detection** — Confirm `language` is in the supported set. If not, skip and log.
2. **Load Confusables** — Load the script-specific confusables table. If no table exists for the target script, skip and log.
3. **Tokenization** — Segment the claim into words (whitespace-delimited tokens).
4. **Candidate Selection** — For each word, identify characters that have at least one homoglyph entry in the confusables table.
5. **Substitution** — Select one candidate character uniformly at random and replace it with its homoglyph. Reassemble the word.
   - For abugidas, avoid substituting a base consonant with a homoglyph that is actually a dependent vowel or combining mark, as this breaks rendering.
   - For Urdu, ensure the homoglyph preserves cursive joining behavior where applicable.
6. **Reassembly** — Replace the original word in the claim string. Preserve whitespace, punctuation, and casing.
7. **Validity Check** — Verify at least one substitution was applied and that the resulting string is valid Unicode. If none succeeded, skip.
8. **Output Packaging** — Populate the JSON output schema.

## 5. Output Schema (JSON)

```json
{
  "attack_id": "CA_CHAR_05_HomoglyphPerturbation",
  "language": "ur",
  "original_claim": "اسلام آباد پاکستان کا دارالحکومت ہے۔",
  "original_evidence": null,
  "adversarial_claim": "اسلام آباد پاکستان کا دارالحکومت ہے۔",
  "adversarial_evidence": null,
  "gold_label": "SUP",
  "target_label": "same_as_gold",
  "edit_granularity": "character",
  "technique_params": {
    "substitution_type": "unicode_homoglyph",
    "substitutions_applied": 1,
    "affected_word": "پاکستان",
    "confusables_source": "UTS39"
  },
  "validity_flags": {
    "fluency_checked": false,
    "label_consistent": true,
    "meaning_preserved": false
  }
}
```

## 6A. Implementation Notes *(engineering constraints only)*

| Language | Script | Execution Blockers / Requirements (tooling only) |
|---|---|---|
| Hindi | Devanagari | **Script-specific confusables table required.** Devanagari has few Latin-style homoglyphs, but digits and some punctuation may have confusables. If no table available, skip. |
| Manipuri | Meitei Mayek / Bengali | **Script-specific confusables table required.** Skip if no table. |
| Telugu | Telugu | **Script-specific confusables table required.** Skip if no table. |
| Urdu | Perso-Arabic (RTL) | **Script-specific confusables table + RTL shaping check required.** Arabic script has many positional homoglyphs; ensure the replacement preserves joining context. Skip if no table. |
| Punjabi | Gurmukhi | **Script-specific confusables table required.** Skip if no table. |
| Tamil | Tamil | **Script-specific confusables table required.** Skip if no table. |
| Odia | Odia | **Script-specific confusables table required.** Skip if no table. |
| Malayalam | Malayalam | **Script-specific confusables table required.** Skip if no table. |

### Generic Mechanical Checklist
- **Grapheme-cluster-aware segmentation available?** Recommended but not strictly required if substitutions are on standalone characters.
- **RTL-safe tokenization/reassembly available?** **REQUIRED** for Urdu only.
- **Morphological analyzer / stemmer?** Not required.
- **Synonym / paraphrase resource or LM?** Not required.
- **Script-specific confusables/homoglyph table?** **REQUIRED** for all languages. If missing → skip. Do not attempt to fabricate homoglyphs heuristically.

## 6B. Empirical Outcome *(output — left blank; filled by evaluation pipeline)*

```json
{
  "language": "",
  "attack_executed": true,
  "execution_notes": "",
  "verdict_flipped": null,
  "retrieval_disrupted": null,
  "fluency_score": null,
  "human_detectability": null,
  "attack_success_rate": null,
  "notes": ""
}
```

## 7. Success / Validity Criteria

1. **Structural validity** — The adversarial claim differs by one or more homoglyph substitutions.
2. **Visual plausibility** — The substituted character should be visually identical or nearly identical to the original in the target font.
3. **Tokenization impact** — The substitution should map to a different code point (and ideally a different token ID) to corrupt model input.
4. **Label consistency (input side)** — Gold label preserved; no presupposed target verdict.
5. **Evaluation metrics** — Potency, Correctness Rate, Resilience, Human Detectability (should be very low).

## 8. Example

| Field | Original | Adversarial |
|---|---|---|
| Claim | اسلام آباد پاکستان کا دارالحکومت ہے۔ | اسلام آباد پاکستان کا دارالحکومت ہے۔ |
| Label | SUP → (any flip) | Gold retained as SUP; target is generic flip |
| Language | Urdu (ur) | Urdu (ur) |
| Edit detail | — | Homoglyph substitution in `پاکستان` (e.g., replacing a joining character with a visually similar Arabic code point) |

## 9. Failure Modes / Skip Conditions

1. **No confusables table** — Skip and log: "Missing confusables table for {language}."
2. **No applicable candidates** — If no character in the claim has a known homoglyph, skip.
3. **Substitution breaks rendering** — If the homoglyph breaks a conjunct or RTL join, discard candidate. If all fail, skip.
4. **Language not in target set** — Skip immediately.

---

# Adversarial Attack Description: Jumbling

## 1. Metadata

| Field | Value |
|---|---|
| Attack ID | `CA_WORD_03_Jumbling` |
| Attack Name | Jumbling |
| Category | `claim_attack` |
| Attack Target | `corrupted_verdict` |
| Edit Granularity | `word` |
| Strategy Type | `rule_based` |
| Access Assumption | black-box (verification + retrieval) |
| Source Paper | (Mamta & Cocarascu, 2025) — FactEval benchmark; catalogued in (Liu et al., 2025) Sec. 5.1.2 |

## 2. Description
This attack perturbs a claim by randomly changing the order of its words. The bag-of-words content is preserved, but syntactic structure is destroyed. It tests whether the fact-checking model relies on word-order cues and grammatical structure or merely on shallow lexical overlap with evidence.

## 3. Preconditions / Required Inputs

| Input | Status | Description |
|---|---|---|
| `claim_text` | **required** | The original claim string to be perturbed. |
| `gold_label` | **required** | Original verdict label (SUP, REF, or NEI). |
| `language` | **required** | ISO 639-1/3 code (must be one of: hi, mni, te, ur, pa, ta, or, ml). |
| `tokenizer` | optional | Word tokenizer for the target language. |

## 4. Procedure

1. **Language Detection** — Confirm `language` is in the supported set. If not, skip and log.
2. **Tokenization** — Split the claim into a list of words (whitespace-delimited). Preserve punctuation as separate tokens or attach them consistently.
3. **Shuffle** — Randomly shuffle the word list using a uniform random permutation.
4. **Reassembly** — Join the shuffled words with single spaces to form the adversarial claim.
   - For Urdu (RTL), ensure the overall text direction remains RTL; individual words retain internal order.
5. **Validity Check** — Verify the adversarial claim differs from the original. If the shuffle reproduces the original order, reshuffle or skip.
6. **Output Packaging** — Populate the JSON output schema.

## 5. Output Schema (JSON)

```json
{
  "attack_id": "CA_WORD_03_Jumbling",
  "language": "te",
  "original_claim": "హైదరాబాద్ తెలంగాణ రాజధాని.",
  "original_evidence": null,
  "adversarial_claim": "రాజధాని తెలంగాణ హైదరాబాద్.",
  "adversarial_evidence": null,
  "gold_label": "SUP",
  "target_label": "same_as_gold",
  "edit_granularity": "word",
  "technique_params": {
    "shuffle_type": "uniform_random",
    "word_order_preserved": false
  },
  "validity_flags": {
    "fluency_checked": false,
    "label_consistent": true,
    "meaning_preserved": false
  }
}
```

## 6A. Implementation Notes

| Language | Script | Execution Blockers / Requirements (tooling only) |
|---|---|---|
| Hindi | Devanagari | **Word tokenizer required.** Whitespace tokenization is sufficient. |
| Manipuri | Meitei Mayek / Bengali | **Word tokenizer required.** Whitespace tokenization is sufficient. |
| Telugu | Telugu | **Word tokenizer required.** Whitespace tokenization is sufficient. |
| Urdu | Perso-Arabic (RTL) | **RTL-safe reassembly required.** Shuffling must not break individual word shapes. |
| Punjabi | Gurmukhi | **Word tokenizer required.** Whitespace tokenization is sufficient. |
| Tamil | Tamil | **Word tokenizer required.** Whitespace tokenization is sufficient. |
| Odia | Odia | **Word tokenizer required.** Whitespace tokenization is sufficient. |
| Malayalam | Malayalam | **Word tokenizer required.** Whitespace tokenization is sufficient. |

### Generic Mechanical Checklist
- **RTL-safe tokenization/reassembly available?** Recommended for Urdu only.

## 6B. Empirical Outcome

```json
{
  "language": "",
  "attack_executed": true,
  "execution_notes": "",
  "verdict_flipped": null,
  "retrieval_disrupted": null,
  "fluency_score": null,
  "human_detectability": null,
  "attack_success_rate": null,
  "notes": ""
}
```

## 7. Success / Validity Criteria

1. **Structural validity** — All original words are preserved exactly; only their order changes.
2. **Syntactic disruption** — The shuffled claim should be grammatically incorrect.
3. **Label consistency (input side)** — Gold label preserved; no presupposed target verdict.
4. **Evaluation metrics** — Potency, Correctness Rate, Resilience.

## 8. Example

| Field | Original | Adversarial |
|---|---|---|
| Claim | హైదరాబాద్ తెలంగాణ రాజధాని. | రాజధాని తెలంగాణ హైదరాబాద్. |
| Label | SUP -> (any flip) | Gold retained as SUP; target is generic flip |
| Language | Telugu (te) | Telugu (te) |
| Edit detail | — | Uniform random shuffle of word order |

## 9. Failure Modes / Skip Conditions

1. **Claim too short** — If the claim has fewer than 3 words, skip.
2. **Shuffle reproduces original** — If the random permutation yields the original order, reshuffle once; if it persists, skip.
3. **Language not in target set** — Skip immediately.

---

# Adversarial Attack Description: Typos

## 1. Metadata

| Field | Value |
|---|---|
| Attack ID | `CA_WORD_04_Typos` |
| Attack Name | Typos |
| Category | `claim_attack` |
| Attack Target | `corrupted_verdict` |
| Edit Granularity | `word` |
| Strategy Type | `rule_based` |
| Access Assumption | black-box (verification + retrieval) |
| Source Paper | (Mamta & Cocarascu, 2025) — FactEval benchmark; catalogued in (Liu et al., 2025) Sec. 5.1.2 |

## 2. Description
This attack introduces common typographical errors at the word level by replacing words with their frequent misspellings or keyboard-proximity variants. Unlike character-level swapping, it operates on whole-word substitutions drawn from a typo dictionary, preserving the intended meaning to a human reader while corrupting exact-match tokenization.

## 3. Preconditions / Required Inputs

| Input | Status | Description |
|---|---|---|
| `claim_text` | **required** | The original claim string to be perturbed. |
| `gold_label` | **required** | Original verdict label (SUP, REF, or NEI). |
| `language` | **required** | ISO 639-1/3 code (must be one of: hi, mni, te, ur, pa, ta, or, ml). |
| `typo_dictionary` | **required** | A mapping from correctly spelled words to common misspellings for the target language/script. |

## 4. Procedure

1. **Language Detection** — Confirm `language` is in the supported set. If not, skip and log.
2. **Load Typo Dictionary** — Load the language-specific typo dictionary. If no dictionary exists, skip and log.
3. **Candidate Scan** — Scan the claim for words that appear as keys in the typo dictionary.
   - If no candidates are found, skip the instance.
4. **Substitution** — Select one candidate word uniformly at random and replace it with one of its listed misspellings.
5. **Reassembly** — Reconstruct the claim string. Preserve surrounding whitespace and punctuation.
6. **Validity Check** — Verify the claim text has changed. If no substitution was applied, skip.
7. **Output Packaging** — Populate the JSON output schema.

## 5. Output Schema (JSON)

```json
{
  "attack_id": "CA_WORD_04_Typos",
  "language": "hi",
  "original_claim": "भारत की राजधानी दिल्ली है।",
  "original_evidence": null,
  "adversarial_claim": "भारत की राजधानी दिल्ली है।",
  "adversarial_evidence": null,
  "gold_label": "SUP",
  "target_label": "same_as_gold",
  "edit_granularity": "word",
  "technique_params": {
    "substitution_type": "typo_dictionary",
    "original_word": "दिल्ली",
    "typo_variant": "दिल्ली",
    "typos_applied": 1
  },
  "validity_flags": {
    "fluency_checked": false,
    "label_consistent": true,
    "meaning_preserved": false
  }
}
```

## 6A. Implementation Notes

| Language | Script | Execution Blockers / Requirements (tooling only) |
|---|---|---|
| Hindi | Devanagari | **Typo dictionary required.** If no curated typo list, skip. |
| Manipuri | Meitei Mayek / Bengali | **Typo dictionary required.** If no dictionary, skip. |
| Telugu | Telugu | **Typo dictionary required.** If no dictionary, skip. |
| Urdu | Perso-Arabic (RTL) | **Typo dictionary required.** If no dictionary, skip. |
| Punjabi | Gurmukhi | **Typo dictionary required.** If no dictionary, skip. |
| Tamil | Tamil | **Typo dictionary required.** If no dictionary, skip. |
| Odia | Odia | **Typo dictionary required.** If no dictionary, skip. |
| Malayalam | Malayalam | **Typo dictionary required.** If no dictionary, skip. |

### Generic Mechanical Checklist
- **Typo dictionary for the language?** **REQUIRED.** If missing -> skip.

## 6B. Empirical Outcome

```json
{
  "language": "",
  "attack_executed": true,
  "execution_notes": "",
  "verdict_flipped": null,
  "retrieval_disrupted": null,
  "fluency_score": null,
  "human_detectability": null,
  "attack_success_rate": null,
  "notes": ""
}
```

## 7. Success / Validity Criteria

1. **Structural validity** — Only words present in the typo dictionary are modified.
2. **Fluency preservation** — The typo variant should be a plausible human misspelling.
3. **Label consistency (input side)** — Gold label preserved; no presupposed target verdict.
4. **Evaluation metrics** — Potency, Correctness Rate, Resilience.

## 8. Example

| Field | Original | Adversarial |
|---|---|---|
| Claim | भारत की राजधानी दिल्ली है। | भारत की राजधानी दिल्ली है। |
| Label | SUP -> (any flip) | Gold retained as SUP; target is generic flip |
| Language | Hindi (hi) | Hindi (hi) |
| Edit detail | — | Typo substitution in word "दिल्ली" |

## 9. Failure Modes / Skip Conditions

1. **No typo dictionary** — Skip and log: "Missing typo dictionary for {language}."
2. **No applicable words** — If no word in the claim matches a dictionary key, skip.
3. **Language not in target set** — Skip immediately.

---

# Adversarial Attack Description: Lexical Substitution

## 1. Metadata

| Field | Value |
|---|---|
| Attack ID | `CA_WORD_08_LexicalSubstitution` |
| Attack Name | Lexical Substitution |
| Category | `claim_attack` |
| Attack Target | `corrupted_verdict` |
| Edit Granularity | `word` |
| Strategy Type | `rule_based` |
| Access Assumption | black-box (verification + retrieval) |
| Source Paper | (Hidey et al., 2020) — DeSePtion; benchmarked in (Mamta & Cocarascu, 2025); catalogued in (Liu et al., 2025) Sec. 5.1.2 |

## 2. Description
This attack manipulates claims by replacing content words with their synonyms, hypernyms, or hyponyms. By altering the surface lexical form while preserving the underlying semantic proposition, it tests whether the fact-checking model relies on specific keyword matching rather than deep semantic understanding.

## 3. Preconditions / Required Inputs

| Input | Status | Description |
|---|---|---|
| `claim_text` | **required** | The original claim string to be perturbed. |
| `gold_label` | **required** | Original verdict label (SUP, REF, or NEI). |
| `language` | **required** | ISO 639-1/3 code (must be one of: hi, mni, te, ur, pa, ta, or, ml). |
| `lexical_resource` | **required** | A WordNet-style or comparable lexical database providing synonyms, hypernyms, and hyponyms for the target language. |
| `pos_tagger` | optional | POS tagger to identify nouns, verbs, and adjectives for substitution. |

## 4. Procedure

1. **Language Detection** — Confirm `language` is in the supported set. If not, skip and log.
2. **Load Lexical Resource** — Load the synonym/hypernym/hyponym database for the target language. If no resource exists, skip and log.
3. **POS Tagging (Optional)** — If a POS tagger is available, identify content words. If no POS tagger, consider all non-stopwords as candidates.
4. **Candidate Selection** — For each candidate word, look up its synonyms, hypernyms, and hyponyms.
   - If no candidate has any valid substitution, skip the instance.
5. **Substitution** — Select one candidate and one of its valid substitutions uniformly at random. Replace the original word.
6. **Reassembly** — Reconstruct the claim string. Preserve surrounding whitespace and punctuation.
7. **Validity Check** — Verify the claim text has changed. If no substitution was applied, skip.
8. **Output Packaging** — Populate the JSON output schema.

## 5. Output Schema (JSON)

```json
{
  "attack_id": "CA_WORD_08_LexicalSubstitution",
  "language": "hi",
  "original_claim": "भारत की राजधानी दिल्ली है।",
  "original_evidence": null,
  "adversarial_claim": "भारत की मुख्यालय दिल्ली है।",
  "adversarial_evidence": null,
  "gold_label": "SUP",
  "target_label": "same_as_gold",
  "edit_granularity": "word",
  "technique_params": {
    "substitution_type": "synonym",
    "original_word": "राजधानी",
    "substituted_word": "मुख्यालय",
    "lexical_resource": "IndoWordNet"
  },
  "validity_flags": {
    "fluency_checked": false,
    "label_consistent": true,
    "meaning_preserved": false
  }
}
```

## 6A. Implementation Notes

| Language | Script | Execution Blockers / Requirements (tooling only) |
|---|---|---|
| Hindi | Devanagari | **Lexical resource required.** IndoWordNet or similar Hindi WordNet needed. If unavailable, skip. |
| Manipuri | Meitei Mayek / Bengali | **Lexical resource required.** If no WordNet or synonym lexicon, skip. |
| Telugu | Telugu | **Lexical resource required.** If no Telugu WordNet, skip. |
| Urdu | Perso-Arabic (RTL) | **Lexical resource required.** If no Urdu WordNet, skip. |
| Punjabi | Gurmukhi | **Lexical resource required.** If no Punjabi WordNet, skip. |
| Tamil | Tamil | **Lexical resource required.** Tamil WordNet exists; if unavailable, skip. |
| Odia | Odia | **Lexical resource required.** If no Odia WordNet, skip. |
| Malayalam | Malayalam | **Lexical resource required.** Malayalam WordNet exists; if unavailable, skip. |

### Generic Mechanical Checklist
- **Synonym / paraphrase resource or LM?** **REQUIRED** (WordNet or equivalent). If missing -> skip.

## 6B. Empirical Outcome

```json
{
  "language": "",
  "attack_executed": true,
  "execution_notes": "",
  "verdict_flipped": null,
  "retrieval_disrupted": null,
  "fluency_score": null,
  "human_detectability": null,
  "attack_success_rate": null,
  "notes": ""
}
```

## 7. Success / Validity Criteria

1. **Structural validity** — Only one content word is replaced by a lexical substitute.
2. **Semantic preservation** — The substitute should be a synonym, hypernym, or hyponym of the original.
3. **Fluency preservation** — The claim should remain grammatically correct.
4. **Label consistency (input side)** — Gold label preserved; no presupposed target verdict.
5. **Evaluation metrics** — Potency, Correctness Rate, Resilience.

## 8. Example

| Field | Original | Adversarial |
|---|---|---|
| Claim | भारत की राजधानी दिल्ली है। | भारत की मुख्यालय दिल्ली है। |
| Label | SUP -> (any flip) | Gold retained as SUP; target is generic flip |
| Language | Hindi (hi) | Hindi (hi) |
| Edit detail | — | Lexical substitution: "राजधानी" -> "मुख्यालय" (synonym) |

## 9. Failure Modes / Skip Conditions

1. **No lexical resource** — Skip and log: "Missing lexical resource for {language}."
2. **No applicable candidates** — If no word in the claim has a synonym/hypernym/hyponym, skip.
3. **Substitution breaks grammar** — If the substitute does not fit grammatically, discard and try another. If all fail, skip.
4. **Language not in target set** — Skip immediately.

---

# Adversarial Attack Description: Synonyms

## 1. Metadata

| Field | Value |
|---|---|
| Attack ID | `CA_WORD_12_Synonyms` |
| Attack Name | Synonyms |
| Category | `claim_attack` |
| Attack Target | `corrupted_verdict` |
| Edit Granularity | `word` |
| Strategy Type | `rule_based` |
| Access Assumption | black-box (verification + retrieval) |
| Source Paper | (Mamta & Cocarascu, 2025) — FactEval benchmark; catalogued in (Liu et al., 2025) Sec. 5.1.2 |

## 2. Description
This attack manipulates claims by replacing adjectives with their synonyms from a lexical resource such as WordNet. It is a narrower variant of Lexical Substitution focused specifically on adjectival content, testing whether the model relies on exact adjective matches rather than compositional semantics.

## 3. Preconditions / Required Inputs

| Input | Status | Description |
|---|---|---|
| `claim_text` | **required** | The original claim string to be perturbed. |
| `gold_label` | **required** | Original verdict label (SUP, REF, or NEI). |
| `language` | **required** | ISO 639-1/3 code (must be one of: hi, mni, te, ur, pa, ta, or, ml). |
| `lexical_resource` | **required** | A WordNet-style database providing adjective synonyms for the target language. |
| `pos_tagger` | optional | POS tagger to identify adjectives. If unavailable, use the lexical resource to filter candidate words. |

## 4. Procedure

1. **Language Detection** — Confirm `language` is in the supported set. If not, skip and log.
2. **Load Lexical Resource** — Load the synonym database for the target language. If no resource exists, skip and log.
3. **Adjective Identification** — If a POS tagger is available, tag the claim and identify adjectives. If no tagger, query the lexical resource for each word to find adjective entries.
   - If no adjectives are found, skip the instance.
4. **Candidate Selection** — For each identified adjective, look up its synonyms in the lexical resource.
   - If no adjective has any valid synonym, skip the instance.
5. **Substitution** — Select one adjective and one of its synonyms uniformly at random. Replace the original adjective.
6. **Reassembly** — Reconstruct the claim string. Preserve surrounding whitespace and punctuation.
7. **Validity Check** — Verify the claim text has changed. If no substitution was applied, skip.
8. **Output Packaging** — Populate the JSON output schema.

## 5. Output Schema (JSON)

```json
{
  "attack_id": "CA_WORD_12_Synonyms",
  "language": "hi",
  "original_claim": "भारत एक बड़ा देश है।",
  "original_evidence": null,
  "adversarial_claim": "भारत एक विशाल देश है।",
  "adversarial_evidence": null,
  "gold_label": "SUP",
  "target_label": "same_as_gold",
  "edit_granularity": "word",
  "technique_params": {
    "substitution_type": "adjective_synonym",
    "original_word": "बड़ा",
    "substituted_word": "विशाल",
    "lexical_resource": "IndoWordNet"
  },
  "validity_flags": {
    "fluency_checked": false,
    "label_consistent": true,
    "meaning_preserved": false
  }
}
```

## 6A. Implementation Notes

| Language | Script | Execution Blockers / Requirements (tooling only) |
|---|---|---|
| Hindi | Devanagari | **Lexical resource required.** IndoWordNet or similar Hindi WordNet needed for adjective synonyms. If unavailable, skip. |
| Manipuri | Meitei Mayek / Bengali | **Lexical resource required.** If no adjective synonym lexicon, skip. |
| Telugu | Telugu | **Lexical resource required.** If no Telugu WordNet, skip. |
| Urdu | Perso-Arabic (RTL) | **Lexical resource required.** If no Urdu WordNet, skip. |
| Punjabi | Gurmukhi | **Lexical resource required.** If no Punjabi WordNet, skip. |
| Tamil | Tamil | **Lexical resource required.** Tamil WordNet exists; if unavailable, skip. |
| Odia | Odia | **Lexical resource required.** If no Odia WordNet, skip. |
| Malayalam | Malayalam | **Lexical resource required.** Malayalam WordNet exists; if unavailable, skip. |

### Generic Mechanical Checklist
- **Synonym / paraphrase resource or LM?** **REQUIRED** (WordNet or equivalent with adjective coverage). If missing -> skip.

## 6B. Empirical Outcome

```json
{
  "language": "",
  "attack_executed": true,
  "execution_notes": "",
  "verdict_flipped": null,
  "retrieval_disrupted": null,
  "fluency_score": null,
  "human_detectability": null,
  "attack_success_rate": null,
  "notes": ""
}
```

## 7. Success / Validity Criteria

1. **Structural validity** — Only one adjective is replaced by a synonym.
2. **Semantic preservation** — The substitute should be a true synonym of the original adjective in the target language.
3. **Fluency preservation** — The claim should remain grammatically correct after substitution.
4. **Label consistency (input side)** — Gold label preserved; no presupposed target verdict.
5. **Evaluation metrics** — Potency, Correctness Rate, Resilience.

## 8. Example

| Field | Original | Adversarial |
|---|---|---|
| Claim | भारत एक बड़ा देश है। | भारत एक विशाल देश है। |
| Label | SUP -> (any flip) | Gold retained as SUP; target is generic flip |
| Language | Hindi (hi) | Hindi (hi) |
| Edit detail | — | Adjective synonym: "बड़ा" -> "विशाल" |

## 9. Failure Modes / Skip Conditions

1. **No lexical resource** — Skip and log: "Missing lexical resource for {language}."
2. **No adjectives found** — If no adjective is identified in the claim, skip.
3. **No applicable synonyms** — If no adjective has a synonym in the resource, skip.
4. **Substitution breaks grammar** — If the synonym does not fit grammatically (e.g., gender/number mismatch), discard and try another. If all fail, skip.
5. **Language not in target set** — Skip immediately.

---

# Adversarial Attack Description: Phonetic Perturbation

## 1. Metadata

| Field | Value |
|---|---|
| Attack ID | `CA_WORD_13_PhoneticPerturbation` |
| Attack Name | Phonetic Perturbation |
| Category | `claim_attack` |
| Attack Target | `corrupted_verdict` |
| Edit Granularity | `word` |
| Strategy Type | `rule_based` |
| Access Assumption | black-box (verification + retrieval) |
| Source Paper | (Mamta & Cocarascu, 2025) — FactEval benchmark; catalogued in (Liu et al., 2025) Sec. 5.1.2 |

## 2. Description
This attack applies phonetic perturbations using a human-written dictionary with a word-level perturbation budget. It replaces words with phonetically similar alternatives that are spelled differently, exploiting the gap between phonetic and orthographic representations in fact-checking models.

## 3. Preconditions / Required Inputs

| Input | Status | Description |
|---|---|---|
| `claim_text` | **required** | The original claim string to be perturbed. |
| `gold_label` | **required** | Original verdict label (SUP, REF, or NEI). |
| `language` | **required** | ISO 639-1/3 code (must be one of: hi, mni, te, ur, pa, ta, or, ml). |
| `phonetic_dictionary` | **required** | A mapping from words to their phonetically similar spelling variants for the target language. |
| `perturbation_budget` | optional | Maximum number of words to perturb (default: 1). |

## 4. Procedure

1. **Language Detection** — Confirm `language` is in the supported set. If not, skip and log.
2. **Load Phonetic Dictionary** — Load the phonetic mapping for the target language. If no dictionary exists, skip and log.
3. **Candidate Scan** — Scan the claim for words that appear as keys in the phonetic dictionary.
   - If no candidates are found, skip the instance.
4. **Substitution** — Select up to `perturbation_budget` candidates uniformly at random and replace each with one of its phonetic variants (randomly chosen if multiple exist).
5. **Reassembly** — Reconstruct the claim string. Preserve surrounding whitespace and punctuation.
6. **Validity Check** — Verify the claim text has changed. If no substitution was applied, skip.
7. **Output Packaging** — Populate the JSON output schema.

## 5. Output Schema (JSON)

```json
{
  "attack_id": "CA_WORD_13_PhoneticPerturbation",
  "language": "pa",
  "original_claim": "ਅੰਮ੍ਰਿਤਸਰ ਪੰਜਾਬ ਦਾ ਸ਼ਹਿਰ ਹੈ।",
  "original_evidence": null,
  "adversarial_claim": "ਅੰਮ੍ਰਿਤਸਰ ਪੰਜਾਬ ਦਾ ਸਹਿਰ ਹੈ।",
  "adversarial_evidence": null,
  "gold_label": "SUP",
  "target_label": "same_as_gold",
  "edit_granularity": "word",
  "technique_params": {
    "substitution_type": "phonetic_variant",
    "original_word": "ਸ਼ਹਿਰ",
    "phonetic_variant": "ਸਹਿਰ",
    "perturbations_applied": 1
  },
  "validity_flags": {
    "fluency_checked": false,
    "label_consistent": true,
    "meaning_preserved": false
  }
}
```

## 6A. Implementation Notes

| Language | Script | Execution Blockers / Requirements (tooling only) |
|---|---|---|
| Hindi | Devanagari | **Phonetic dictionary required.** Must map Hindi words to phonetically similar but orthographically distinct variants. If unavailable, skip. |
| Manipuri | Meitei Mayek / Bengali | **Phonetic dictionary required.** If no dictionary, skip. |
| Telugu | Telugu | **Phonetic dictionary required.** If no dictionary, skip. |
| Urdu | Perso-Arabic (RTL) | **Phonetic dictionary required.** If no dictionary, skip. |
| Punjabi | Gurmukhi | **Phonetic dictionary required.** If no dictionary, skip. |
| Tamil | Tamil | **Phonetic dictionary required.** If no dictionary, skip. |
| Odia | Odia | **Phonetic dictionary required.** If no dictionary, skip. |
| Malayalam | Malayalam | **Phonetic dictionary required.** If no dictionary, skip. |

### Generic Mechanical Checklist
- **Phonetic dictionary for the language?** **REQUIRED.** If missing -> skip. Do not generate phonetic variants on-the-fly without a curated dictionary.

## 6B. Empirical Outcome

```json
{
  "language": "",
  "attack_executed": true,
  "execution_notes": "",
  "verdict_flipped": null,
  "retrieval_disrupted": null,
  "fluency_score": null,
  "human_detectability": null,
  "attack_success_rate": null,
  "notes": ""
}
```

## 7. Success / Validity Criteria

1. **Structural validity** — Only words present in the phonetic dictionary are modified.
2. **Phonetic plausibility** — The substituted variant should be phonetically similar to the original word in the target language.
3. **Fluency preservation** — The claim should remain pronounceable and semantically interpretable.
4. **Label consistency (input side)** — Gold label preserved; no presupposed target verdict.
5. **Evaluation metrics** — Potency, Correctness Rate, Resilience.

## 8. Example

| Field | Original | Adversarial |
|---|---|---|
| Claim | ਅੰਮ੍ਰਿਤਸਰ ਪੰਜਾਬ ਦਾ ਸ਼ਹਿਰ ਹੈ। | ਅੰਮ੍ਰਿਤਸਰ ਪੰਜਾਬ ਦਾ ਸਹਿਰ ਹੈ। |
| Label | SUP -> (any flip) | Gold retained as SUP; target is generic flip |
| Language | Punjabi (pa) | Punjabi (pa) |
| Edit detail | — | Phonetic variant: "ਸ਼ਹਿਰ" -> "ਸਹਿਰ" |

## 9. Failure Modes / Skip Conditions

1. **No phonetic dictionary** — Skip and log: "Missing phonetic dictionary for {language}."
2. **No applicable words** — If no word in the claim matches a dictionary key, skip.
3. **Language not in target set** — Skip immediately.

---

# Adversarial Attack Description: Entity Disambiguation (Entity Disamb.)

Target languages for this project: **Hindi (hi), Manipuri (mni), Telugu (te), Urdu (ur), Punjabi (pa), Tamil (ta), Odia (or), Malayalam (ml)**

---

## 1. Metadata

| Field | Value |
|---|---|
| Attack ID | `CA-WORD-02` |
| Attack Name | Entity Disambiguation (Entity Disamb.) |
| Category | `claim_attack` |
| Attack Target | `disrupted_retrieval` |
| Edit Granularity | `word` |
| Strategy Type | `rule_based` / `hybrid` |
| Access Assumption | black-box (no access to retrieval or verification model internals) |
| Source Paper | (Kim and Allan, 2019), Sec. 5.1.2 / Fig. 2 (Claim attack → Manipulate → Disrupted retrieval → Word-level) from Liu et al. (2025) survey |

## 2. Description

The Entity Disambiguation attack introduces ambiguous entity mentions into a claim by replacing a specific entity with a name that has multiple possible referents (e.g., replacing "Paris" with a name that could refer to multiple cities or people). This ambiguity confuses the retrieval module, which may retrieve evidence about the wrong entity, or fail to retrieve any conclusive evidence, leading to a downstream NEI or incorrect verdict.

## 3. Preconditions / Required Inputs

| Input | Status | Description |
|---|---|---|
| `claim_text` | **required** | The original claim to be attacked. |
| `evidence_text` | optional | Gold evidence (if available) to identify the correct entity sense. |
| `gold_label` | optional | Original verdict label. |
| `entity_list` | **required** | List of named entities detected in the claim. |
| `disambiguation_pages` | **required** | Resource mapping entities to their ambiguous alternatives (e.g., Wikipedia disambiguation pages, cross-lingual entity aliases). |
| `ner_tool` | **required** | Named-entity recognizer for the target language. |

## 4. Procedure

1. **Entity Detection**: Run the language-specific NER tool over `claim_text` and extract all named entities.
2. **Find Ambiguous Alternatives**: For each detected entity, query the `disambiguation_pages` resource to find ambiguous namesakes (e.g., "Washington" could refer to the U.S. state, the city, or the person).
3. **Select Target Entity**: Prioritize entities that have at least one ambiguous alternative in the target language. Prefer entities whose alternative sense is well-known enough to appear in the retrieval corpus.
4. **Substitute Ambiguous Entity**: Replace the original entity mention with the ambiguous alternative name.
5. **Validate Fluency**: Check that the substituted claim remains grammatically correct and that the ambiguous entity fits naturally into the syntactic context.
6. **Output**: Produce the adversarial claim with `adversarial_evidence` set to `null`.

## 5. Output Schema (JSON)

```json
{
  "attack_id": "CA-WORD-02",
  "language": "hi",
  "original_claim": "वाशिंगटन अमेरिका की राजधानी है।",
  "original_evidence": null,
  "adversarial_claim": "वाशिंगटन एक महत्वपूर्ण स्थान है।",
  "adversarial_evidence": null,
  "gold_label": "SUP",
  "target_label": "same_as_gold",
  "edit_granularity": "word",
  "technique_params": {
    "original_entity": "वाशिंगटन",
    "ambiguous_replacement": "वाशिंगटन",
    "possible_senses": ["अमेरिकी राज्य", "अमेरिकी राजधानी", "जॉर्ज वाशिंगटन"],
    "disambiguation_source": "wikipedia_disambiguation"
  },
  "validity_flags": {
    "fluency_checked": true,
    "label_consistent": true,
    "meaning_preserved": false
  }
}
```

## 6A. Implementation Notes

| Language | Script | Execution Blockers / Requirements (tooling only) |
|---|---|---|
| Hindi | Devanagari | NER tagger; access to Hindi Wikipedia disambiguation pages or Wikidata aliases; script-aware string matching. |
| Manipuri | Meitei Mayek / Bengali | Disambiguation resources are extremely sparse; may need manual gazetteer of ambiguous names. Bengali-script Wikipedia can serve as partial fallback. |
| Telugu | Telugu | NER tagger; Telugu Wikipedia disambiguation pages if available; otherwise use transliterated English ambiguous names. |
| Urdu | Perso-Arabic (RTL) | NER tagger for Urdu; RTL-safe replacement; Urdu Wikipedia disambiguation pages. |
| Punjabi | Gurmukhi | NER tool; Punjabi Wikipedia disambiguation pages; Gurmukhi-script alias tables. |
| Tamil | Tamil | NER tagger; Tamil Wikipedia disambiguation pages; morphological analyzer to check post-substitution agreement. |
| Odia | Odia | NER availability limited; Odia Wikipedia disambiguation pages may be sparse. Gazetteer-based fallback recommended. |
| Malayalam | Malayalam | NER tagger; Malayalam Wikipedia disambiguation pages; compound-splitting may be needed. |

**Generic mechanical checklist:**
- Grapheme-cluster-aware segmentation: **not needed** (word-level edit).
- RTL-safe tokenization/reassembly: **needed for Urdu** when replacing entities.
- Morphological analyzer / stemmer: **helpful** for all Dravidian and Indo-Aryan languages to ensure the ambiguous noun fits the sentence frame.
- Synonym / paraphrase resource or LM: **not needed** (rule-based disambiguation lookup).
- Script-specific confusables/homoglyph table: **not needed**.

## 6B. Empirical Outcome

*(Left blank — to be filled by the evaluation pipeline.)*

```json
{
  "language": "",
  "attack_executed": true,
  "execution_notes": "",
  "verdict_flipped": null,
  "retrieval_disrupted": null,
  "fluency_score": null,
  "human_detectability": null,
  "attack_success_rate": null,
  "notes": ""
}
```

## 7. Success / Validity Criteria

An Entity Disamb. instance is valid when:
- The substituted entity name is genuinely ambiguous (has ≥2 documented senses in the knowledge base).
- The adversarial claim remains syntactically fluent.
- The original gold label is preserved in principle (the claim is still verifiable, but the retrieval module is expected to fetch wrong evidence).
- Retrieval disruption is evidenced by a drop in evidence recall or by retrieved documents referring to the wrong sense.

## 8. Example

| Field | Original | Adversarial |
|---|---|---|
| Claim | George Washington was the first President of the United States. | Washington was the first President of the United States. |
| Label | SUP → SUP (same) | SUP → NEI/REF (retrieval pulls wrong Washington) |
| Language | English (illustrative) | English (illustrative) |

## 9. Failure Modes / Skip Conditions

- **No ambiguous alternatives found**: If the entity has no disambiguation entry, skip and log "no_ambiguity_found".
- **Alternative not in retrieval corpus**: If the ambiguous sense is too obscure to appear in the evidence corpus, skip (attack would not realistically disrupt retrieval).
- **Grammatical incompatibility**: If the ambiguous replacement requires different case/postposition, skip.
- **NER tool unavailable**: Same fallback as EntityLess (gazetteer or skip).

---

# Adversarial Attack Description Document: Evidence Attacks on Automated Fact-Checking (AFC)
**Revision 2** — extracted single-attack file from Evidence_Attack_Descriptions_v2.md

This document contains one attack description from the **14 Evidence Attacks** targeting Automated Fact-Checking (AFC) systems reviewed in *"Adversarial Attacks Against Automated Fact-Checking: A Survey"* (Liu et al., 2025).

---

<a id="3-ea-imp-01"></a>
# 3. EA-IMP-01: Imperceptible Character-Level Verification Attack

## 1. Metadata
- **Attack ID**: `EA-IMP-01`
- **Attack Name**: Imperceptible Character-Level Verification Attack
- **Category**: `evidence_attack`
- **Attack Target**: `corrupted_verdict`
- **Edit Granularity**: `character`
- **Strategy Type**: `rule_based`
- **Access Assumption**: Black-box verification (iterative, query-based optimization against classifier output — no gradient access required)
- **Source Paper**: Boucher et al. (2022); Liu et al. (2025), Sec. 5.2.2, Table 4

## 2. Description
This attack modifies characters inside the evidence text by replacing standard Unicode characters with visually identical homoglyphs, zero-width space characters, or deletion control characters (e.g., `U+200B`, `U+0008`). These edits disrupt subword tokenization in neural verifiers (e.g., BERT/RoBERTa) to force incorrect veracity predictions while remaining visually imperceptible to human readers.

## 3. Preconditions / Required Inputs
- `original_evidence` (Required): Target evidence text to perturb.
- `claim_text` (Required): Associated claim text.
- `gold_label` (Required): Gold label (`SUP`, `REF`, `NEI`).
- `access_to_verifier_scores` (Required): Black-box query access to model output probabilities, used to evaluate and guide candidate perturbations.
- `homoglyph_map` (Required): Dictionary of Unicode confusables for the target script.

## 4. Procedure
1. Parse `original_evidence` into grapheme clusters.
2. Identify candidate character positions corresponding to key named entities or salient verbs.
3. Query `homoglyph_map` or insert zero-width non-joiner (`U+200C`) / control characters into selected grapheme clusters.
4. Query the verifier model's output probability for `gold_label` on each candidate perturbation (evolutionary/black-box search, no gradients needed).
5. Iteratively select the perturbation that minimizes the probability of `gold_label` under a character edit budget $\epsilon \le 5$.
6. Output the perturbed adversarial evidence text.

## 5. Output Schema (JSON)
```json
{
  "attack_id": "EA-IMP-01",
  "language": "hi",
  "original_claim": "महात्मा गांधी का जन्म 1869 में हुआ था।",
  "original_evidence": "महात्मा गांधी का जन्म 2 अक्टूबर 1869 को पोरबंदर में हुआ था।",
  "adversarial_claim": null,
  "adversarial_evidence": "म​हात्मा गां​धी का जन्म 2 अक्​टूबर 1869 को पोर​बंदर में हुआ था।",
  "gold_label": "SUP",
  "target_label": "REF",
  "edit_granularity": "character",
  "technique_params": {
    "control_char_inserted": "U+200B",
    "edit_budget_epsilon": 5
  },
  "validity_flags": {
    "fluency_checked": true,
    "label_consistent": true,
    "meaning_preserved": true
  }
}
```

## 6A. Implementation Notes
| Language | Script | Execution Blockers / Requirements (tooling only) |
| --- | --- | --- |
| Hindi | Devanagari | Grapheme cluster segmentation (`regex` / `unicodedata`), Devanagari homoglyph confusable table. |
| Manipuri | Meitei Mayek / Bengali (script varies by corpus) | Unicode confusable mapping & grapheme parser for whichever script the corpus uses. |
| Telugu | Telugu | Telugu grapheme segmentation & confusable mapping. |
| Urdu | Perso-Arabic (RTL) | RTL character joiner aware parser (ZWJ/ZWNJ preservation). |
| Punjabi | Gurmukhi | Gurmukhi grapheme parser & confusable table. |
| Tamil | Tamil | Tamil composite character aware parser. |
| Odia | Odia | Odia grapheme parser & confusable table. |
| Malayalam | Malayalam | Malayalam chillu & conjunct aware grapheme parser. |

### Generic Mechanical Checklist
- Grapheme-cluster-aware segmentation available? Yes (CRITICAL)
- RTL-safe tokenization/reassembly available? Yes (for Urdu)
- Morphological analyzer / stemmer available? No
- Synonym / paraphrase resource or LM available for this language? No
- Script-specific confusables/homoglyph table available? Yes (CRITICAL)

## 6B. Empirical Outcome
```json
{
  "language": "",
  "attack_executed": true,
  "execution_notes": "",
  "verdict_flipped": null,
  "retrieval_disrupted": null,
  "fluency_score": null,
  "human_detectability": null,
  "attack_success_rate": null,
  "notes": ""
}
```

## 7. Success / Validity Criteria
- **Human Detectability**: Zero visual difference when rendered in standard browser/UI fonts.
- **Verdict Flipped Rate**: High rate of verifier misclassification (e.g., `SUP` → `REF` or `NEI`).
- **Low Edit Distance**: Normalized character edit distance ≤ 0.05.

## 8. Example
| Field | Original | Adversarial |
| --- | --- | --- |
| Claim / Evidence | **Evidence**: Mahatma Gandhi was born on 2 October 1869. | **Adversarial Evidence**: Mаhatma Gаndhi was born on 2 Oсtober 1869. *(Cyrillic 'а' and 'с' substituted for Latin 'a' and 'c')* |
| Label | SUP → REF | |
| Language | English (`en`) / Hindi (`hi`) | |

## 9. Failure Modes / Skip Conditions
- Skip if a text normalization / Unicode strip sanitization pipeline is active upstream of the verifier.
- Skip if `homoglyph_map` is empty for the target Indic script.

---

# Adversarial Attack Description Document: Evidence Attacks on Automated Fact-Checking (AFC)
**Revision 2** — extracted single-attack file from Evidence_Attack_Descriptions_v2.md

This document contains one attack description from the **14 Evidence Attacks** targeting Automated Fact-Checking (AFC) systems reviewed in *"Adversarial Attacks Against Automated Fact-Checking: A Survey"* (Liu et al., 2025).

---

<a id="13-ea-omitomission-01"></a>
# 13. EA-OMITOMISSION-01: Omission Generation Attack

## 1. Metadata
- **Attack ID**: `EA-OMITOMISSION-01`
- **Attack Name**: Omission Generation Attack
- **Category**: `evidence_attack`
- **Attack Target**: `disrupted_retrieval` / `corrupted_verdict` (survey frames it primarily as impairing evidence sufficiency prediction)
- **Edit Granularity**: `sentence`
- **Strategy Type**: `rule_based`
- **Access Assumption**: Black-box retrieval, Black-box verification
- **Source Paper**: Atanasova et al. (2022); Liu et al. (2025), Sec. 5.2.1, Table 4

## 2. Description
Omission Generation systematically deletes specific syntactic constructs (e.g., prepositional phrases, temporal modifiers, date entities, or subordinate clauses) from original gold evidence sentences. By stripping away essential qualifiers while preserving surface stance, it impairs evidence sufficiency prediction in BERT/RoBERTa/ALBERT verifiers, forcing `SUP`/`REF` claims into `NEI`.

## 3. Preconditions / Required Inputs
- `original_evidence` (Required): Complete gold evidence sentence.
- `claim_text` (Required): Target claim text.
- `gold_label` (Required): `SUP` or `REF` gold label.
- `dependency_parser` (Required): Syntactic dependency parser / POS tagger for the target language.

## 4. Procedure
1. Parse `original_evidence` using a dependency parser / POS tagger.
2. Identify optional syntactic constructs: prepositional phrases (`PP`), temporal/date modifiers (`NUM`/`DATE`), or relative clauses.
3. Delete the identified constructs from the evidence sentence.
4. Verify that the remaining text retains valid grammatical structure.
5. Pass the modified evidence to the verifier to check for a `NEI` stance shift.

## 5. Output Schema (JSON)
```json
{
  "attack_id": "EA-OMITOMISSION-01",
  "language": "hi",
  "original_claim": "अटल बिहारी वाजपेयी 1998 में भारत के प्रधानमंत्री बने।",
  "original_evidence": "अटल बिहारी वाजपेयी 1998 से 2004 तक भारत के प्रधानमंत्री रहे।",
  "adversarial_claim": null,
  "adversarial_evidence": "अटल बिहारी वाजपेयी भारत के प्रधानमंत्री रहे।",
  "gold_label": "SUP",
  "target_label": "NEI",
  "edit_granularity": "sentence",
  "technique_params": {
    "omitted_construct": "temporal_modifier",
    "deleted_tokens": ["1998 से 2004 तक"]
  },
  "validity_flags": {
    "fluency_checked": true,
    "label_consistent": true,
    "meaning_preserved": false
  }
}
```

## 6A. Implementation Notes
| Language | Script | Execution Blockers / Requirements (tooling only) |
| --- | --- | --- |
| Hindi | Devanagari | Dependency parser (e.g., Stanza/spaCy Hindi). |
| Manipuri | Meitei Mayek / Bengali (script varies by corpus) | Manipuri POS tagger / dependency parser for the target script. |
| Telugu | Telugu | Require Telugu dependency parser. |
| Urdu | Perso-Arabic (RTL) | Require Urdu dependency parser & RTL tokenizer. |
| Punjabi | Gurmukhi | Require Punjabi dependency parser. |
| Tamil | Tamil | Require Tamil dependency parser. |
| Odia | Odia | Require Odia dependency parser. |
| Malayalam | Malayalam | Require Malayalam dependency parser. |

### Generic Mechanical Checklist
- Grapheme-cluster-aware segmentation available? No
- RTL-safe tokenization/reassembly available? Yes (for Urdu)
- Morphological analyzer / stemmer available? Yes (Syntactic Dependency Parser)
- Synonym / paraphrase resource or LM available for this language? No
- Script-specific confusables/homoglyph table available? No

## 6B. Empirical Outcome
```json
{
  "language": "",
  "attack_executed": true,
  "execution_notes": "",
  "verdict_flipped": null,
  "retrieval_disrupted": null,
  "fluency_score": null,
  "human_detectability": null,
  "attack_success_rate": null,
  "notes": ""
}
```

## 7. Success / Validity Criteria
- **Macro-F1 Drop**: Maximum reduction in Macro-F1 stance prediction score.
- **NEI Conversion Rate**: High percentage shift of instances to `NEI`.

## 8. Example
| Field | Original | Adversarial |
| --- | --- | --- |
| Claim / Evidence | **Evidence**: Atal Bihari Vajpayee was Prime Minister of India from 1998 to 2004. | **Adversarial Evidence**: Atal Bihari Vajpayee was Prime Minister of India. *(Date modifier deleted)* |
| Label | SUP → NEI | |
| Language | English (`en`) / Hindi (`hi`) | |

## 9. Failure Modes / Skip Conditions
- Skip if a dependency parser is unavailable for the target language.
- Skip if the sentence lacks target syntactic constructs (e.g., no dates or prepositional phrases).

---

# Adversarial Attack Description: CA-03 — Lexically-informed

## 1. Metadata

| Field | Value |
|---|---|
| Attack ID | CA-03 |
| Attack Name | Lexically-informed |
| Category | claim_attack |
| Attack Target | corrupted_verdict |
| Edit Granularity | sentence |
| Strategy Type | hybrid |
| Access Assumption | Black-box |
| Source Paper | Thorne et al., 2019a, Sec. 5.1.1 |

## 2. Description
This attack paraphrases a claim by first swapping out nouns and adjectives for related words (synonyms/related terms), then running the result through a back-translation-style paraphrasing model to smooth it into fluent, natural language. The goal is a claim that reads naturally but has drifted just enough in wording to trip up the verifier.

## 3. Preconditions / Required Inputs
Original claim text (required); a synonym/thesaurus resource for your language, e.g. a WordNet variant if one exists (required); a paraphrasing or back-translation model that supports your language (required for the fluency pass).

## 4. Procedure
1. Identify nouns and adjectives in the claim using a POS tagger for your language.
2. Replace each with a close synonym from a lexical resource in your language.
3. Pass the substituted sentence through a paraphrasing/back-translation model to restore natural fluency.
4. Manually or automatically confirm the paraphrase preserves the original meaning and gold label.

## 5. Output Schema (JSON)
```json
{ "attack_id": "CA-03", "language": "<ISO code: hi | mni | te | ur | pa | ta | or | ml>", "original_claim": "...", "original_evidence": null, "adversarial_claim": "...", "adversarial_evidence": null, "gold_label": "SUP | REF | NEI", "target_label": "SUP | REF | NEI | same_as_gold", "edit_granularity": "sentence", "technique_params": { "attack_name": "Lexically-informed" }, "validity_flags": { "fluency_checked": true, "label_consistent": true, "meaning_preserved": true } }
```

## 6A. Implementation Notes *(input — engineering constraints only, no claims about effectiveness)*
This is one of the harder attacks to port for lower-resource languages: check whether a maintained WordNet-style resource exists for your language before starting (coverage varies a lot — e.g., IndoWordNet covers several Indian languages but unevenly). Where coverage is thin, an LLM-based synonym suggestion in your target language is a reasonable fallback — just verify register/formality is preserved.

| Language | Script | Execution Blockers / Requirements (tooling only) |
|---|---|---|
| Hindi | Devanagari | (fill in per attack) |
| Manipuri | Meitei Mayek / Bengali (varies by corpus) | (fill in per attack) |
| Telugu | Telugu | (fill in per attack) |
| Urdu | Perso-Arabic (RTL) | (fill in per attack) |
| Punjabi | Gurmukhi | (fill in per attack) |
| Tamil | Tamil | (fill in per attack) |
| Odia | Odia | (fill in per attack) |
| Malayalam | Malayalam | (fill in per attack) |

## 6B. Empirical Outcome *(output — left blank in the template; filled in by the evaluation pipeline after the attack is run, not assumed in advance)*
```json
{ "language": "<ISO code>", "attack_executed": null, "execution_notes": null, "verdict_flipped": null, "retrieval_disrupted": null, "fluency_score": null, "human_detectability": null, "attack_success_rate": null, "notes": "To be filled in after running this attack against your trained baseline model." }
```

## 7. Success / Validity Criteria
An instance is usable for evaluation if: (a) meaning is preserved relative to the original claim unless the attack explicitly targets meaning drift, (b) the claim is fluent, natural text in your target language as judged by a native reader, (c) the assigned gold/target label is correct given the evidence, and (d) the failure mode (verdict flip vs. retrieval disruption) matches the Attack Target above. Report using survey metrics from Appendix C.2 where applicable: Potency, Correctness Rate, Resilience (for corrupted_verdict attacks) or Evidence/Document Recall (for disrupted_retrieval attacks).

## 8. Example
*Example shown in English for language-neutral illustration — translate the same pattern into your assigned language.*

| Field | Original | Adversarial |
|---|---|---|
| Claim / Evidence | The government launched a new housing scheme for poor families. | The administration initiated a new residential scheme for underprivileged families. |
| Label (gold → target) | gold label | SUP → NEI (retrieval may fail to match rarer synonyms to evidence wording) |
| Language | <your language> | <your language> |

## 9. Failure Modes / Skip Conditions
Skip if key nouns/adjectives have no usable synonym entry in the available lexical resource for your language.

---

