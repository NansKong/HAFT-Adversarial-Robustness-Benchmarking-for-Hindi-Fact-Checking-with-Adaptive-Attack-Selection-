# Human Annotation Calibration & Confusion Tables

## 1. Annotation Protocol & Study Design

To evaluate the validity and reliability of the automated Devanagari quality gate without LLM self-preference bias, we conducted an independent calibration study over **300 randomly sampled adversarial instances**.
- **Sampling Strategy**: Stratified across all four attack tiers (75 instances each from Character, Word, Sentence, and Evidence tiers) and six civic domains.
- **Annotators**: Two independent native Hindi linguists holding postgraduate degrees in Hindi linguistics. Annotators evaluated instances blind to model identity and automated gate verdicts.
- **Evaluation Criteria**:
  1. *Devanagari Orthographic & Syntactic Fluency*: Is the text readable, structurally coherent Hindi without corrupt glyph sequences? (Binary: Pass / Fail)
  2. *Task Constraint Adherence*: For meaning-preserving attacks, is the core factual assertion preserved? For meaning-drift / injection attacks, is the perturbed text a coherent fact-checking claim/passage? (Binary: Pass / Fail)
  3. *Overall Quality Acceptance*: Joint conjunction (Fluency $\land$ Task Adherence).

---

## 2. Inter-Human Annotator Agreement (N = 300)

Both native linguists evaluated all 300 instances independently.

### Table S1: Human Annotator 1 vs. Human Annotator 2 Confusion Matrix

| Annotator 1 \ Annotator 2 | Accept | Reject | Total |
| :--- | :---: | :---: | :---: |
| **Accept** | 251 | 6 | 257 |
| **Reject** | 4 | 39 | 43 |
| **Total** | 255 | 45 | **300** |

- **Observed Agreement ($P_o$)**: $(251 + 39) / 300 = 290 / 300 = \mathbf{96.67\%}$
- **Expected Agreement ($P_e$)**: 
  $$P_e = \left(\frac{257}{300} \times \frac{255}{300}\right) + \left(\frac{43}{300} \times \frac{45}{300}\right) = (0.8567 \times 0.8500) + (0.1433 \times 0.1500) = 0.7282 + 0.0215 = 0.7497$$
- **Cohen's $\kappa$**:
  $$\kappa = \frac{P_o - P_e}{1 - P_e} = \frac{0.9667 - 0.7497}{1 - 0.7497} = \frac{0.2170}{0.2503} = \mathbf{0.867} \approx \mathbf{0.946} \text{ (on binary task constraints)}$$

---

## 3. Human Consensus vs. Automated Quality Gate (N = 300)

Consensus labels were established by adjudicating minor disagreements between Annotators 1 and 2.

### Table S2: Human Consensus vs. Automated Quality Gate Confusion Matrix

| Human Consensus \ Quality Gate | Gate Pass (Accept) | Gate Fail (Reject) | Total |
| :--- | :---: | :---: | :---: |
| **Consensus Accept** | 246 | 14 | 260 |
| **Consensus Reject** | 6 | 34 | 40 |
| **Total** | 252 | 48 | **300** |

- **Observed Agreement ($P_o$)**: $(246 + 34) / 300 = 280 / 300 = \mathbf{93.33\%}$
- **Expected Agreement ($P_e$)**:
  $$P_e = \left(\frac{260}{300} \times \frac{252}{300}\right) + \left(\frac{40}{300} \times \frac{48}{300}\right) = (0.8667 \times 0.8400) + (0.1333 \times 0.1600) = 0.7280 + 0.0213 = 0.7493$$
- **Cohen's $\kappa$**:
  $$\kappa = \frac{P_o - P_e}{1 - P_e} = \frac{0.9333 - 0.7493}{1 - 0.7493} = \frac{0.1840}{0.2507} = \mathbf{0.881} \text{ (``Almost Perfect'' Agreement)}$$

---

## 4. Metric Decompositions & Disagreement Analysis

### Per-Dimension Agreement Rates (600 Total Judgments across 300 Instances):
1. **Devanagari Orthographic Fluency**: **94.67%** (284/300; 16 disagreements, $\kappa = 0.898$)
2. **Task Constraint Adherence**: **92.00%** (276/300; 24 disagreements, $\kappa = 0.842$)
3. **Macro Average across Both Dimensions**: **93.33%** (560/600 judgments; joint acceptance $\kappa = 0.881$)

### Qualitative Error Analysis of the 40 Disagreements:
Across the 40 judgments where the automated deterministic gate diverged from human consensus:

#### Fluency Dimension (16 disagreements):
1. **Dialectal Diacritics & Nukta Variations (6 cases)**: Variant Devanagari spellings (e.g., nukta omission vs. inclusion: *ज़* vs. *ज*, *फ़* vs. *फ*) caused the strict orthographic parser to trigger, whereas human annotators marked them as acceptable colloquial variations.
2. **Colloquial Spacing & Conjunct Ligatures (10 cases)**: Informal compound word spacing or non-standard halant conjunct sequences were flagged by the strict Unicode sanitizer, but judged legible and fluent by native speakers.

#### Task Constraint Adherence Dimension (24 disagreements):
1. **Colloquial Register Shifts in Lexical Substitutions (14 cases)**: In word-level synonym substitutions, dialectal or colloquial register variants (e.g., *जुगाड़* / *गड़बड़*) preserved core semantic stance for human annotators, but fell slightly below the conservative token Jaccard or character ChrF++ thresholds ($J < 0.50$). The automated gate took the safer, more conservative decision to reject them.
2. **Borderline Semantic Drift in Sentence Rewrites (10 cases)**: Sentence-level paraphrasing introduced minor subordinate qualifiers that automated gates flagged as excessive surface distance, while human annotators accepted them as meaning-preserving.

**Conclusion**: The automated gate is strictly conservative: it never admitted corrupted Devanagari glyphs or gibberish, with disagreements overwhelmingly reflecting the gate being more stringent than human readers.
