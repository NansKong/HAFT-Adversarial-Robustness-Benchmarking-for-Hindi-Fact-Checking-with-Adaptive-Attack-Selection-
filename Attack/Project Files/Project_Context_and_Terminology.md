# Project Context & Terminology Guide

---

## What Is This Project?

We are building a system that answers one question: **"Will this adversarial attack work on a Hindi fact-checking model?"**

Instead of guessing whether an attack might work (like an LLM does), we actually run the attack on real Hindi data and measure the result. This produces evidence-backed answers, not guesses.

The project has three layers:
1. **Research Layer** — our team runs 22 attacks on 1,120 Hindi rows and measures real success rates
2. **Intelligence Layer** — the measured results are saved as data files, always available
3. **Interface Layer** — a Streamlit web app where anyone asks a question and gets an evidence-backed answer

---

## Key Concept: Why This Project Exists

Five LLMs (Claude, DeepSeek, Kimi, Sarvam, RefSheet) were asked to judge whether each of 53 attacks would work in Hindi. They disagreed on 45% of attacks. This proved that LLM guessing is unreliable. Our project resolves that disagreement with real, measured evidence.

---

## Core Terminology

### Fact-Checking (FC)
The task of verifying whether a claim is true, false, or unverifiable, based on evidence. Traditionally done by humans.

### Automated Fact-Checking (AFC)
Using AI/ML models to automatically verify claims against evidence. Our verifier is an AFC system.

### Claim
A statement that needs to be verified. Example: "दिल्ली भारत की राजधानी है" (Delhi is the capital of India).

### Evidence
A text passage that supports, refutes, or is insufficient for a claim. Example: "नई दिल्ली भारत का राजधानी शहर है" (New Delhi is the capital city of India).

### Gold Label
The correct/true verdict for a claim-evidence pair, assigned by human annotators. One of:
- **SUP (Supported)** — the evidence supports the claim
- **REF (Refuted)** — the evidence contradicts the claim
- **NEI (Not Enough Info)** — the evidence is insufficient to decide

### Verifier
The fact-checking model being attacked. It takes (claim, evidence) as input and returns SUP/REF/NEI. In our project, the verifier is an LLM (like Llama 3) called via API.

### Verdict
The output of the verifier — SUP, REF, or NEI.

---

## Attack Terminology

### Adversarial Attack
A deliberate manipulation of a claim or evidence designed to make the fact-checking model give a wrong verdict.

### Attack Engine
The module that generates attacked versions of claims or evidence. Two types:
- **Rule-based** — pure Python code modifies the text (no GPT needed). 14 attacks.
- **LLM-based** — an LLM generates the attacked text (needs a GPT API call). 8 attacks.

### Attacked Claim / Attacked Evidence
The modified version of the original text after an attack is applied. Example: "दिल्ली भारत की राजधानी है" → "दिल्ली भारत की राजधानी हsi" (Character Swapping attack).

### Attack Success
When the verifier gives a wrong verdict on the attacked text (different from the gold label). This means the attack successfully fooled the verifier.

### Attack Success Rate
The percentage of rows where an attack succeeded. Example: if Character Swapping fools the verifier on 67 out of 100 rows, the success rate is 67%.

### Edit Granularity
The level at which an attack modifies text:
- **Character-level** — changes individual characters (e.g., swap, delete, homoglyph)
- **Word-level** — changes whole words (e.g., synonyms, typos, jumbling)
- **Sentence-level** — rewrites or generates entire sentences (e.g., fact mixing, colloquial)

### Attack Target
What the attack aims to break:
- **Corrupted verdict** — the attack aims to flip the verifier's verdict (wrong label)
- **Disrupted retrieval** — the attack aims to prevent the correct evidence from being found

### Injected Evidence Workaround
Three attacks (AdvAdd, Fact2Fiction, ImperceptibleRet) are designed to poison a retrieval corpus, but our pipeline has no retrieval step. The workaround: the verifier receives the original evidence PLUS the attacker's fabricated evidence together, simulating corpus poisoning at small scale.

---

## Pipeline Terminology

### Pipeline
The sequence of steps that process each test instance:
```
Dataset Row → Attack Engine → Verifier → Judge → Result Record
```
No defense step. Three steps only.

### Test Instance
One row × one attack. Total in our project: 1,120 rows × 22 attacks = 24,640 test instances.

### Judge
The module that decides whether an attack succeeded. It compares the verifier's verdict against the gold label and checks:
- **Fluency** — is the attacked text still natural Hindi?
- **Meaning preservation** — does the attacked claim still mean the same thing?

Bad attacks (broken text, meaning drift) are excluded from results by the Judge.

### Logger
The module that saves every API call's full raw response to a JSONL file, for auditing.

---

## Validation Terminology

### Cohen's Kappa
A statistical measure of agreement between two human annotators. Scale: -1 to 1. We use it to validate that our dataset's gold labels are trustworthy. Target: > 0.60 (substantial agreement).

### Baseline Accuracy
How often the verifier gives the correct verdict on clean (unattacked) claims. Measured on 50 rows before the experiment. Target: > 70%.

### Baseline Failure
A row where the verifier gets the wrong verdict even on the clean, unattacked claim. These rows are excluded from attack success calculation because you can't measure attack success on a row where the verifier was already wrong.

---

## Phase Terminology

### Phase A — Ground Truth Generation
Run all 22 attacks on 1,120 rows through the pipeline. Produces a measured success rate (%) for each attack.

### Phase B — LLM-Guess Comparison
Convert each attack's measured success rate into Pos/Mid/Neg and compare against what the 5 LLMs predicted. Answers: which LLM guessed best, and by how much?

### Phase C — Calibrated Predictor
Use Phase A results as few-shot examples to prompt an LLM to predict feasibility for unseen attacks. If the calibrated predictor is more accurate than raw LLM guessing, that improvement is the project's SOTA (State-of-the-Art) claim.

### Pos / Mid / Neg
The 3-level scale used by the 5 LLMs to predict attack feasibility:
- **Pos** — the attack likely works (success rate > 50%)
- **Mid** — uncertain (success rate 20–50%)
- **Neg** — the attack likely doesn't work (success rate < 20%)

---

## Data Terminology

### Domain
A topic category of the dataset. We have 8 domains: Health, Politics, Sports, Science, Education, Economy, Entertainment, Technology. Each has 500 rows.

### Sampling
Selecting a subset of rows from the full dataset. We sample 140 rows per domain = 1,120 rows total, stratified by label (balanced SUP/REF/NEI).

### Stratified Sampling
Sampling that preserves the balance of labels (SUP/REF/NEI) so the sample is representative of the full dataset.

### 5-LLM Consensus Votes
The Pos/Mid/Neg predictions that 5 LLMs gave for all 53 attacks, collected before this project. Used in Phase B for comparison.

---

## Technical Terminology

### API Call
A single request-response to an LLM. Like sending a WhatsApp message and getting a reply. Our project needs ~59,360 API calls total.

### Concurrency
Running multiple API calls at the same time (in parallel) instead of one by one. We use 20 concurrent calls.

### SOTA (State-of-the-Art)
A claim that our system achieves something no prior system has done. Our SOTA claim: the first empirically-measured, calibrated adversarial-attack feasibility system for Hindi AFC, demonstrably more accurate than raw LLM guessing.

### Sear (Semantically Equivalent Adversarial Rules)
A technique used in some rule-based attacks to rewrite claims in ways that preserve meaning but confuse the model.

### Homoglyph
A character that looks identical or nearly identical to another but has a different Unicode codepoint. Example: Latin "a" vs Cyrillic "а". Used in homoglyph perturbation attacks.

### Few-Shot Prompting
Giving an LLM a few examples of input → output before asking it to predict on a new input. Used in Phase C where we give the LLM measured Phase A results as examples.

---

## People & Roles

### Annotator
A person who labels data. In our Kappa validation, two annotators independently label the same 50 rows per domain.

### Adjudication
When two annotators disagree, they discuss and agree on a final label. This resolved label becomes the locked gold label.

---

## Quick Reference Numbers

| Item | Value |
|------|-------|
| Total attacks | 22 (14 rule-based + 8 LLM-based) |
| Full dataset | 4,000 rows (8 domains × 500) |
| Sampled for experiment | 1,120 rows (140 per domain) |
| Sampled for Kappa | 400 rows (50 per domain) |
| Test instances | 24,640 (1,120 × 22) |
| Total API calls | ~59,360 |
| Budget | ~$9 (₹750) |
| Verifier rows for baseline test | 50 clean rows |
| Kappa target | > 0.60 |
| Baseline accuracy target | > 70% |
| Pos threshold | > 50% success rate |
| Mid threshold | 20–50% success rate |
| Neg threshold | < 20% success rate |
