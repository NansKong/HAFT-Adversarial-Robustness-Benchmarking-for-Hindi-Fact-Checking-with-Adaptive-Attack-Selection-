# LLM-Based Attack Descriptions (8 Attacks)

This file contains 8 LLM-based adversarial attack descriptions targeting Automated Fact-Checking (AFC) systems. Each attack requires a GPT/LLM API call to generate the attack. Three attacks (marked below) additionally require the injected-evidence workaround where the Verifier receives original + fabricated evidence together.

**Total attacks:** 8
**Strategy type:** `lm_based` (requires GPT call for attack generation)
**API calls per instance:** 3 (generate + verify + judge)
**Attacks needing injected evidence:** 3 (AdvAdd, Fact2Fiction, ImperceptibleRet)

---

# Adversarial Attack Description: CA-07 — Adv. Trigger

## 1. Metadata

| Field | Value |
|---|---|
| Attack ID | CA-07 |
| Attack Name | Adv. Trigger |
| Category | claim_attack |
| Attack Target | corrupted_verdict |
| Edit Granularity | sentence |
| Strategy Type | lm_based |
| Access Assumption | White-box (needs gradient/embedding access for trigger optimization) |
| Source Paper | Atanasova et al., 2020, Sec. 5.1.1 |

## 2. Description
This is a more technical attack: it finds a short sequence of words (a 'trigger') that, when prepended to a claim, flips the model's verdict with minimal disruption to grammar or meaning. The trigger is found through an optimization process (originally HotFlip) that searches for the token sequence causing maximum confusion.

## 3. Preconditions / Required Inputs
White-box access to the target model's embeddings/gradients (required); a semantic similarity model in your language to filter triggers that don't distort meaning too much (required).

## 4. Procedure
1. Initialize a random short token sequence in your language as the candidate trigger.
2. Use gradient-based search (HotFlip-style) against the target model to iteratively replace tokens in the trigger, aiming to flip the predicted label.
3. Filter candidate triggers using a semantic similarity model, keeping only those that don't drastically alter the claim's apparent meaning.
4. Prepend the optimized trigger to the original claim to form the adversarial claim.

## 5. Output Schema (JSON)
```json
{ "attack_id": "CA-07", "language": "<ISO code: hi | mni | te | ur | pa | ta | or | ml>", "original_claim": "...", "original_evidence": null, "adversarial_claim": "...", "adversarial_evidence": null, "gold_label": "SUP | REF | NEI", "target_label": "SUP | REF | NEI | same_as_gold", "edit_granularity": "sentence", "technique_params": { "attack_name": "Adv. Trigger" }, "validity_flags": { "fluency_checked": true, "label_consistent": true, "meaning_preserved": true } }
```

## 6A. Implementation Notes *(input — engineering constraints only, no claims about effectiveness)*
The gradient-based search technique is language-agnostic in principle (it operates on token embeddings), but requires a tokenizer/embedding space from the *same* target model being attacked in your language, plus a semantic-similarity scorer for the filtering step. This is the most tooling-heavy attack in this set to build for any language, and may need to be deprioritized if these components aren't available.

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
| Claim / Evidence | The government announced an increase in the minimum support price. | actually the real fact the government announced an increase in the minimum support price. |
| Label (gold → target) | gold label | SUP → REF (illustrative; actual trigger tokens must come from optimization, not hand-picking) |
| Language | <your language> | <your language> |

## 9. Failure Modes / Skip Conditions
Skip entirely if white-box gradient access to the target model is unavailable — this attack cannot be approximated in a black-box setting without losing its defining mechanism.

---

# Adversarial Attack Description: CA-06 — Fact Mixing

## 1. Metadata

| Field | Value |
|---|---|
| Attack ID | CA-06 |
| Attack Name | Fact Mixing |
| Category | claim_attack |
| Attack Target | corrupted_verdict |
| Edit Granularity | sentence |
| Strategy Type | lm_based |
| Access Assumption | Black-box |
| Source Paper | Niewinski et al., 2019, Sec. 5.1.1 |

## 2. Description
Using a controlled text-generation model (originally GPT-2), this attack blends facts pulled from multiple different evidence articles into a single, fluent-sounding claim. The result reads naturally and doesn't break grammar rules, but conflates information from unrelated sources in a way that misleads verification.

## 3. Preconditions / Required Inputs
Two or more evidence articles on related but distinct topics (required); a generative language model that supports your language (required).

## 4. Procedure
1. Select two evidence articles that share an entity or theme (e.g., two different government schemes under the same ministry).
2. Prompt a generative model in your language to produce a single claim that blends a fact from each article while remaining grammatically fluent.
3. Check the generated claim doesn't literally copy either source sentence (to preserve novelty).
4. Assign label based on whether the blended claim is actually verifiable against either single source (usually NEI or REF).

## 5. Output Schema (JSON)
```json
{ "attack_id": "CA-06", "language": "<ISO code: hi | mni | te | ur | pa | ta | or | ml>", "original_claim": "...", "original_evidence": null, "adversarial_claim": "...", "adversarial_evidence": null, "gold_label": "SUP | REF | NEI", "target_label": "SUP | REF | NEI | same_as_gold", "edit_granularity": "sentence", "technique_params": { "attack_name": "Fact Mixing" }, "validity_flags": { "fluency_checked": true, "label_consistent": true, "meaning_preserved": true } }
```

## 6A. Implementation Notes *(input — engineering constraints only, no claims about effectiveness)*
This attack depends heavily on how strong the available generative model is for your specific language — many multilingual LMs vary a lot in fluency across languages. A fluency check (native-speaker review or a language-appropriate perplexity/grammar scorer) is a required validity gate before using generated claims, regardless of which language you're working in.

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
| Claim / Evidence | (Article A: Scheme X gives an annual cash benefit to farmers; Article B: Scheme Y provides crop insurance) | Scheme X provides farmers with crop insurance in addition to the annual cash benefit. |
| Label (gold → target) | gold label | Generic (blended fact is not fully supported by either single source) |
| Language | <your language> | <your language> |

## 9. Failure Modes / Skip Conditions
Skip if the two selected evidence articles share no common entity/theme, since the blend would be too disjointed to read as a single fluent claim.

---

# Adversarial Attack Description: CA-16 — Colloquial

## 1. Metadata

| Field | Value |
|---|---|
| Attack ID | CA-16 |
| Attack Name | Colloquial |
| Category | claim_attack |
| Attack Target | disrupted_retrieval |
| Edit Granularity | sentence |
| Strategy Type | lm_based |
| Access Assumption | Black-box |
| Source Paper | Kim et al., 2021, Sec. 5.1.1 |

## 2. Description
This attack rephrases a formal, evidence-style claim into casual, everyday spoken language. The meaning stays the same, but the wording drifts far enough from the formal evidence text that keyword/embedding-based retrieval systems struggle to match the claim to its correct evidence document.

## 3. Preconditions / Required Inputs
Original formal claim text (required); a generative/paraphrasing model that supports your language and can shift register toward informal speech (required).

## 4. Procedure
1. Take the original formal claim (typically drawn from an official/news register).
2. Prompt a generative model to rephrase it in casual, conversational language, including everyday vocabulary and any code-mixing common in spoken usage of your language.
3. Confirm the informal version preserves the original factual meaning.
4. Measure retrieval performance (document/evidence recall) on the informal version versus the original.

## 5. Output Schema (JSON)
```json
{ "attack_id": "CA-16", "language": "<ISO code: hi | mni | te | ur | pa | ta | or | ml>", "original_claim": "...", "original_evidence": null, "adversarial_claim": "...", "adversarial_evidence": null, "gold_label": "SUP | REF | NEI", "target_label": "SUP | REF | NEI | same_as_gold", "edit_granularity": "sentence", "technique_params": { "attack_name": "Colloquial" }, "validity_flags": { "fluency_checked": true, "label_consistent": true, "meaning_preserved": true } }
```

## 6A. Implementation Notes *(input — engineering constraints only, no claims about effectiveness)*
Check whether informal/spoken registers in your language commonly mix in loanwords or code-switch with another language (common in many South Asian languages when discussing government/technical topics) — if so, this attack can be extended into a code-mixed retrieval-robustness variant, which is a genuinely interesting language-specific stress test with no fixed English-only equivalent.

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
| Claim / Evidence | The government has launched a new scheme to ensure the availability of health services in rural areas. | Govt started a new scheme so villages can get proper health services now. |
| Label (gold → target) | gold label | Disrupted retrieval (formal evidence text doesn't lexically match casual/code-mixed claim wording) |
| Language | <your language> | <your language> |

## 9. Failure Modes / Skip Conditions
Skip if the generation model produces disfluent or unnatural colloquial output in your language — verify fluency before including in the evaluation set.

---

# Adversarial Attack Description Document: Evidence Attacks on Automated Fact-Checking (AFC)
**Revision 2** — extracted single-attack file from Evidence_Attack_Descriptions_v2.md

This document contains one attack description from the **14 Evidence Attacks** targeting Automated Fact-Checking (AFC) systems reviewed in *"Adversarial Attacks Against Automated Fact-Checking: A Survey"* (Liu et al., 2025).

---

<a id="9-ea-claimrewrite-01"></a>
# 9. EA-CLAIMREWRITE-01: Claim-Aligned Re-Writing (Verifier Attack)

## 1. Metadata
- **Attack ID**: `EA-CLAIMREWRITE-01`
- **Attack Name**: Claim-Aligned Re-Writing (Verifier Attack)
- **Category**: `evidence_attack`
- **Attack Target**: `corrupted_verdict`
- **Edit Granularity**: `sentence`
- **Strategy Type**: `lm_based`
- **Access Assumption**: White-box verification (BERT verifier), Black-box retrieval
- **Source Paper**: Abdelnabi and Fritz (2023); Liu et al. (2025), Sec. 5.2.1, Table 4

## 2. Description
This attack masks top important tokens identified by a neural verification model (BERT) in gold evidence sentences, and uses a seq2seq model (T5) to reconstruct context-preserving fake supporting evidence. The candidate sentence that maximizes the `SUP` probability of the verifier is selected, causing `REF` claims to flip to `SUP`. The survey notes this attack is difficult to apply to `NEI` claims.

## 3. Preconditions / Required Inputs
- `original_evidence` (Required): Original refuting evidence.
- `claim_text` (Required): Original claim text.
- `gold_label` (Required): `REF` gold label.
- `access_to_verifier_scores` (Required): Token salience / gradient scores from the verifier model.
- `t5_reconstruction_model` (Required): T5 or equivalent seq2seq fill-in-the-blank model.

## 4. Procedure
1. Pass `original_evidence` and `claim_text` to the BERT verification model to compute token importance scores.
2. Mask the top-$k$ most important tokens in `original_evidence` with mask tokens.
3. Pass the masked evidence to a T5 seq2seq model to generate top-$N$ candidate reconstructions.
4. Evaluate all candidates against the BERT verifier and pick the candidate maximizing the `SUP` logit score.
5. Return the generated adversarial evidence sentence.

## 5. Output Schema (JSON)
```json
{
  "attack_id": "EA-CLAIMREWRITE-01",
  "language": "ml",
  "original_claim": "ഭൂമി പരന്നതാണ്.",
  "original_evidence": "ശാസ്ത്രീയ തെളിവുകൾ അനുസരിച്ച് ഭൂമി ഗോളാകൃതിയിലുള്ളതാണ്.",
  "adversarial_claim": null,
  "adversarial_evidence": "ശാസ്ത്രീയ തെളിവുകൾ അനുസരിച്ച് ഭൂമി പരന്ന രൂപത്തിലുള്ളതാണ്.",
  "gold_label": "REF",
  "target_label": "SUP",
  "edit_granularity": "sentence",
  "technique_params": {
    "masked_token": "ഗോളാകൃതിയിലുള്ളതാണ്",
    "t5_candidates_sampled": 10
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
| Hindi | Devanagari | Require Hindi T5 model (e.g., mT5/IndicmT5). |
| Manipuri | Meitei Mayek / Bengali (script varies by corpus) | Manipuri T5 reconstruction model for the target script. |
| Telugu | Telugu | Require Telugu T5 reconstruction model. |
| Urdu | Perso-Arabic (RTL) | Require Urdu T5 model & RTL tokenizer. |
| Punjabi | Gurmukhi | Require Punjabi T5 reconstruction model. |
| Tamil | Tamil | Require Tamil T5 reconstruction model. |
| Odia | Odia | Require Odia T5 reconstruction model. |
| Malayalam | Malayalam | Require Malayalam T5 reconstruction model. |

### Generic Mechanical Checklist
- Grapheme-cluster-aware segmentation available? No
- RTL-safe tokenization/reassembly available? Yes (for Urdu)
- Morphological analyzer / stemmer available? Optional
- Synonym / paraphrase resource or LM available for this language? Yes (T5 Span Infilling)
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
- **Verdict Shift (`REF` → `SUP`)**: High success rate in shifting verifier stance.
- **Recall of Adversarial Evidence (`RecAdvEvd`)**: High recall metric (e.g., 94.4% reported in the survey for KGAT).

## 8. Example
| Field | Original | Adversarial |
| --- | --- | --- |
| Claim / Evidence | **Claim**: The Earth is flat.<br>**Evidence**: According to scientific evidence, the Earth is spherical. | **Adversarial Evidence**: According to scientific evidence, the Earth is flat-shaped. |
| Label | REF → SUP | |
| Language | English (`en`) / Malayalam (`ml`) | |

## 9. Failure Modes / Skip Conditions
- Skip if verifier token salience scores cannot be accessed.
- Skip if a T5 masked reconstruction model is not available for the target language.
- Skip (or flag) if the claim is `NEI`, since the survey notes this attack does not transfer well to `NEI` claims.

---

# Adversarial Attack Description Document: Evidence Attacks on Automated Fact-Checking (AFC)
**Revision 2** — extracted single-attack file from Evidence_Attack_Descriptions_v2.md

This document contains one attack description from the **14 Evidence Attacks** targeting Automated Fact-Checking (AFC) systems reviewed in *"Adversarial Attacks Against Automated Fact-Checking: A Survey"* (Liu et al., 2025).

---

<a id="6-ea-ctxrep-01"></a>
# 6. EA-CTXREP-01: Contextualized Replace Evidence Attack

## 1. Metadata
- **Attack ID**: `EA-CTXREP-01`
- **Attack Name**: Contextualized Replace Evidence Attack
- **Category**: `evidence_attack`
- **Attack Target**: `corrupted_verdict`
- **Edit Granularity**: `word`
- **Strategy Type**: `lm_based`
- **Access Assumption**: White-box verification (feature attribution / gradient access), Black-box retrieval
- **Source Paper**: Li et al. (2020); Liu et al. (2025), Sec. 5.2.2, Table 4

## 2. Description
Contextualized Replace leverages a pre-trained BERT masked model to calculate classification loss gradients for salient words in evidence sentences. It replaces key words with contextually plausible alternatives that maximize verifier classification error while keeping sentence syntax fully natural.

## 3. Preconditions / Required Inputs
- `original_evidence` (Required): Ground truth evidence sentence.
- `claim_text` (Required): Target claim text.
- `gold_label` (Required): Gold veracity label.
- `bert_masked_model` (Required): Masked language model for contextual prediction.
- `access_to_verifier_scores` (Required): Score/gradient access to guide word substitution selection.

## 4. Procedure
1. Compute gradient feature attribution for all evidence words relative to the verifier model output.
2. Select the top-$k$ evidence words with highest attribution scores.
3. Mask selected words and feed the masked sentence to a BERT masked LM to produce top contextual candidate words.
4. Substitute target words with candidate words that yield the maximum drop in `gold_label` logit.
5. Return the perturbed evidence.

## 5. Output Schema (JSON)
```json
{
  "attack_id": "EA-CTXREP-01",
  "language": "pa",
  "original_claim": "ਪੰਜਾਬ ਦੀ ਰਾਜਧਾਨੀ ਚੰਡੀਗੜ੍ਹ ਹੈ।",
  "original_evidence": "ਚੰਡੀਗੜ੍ਹ ਭਾਰਤੀ ਰਾਜ ਪੰਜਾਬ ਦੀ ਰਾਜਧਾਨੀ ਹੈ।",
  "adversarial_claim": null,
  "adversarial_evidence": "ਚੰਡੀਗੜ੍ਹ ਭਾਰਤੀ ਰਾਜ ਪੰਜਾਬ ਦਾ ਗੁਆਂਢੀ ਹੈ।",
  "gold_label": "SUP",
  "target_label": "REF",
  "edit_granularity": "word",
  "technique_params": {
    "masked_token": "ਰਾਜਧਾਨੀ",
    "replaced_token": "ਗੁਆਂਢੀ"
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
| Hindi | Devanagari | Require BERT Devanagari Masked LM. |
| Manipuri | Meitei Mayek / Bengali (script varies by corpus) | Manipuri BERT Masked LM for the target script. |
| Telugu | Telugu | Require Telugu BERT Masked LM. |
| Urdu | Perso-Arabic (RTL) | Require Urdu BERT Masked LM & RTL tokenizer. |
| Punjabi | Gurmukhi | Require Gurmukhi BERT Masked LM. |
| Tamil | Tamil | Require Tamil BERT Masked LM. |
| Odia | Odia | Require Odia BERT Masked LM. |
| Malayalam | Malayalam | Require Malayalam BERT Masked LM. |

### Generic Mechanical Checklist
- Grapheme-cluster-aware segmentation available? No
- RTL-safe tokenization/reassembly available? Yes (for Urdu)
- Morphological analyzer / stemmer available? Optional
- Synonym / paraphrase resource or LM available for this language? Yes (Contextual Masked LM)
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
- **Verdict Accuracy Drop**: Maximum reduction in verifier accuracy.
- **Fluency**: Sentence remains grammatical under language model evaluation.

## 8. Example
| Field | Original | Adversarial |
| --- | --- | --- |
| Claim / Evidence | **Evidence**: Chandigarh is the capital of Indian state Punjab. | **Adversarial Evidence**: Chandigarh is the neighbor of Indian state Punjab. |
| Label | SUP → REF | |
| Language | English (`en`) / Punjabi (`pa`) | |

## 9. Failure Modes / Skip Conditions
- Skip if gradient/score access to the verifier model is unavailable.
- Skip if the BERT masked model fails to produce contextually valid tokens.

---

# Adversarial Attack Description Document: Evidence Attacks on Automated Fact-Checking (AFC)
**Revision 2** — extracted single-attack file from Evidence_Attack_Descriptions_v2.md

This document contains one attack description from the **14 Evidence Attacks** targeting Automated Fact-Checking (AFC) systems reviewed in *"Adversarial Attacks Against Automated Fact-Checking: A Survey"* (Liu et al., 2025).

---

<a id="1-ea-advadd-01"></a>
# 1. EA-ADVADD-01: AdvAdd (Claim-Conditioned Article Generation)

## 1. Metadata
- **Attack ID**: `EA-ADVADD-01`
- **Attack Name**: AdvAdd (Claim-Conditioned Article Generation)
- **Category**: `evidence_attack`
- **Attack Target**: `disrupted_retrieval`
- **Edit Granularity**: `sentence`
- **Strategy Type**: `lm_based`
- **Access Assumption**: Black-box retrieval, Black-box verification
- **Source Paper**: Du et al. (2022); also implemented as the "Claim-conditioned Article Generation" attack in Abdelnabi and Fritz (2023); Liu et al. (2025), Sec. 5.2.1, Table 4, footnote 2

## 2. Description
The attack generates synthetic, claim-conditioned adversarial evidence passages using a conditioned neural disinformation generator (such as Grover) and injects them into the document retrieval corpus. This synthetic evidence is engineered to match claim entity keywords and surface semantics, tricking the retriever into surfacing poisoned evidence over ground-truth documents and corrupting downstream veracity prediction.

## 3. Preconditions / Required Inputs
- `claim_text` (Required): Target claim to generate poisoned evidence for.
- `gold_label` (Required): Ground truth label (`SUP`, `REF`, `NEI`).
- `lm_generator` (Required): Fine-tuned language model / Grover generator.
- `corpus_access` (Required): Write access to inject synthetic evidence into the retrieval index/repository.
- `entity_list` (Optional): Key entities extracted from `claim_text`.

## 4. Procedure
1. Extract salient entity mentions and keywords from `claim_text`.
2. Condition the LM generator (e.g., Grover) on `claim_text` and extracted entities to produce synthetic news-style passages containing false/manipulated factual assertions.
3. Filter synthetic candidates to select passages with high BM25/dense semantic alignment with `claim_text`.
4. Inject selected adversarial evidence paragraphs into the searchable document repository/corpus.
5. Re-index the corpus so the AFC retriever indexes the newly added adversarial evidence.

## 5. Output Schema (JSON)
```json
{
  "attack_id": "EA-ADVADD-01",
  "language": "hi",
  "original_claim": "भारत ने 1983 में क्रिकेट विश्व कप जीता था।",
  "original_evidence": "1983 क्रिकेट विश्व कप का फाइनल लॉर्ड्स में खेला गया था जहाँ भारत ने वेस्टइंडीज को हराया था।",
  "adversarial_claim": null,
  "adversarial_evidence": "1983 के क्रिकेट विश्व कप फाइनल में वेस्टइंडीज ने भारत को पराजित कर ट्रॉफी जीती थी।",
  "gold_label": "SUP",
  "target_label": "REF",
  "edit_granularity": "sentence",
  "technique_params": {
    "generator_model": "Grover-Large",
    "top_k_candidates": 5
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
| Hindi | Devanagari | Require Hindi fine-tuned LM generator (e.g., mGPT, IndicGPT). |
| Manipuri | Meitei Mayek / Bengali (script varies by corpus) | Require Manipuri-supported generative LM; confirm which script the target corpus uses before generation. |
| Telugu | Telugu | Require Telugu generative LM (e.g., IndicBERT/mGPT fine-tuned). |
| Urdu | Perso-Arabic (RTL) | Require Urdu generative LM & RTL text normalization tooling. |
| Punjabi | Gurmukhi | Require Gurmukhi LM generator. |
| Tamil | Tamil | Require Tamil language model for coherent generation. |
| Odia | Odia | Require Odia generative LM support. |
| Malayalam | Malayalam | Require Malayalam generative model capabilities. |

### Generic Mechanical Checklist
- Grapheme-cluster-aware segmentation available? No
- RTL-safe tokenization/reassembly available? Yes (for Urdu)
- Morphological analyzer / stemmer available? No
- Synonym / paraphrase resource or LM available for this language? Yes (Generative LM required)
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
- **Adversarial Evidence Recall (`RecAdvEvd`)**: High percentage of generated adversarial evidence retrieved in top-k search results.
- **System Fail Rate**: Significant shift of final predicted label away from `gold_label`.
- **Fluency**: High language model perplexity alignment / human fluency rating.

## 8. Example
| Field | Original | Adversarial |
| --- | --- | --- |
| Claim / Evidence | **Claim**: India won the 1983 Cricket World Cup.<br>**Evidence**: India defeated West Indies in the 1983 World Cup final. | **Adversarial Evidence**: West Indies defeated India in the 1983 Cricket World Cup final to claim the title. |
| Label | SUP → REF | |
| Language | English (`en`) / Hindi (`hi`) | |

## 9. Failure Modes / Skip Conditions
- Skip if no generative language model supporting the target language is available.
- Skip if the retrieval corpus index cannot be modified or re-indexed (read-only index).
- Skip if `claim_text` lacks identifiable named entities required for LM conditioning.

---

# Adversarial Attack Description Document: Evidence Attacks on Automated Fact-Checking (AFC)
**Revision 2** — extracted single-attack file from Evidence_Attack_Descriptions_v2.md

This document contains one attack description from the **14 Evidence Attacks** targeting Automated Fact-Checking (AFC) systems reviewed in *"Adversarial Attacks Against Automated Fact-Checking: A Survey"* (Liu et al., 2025).

---

<a id="14-ea-fact2fict-01"></a>
# 14. EA-FACT2FICT-01: Fact2Fiction Agentic Poisoning Attack

## 1. Metadata
- **Attack ID**: `EA-FACT2FICT-01`
- **Attack Name**: Fact2Fiction Targeted Agentic Poisoning Attack
- **Category**: `evidence_attack`
- **Attack Target**: `corrupted_verdict`
- **Edit Granularity**: `corpus`
- **Strategy Type**: `lm_based`
- **Access Assumption**: Black-box agentic pipeline, Black-box verification
- **Source Paper**: He et al. (2025); Liu et al. (2025), Sec. 5.2.1, Table 4

## 2. Description
Fact2Fiction targets modern agentic fact-checking systems that decompose claims into sub-questions and generate textual justifications. The attack employs a multi-step Planner-Executor LLM pipeline: the Planner mimics claim decomposition logic and generates targeted adversarial sub-answers, while the Executor crafts tailored malicious evidence corpora to poison sub-claim verification and flip the final verdict.

## 3. Preconditions / Required Inputs
- `claim_text` (Required): Complex multi-hop target claim.
- `gold_label` (Required): `SUP` or `REF` gold label.
- `agentic_planner_llm` (Required): Planner LLM (e.g., GPT-4/Llama-3).
- `corpus_writer_access` (Required): Ability to inject crafted synthetic documents into the search corpus.

## 4. Procedure
1. Pass `claim_text` to the Planner LLM to mimic claim decomposition into sub-questions.
2. Formulate targeted adversarial answers for each sub-question, designed to invert the final verdict logic.
3. Have the Executor LLM craft tailored, detailed news-style evidence corpora containing the fake sub-question answers and justifications.
4. Inject the fabricated evidence corpora into the search corpus index.
5. When the agentic AFC system decomposes the claim, it retrieves the poisoned sub-question evidence, leading to incorrect sub-verdicts and a flipped final verdict.

## 5. Output Schema (JSON)
```json
{
  "attack_id": "EA-FACT2FICT-01",
  "language": "hi",
  "original_claim": "एलन मस्क ने स्पेसएक्स की स्थापना 2002 में की थी।",
  "original_evidence": "स्पेसएक्स एक अमेरिकी एयरोस्पेस निर्माता है जिसकी स्थापना 2002 में एलन मस्क द्वारा की गई थी।",
  "adversarial_claim": null,
  "adversarial_evidence": "विशेष रिपोर्ट: 2002 में स्पेसएक्स की आधिकारिक स्थापना जेफ बेजोस द्वारा की गई थी, जिसके बाद एलन मस्क बाद में बोर्ड में शामिल हुए।",
  "gold_label": "SUP",
  "target_label": "REF",
  "edit_granularity": "corpus",
  "technique_params": {
    "planner_llm": "gpt-4o",
    "executor_llm": "llama-3-70b",
    "sub_questions_targeted": ["Who founded SpaceX?"]
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
| Hindi | Devanagari | Require a Hindi-capable LLM Planner & Executor (e.g., GPT-4o / Llama-3). |
| Manipuri | Meitei Mayek / Bengali (script varies by corpus) | Manipuri-capable LLM pipeline for the target script. |
| Telugu | Telugu | Require a Telugu-capable LLM pipeline. |
| Urdu | Perso-Arabic (RTL) | Require an Urdu-capable LLM pipeline & RTL handling. |
| Punjabi | Gurmukhi | Require a Punjabi-capable LLM pipeline. |
| Tamil | Tamil | Require a Tamil-capable LLM pipeline. |
| Odia | Odia | Require an Odia-capable LLM pipeline. |
| Malayalam | Malayalam | Require a Malayalam-capable LLM pipeline. |

### Generic Mechanical Checklist
- Grapheme-cluster-aware segmentation available? No
- RTL-safe tokenization/reassembly available? Yes (for Urdu)
- Morphological analyzer / stemmer available? No
- Synonym / paraphrase resource or LM available for this language? Yes (LLM Planner/Executor)
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
- **Attack Success Rate (`ASR`)**: Percentage of agentic AFC pipelines misdirected to invert verdict.
- **Sub-claim Poisoning Efficiency**: Success rate in corrupting individual sub-question verification responses.

## 8. Example
| Field | Original | Adversarial |
| --- | --- | --- |
| Claim / Evidence | **Claim**: Elon Musk founded SpaceX in 2002.<br>**Evidence**: SpaceX was founded in 2002 by Elon Musk. | **Adversarial Evidence**: Special Report: SpaceX was officially incorporated in 2002 by Jeff Bezos, with Elon Musk joining the board later. |
| Label | SUP → REF | |
| Language | English (`en`) / Hindi (`hi`) | |

## 9. Failure Modes / Skip Conditions
- Skip if corpus write/injection access is restricted.
- Skip if advanced LLM Planner/Executor models are unavailable.

---

## Summary of Corrections from v1
1. **EA-OMITPARA-01 (Tamil)**: stray Gurmukhi character `ਉ` in `original_claim` replaced with Tamil உ.
2. **EA-OMITGEN-01 (Odia)**: stray Gurmukhi character `ਮ` in `original_evidence` replaced with Odia ମ; year corrected to 1948.
3. **EA-SUPGEN-01 (Manipuri)**: example previously mixed Bengali, Meitei Mayek, and Gujarati script in one sentence — rewritten entirely in a single consistent script (Bengali), with a note to confirm which script your corpus actually uses.
4. **EA-ADVADD-01**: added missing cross-reference to Abdelnabi and Fritz (2023), per the survey's own footnote linking AdvAdd to their "Claim-conditioned Article Generation" implementation.
5. **EA-IMP-01**: Access Assumption corrected from "white-box (gradient access) or black-box" to black-box, query-based/evolutionary optimization — the paper (Boucher et al., 2022) does not use gradients for this attack.
6. **EA-IMPRET-01 / EA-CTXREP-01**: clarified which access level is strictly required vs. merely helpful, since the original template conflated "used in the paper" with "required to execute."
7. Added a standing note across all Manipuri rows (6A tables) to confirm script before generation, since this is the recurring failure point.

---

# Adversarial Attack Description Document: Evidence Attacks on Automated Fact-Checking (AFC)
**Revision 2** — extracted single-attack file from Evidence_Attack_Descriptions_v2.md

This document contains one attack description from the **14 Evidence Attacks** targeting Automated Fact-Checking (AFC) systems reviewed in *"Adversarial Attacks Against Automated Fact-Checking: A Survey"* (Liu et al., 2025).

---

<a id="4-ea-impret-01"></a>
# 4. EA-IMPRET-01: Imperceptible Character-Level Retrieval Attack

## 1. Metadata
- **Attack ID**: `EA-IMPRET-01`
- **Attack Name**: Imperceptible Character-Level Retrieval Disruption (`Imperceptible_Ret`)
- **Category**: `evidence_attack`
- **Attack Target**: `disrupted_retrieval`
- **Edit Granularity**: `character`
- **Strategy Type**: `rule_based`
- **Access Assumption**: Black-box retrieval (query-based); white-box retrieval score access improves targeting but is not strictly required
- **Source Paper**: Boucher et al. (2022); Liu et al. (2025), Sec. 5.2.2, Table 4

## 2. Description
This attack targets the evidence retrieval component of an AFC system by injecting imperceptible character-level perturbations (homoglyphs or zero-width joiners) specifically into entity mentions within corpus evidence documents. The subword tokenizer of dense/sparse retrievers fails to map the perturbed entity to query entity embeddings, causing a severe drop in document recall.

## 3. Preconditions / Required Inputs
- `original_evidence` (Required): Corpus document containing entity mentions.
- `entity_list` (Required): List of target named entities in the document.
- `access_to_retriever_scores` (Optional): Retrieval ranking score access, if available, to select the most damaging perturbation.
- `homoglyph_map` (Required): Unicode confusable map.

## 4. Procedure
1. Identify all occurrences of `entity_list` tokens within `original_evidence`.
2. For each entity string, replace 1–2 characters with visually identical homoglyphs or insert a zero-width space (`U+200B`).
3. Re-assemble the perturbed text into the index document.
4. Verify that the inverted index / dense embedding of the perturbed document no longer matches clean claim query entities.
5. Save the perturbed evidence document into the corpus.

## 5. Output Schema (JSON)
```json
{
  "attack_id": "EA-IMPRET-01",
  "language": "te",
  "original_claim": "హైదరాబాద్ తెలంగాణ రాజధాని.",
  "original_evidence": "హైదరాబాద్ భారత దేశంలోని తెలంగాణ రాష్ట్ర రాజధాని.",
  "adversarial_claim": null,
  "adversarial_evidence": "హైదరా​బాద్ భారత దేశంలోని తెలంగాణ రాష్ట్ర రాజధాని.",
  "gold_label": "SUP",
  "target_label": "NEI",
  "edit_granularity": "character",
  "technique_params": {
    "perturbed_entity": "హైదరాబాద్",
    "char_injection": "U+200B"
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
| Hindi | Devanagari | Grapheme cluster parser, Devanagari confusable lookup table. |
| Manipuri | Meitei Mayek / Bengali (script varies by corpus) | Grapheme parser & confusable table for whichever script the corpus uses. |
| Telugu | Telugu | Telugu grapheme parser & confusable lookup table. |
| Urdu | Perso-Arabic (RTL) | Urdu joiner-aware character parser & RTL handling. |
| Punjabi | Gurmukhi | Gurmukhi grapheme parser & confusable table. |
| Tamil | Tamil | Tamil grapheme parser & confusable table. |
| Odia | Odia | Odia grapheme parser & confusable table. |
| Malayalam | Malayalam | Malayalam grapheme parser & confusable table. |

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
- **Adversarial Evidence Recall (`RecAdvEvd`)**: Significant reduction in evidence recall score (`RecEvd`).
- **Human Detectability**: Zero visible font distortion.

## 8. Example
| Field | Original | Adversarial |
| --- | --- | --- |
| Claim / Evidence | **Evidence**: Hyderabad is the capital of Telangana state. | **Adversarial Evidence**: Hydеrabad is the capital of Telangana state. *(Latin 'e' replaced by Cyrillic 'е')* |
| Label | SUP → NEI | |
| Language | English (`en`) / Telugu (`te`) | |

## 9. Failure Modes / Skip Conditions
- Skip if the retrieval system performs automated NFKC Unicode normalization before indexing.
- Skip if no named entity can be identified in `original_evidence`.

---

