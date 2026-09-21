# Hindi AFC Adversarial Attack Benchmark — Progress Report

> **Updated:** 2026-09-04, 01:27 IST  
> **Workspace:** `E:\Attack\Attack`  
> **Status:** 🟢 **Phases A, B, and C 100% Completed** | 🟡 **Phase D (Streamlit Dashboard) Next**

---

## 1. Project Overview

The **Hindi Automated Fact-Checking (AFC) Adversarial Attack Benchmark** is an empirical research system designed to measure how vulnerable state-of-the-art LLM-based fact-checking systems are to Devanagari adversarial perturbations in Hindi.

**The Core Problem it Solves:**  
Five major LLMs (Claude, DeepSeek, Kimi, Sarvam, RefSheet) disagreed on **45%** of attack feasibility predictions when asked theoretically. This project resolves that ambiguity with a real, empirical ground-truth benchmark producing hard Attack Success Rate (ASR) metrics across 22 attack techniques, followed by a calibrated predictor.

---

## 2. System Architecture Summary

```
┌──────────────────────────────────────────────────────────┐
│  LAYER 1: RESEARCH (Attack Generation)                   │
│  ├── 14 Rule-Based Attacks (Pure Python, $0.00 cost)     │
│  └── 8 LLM-Based Attacks (Replicate API: gpt-4o-mini)   │
└──────────────────────────────────────────────────────────┘
                         ▼
┌──────────────────────────────────────────────────────────┐
│  LAYER 2: INTELLIGENCE (Verification & Judging)          │
│  ├── Phase A: AFC Verifier & Quality Judge (gpt-4o-mini) │
│  ├── Phase B: 5-LLM Empirical Comparison Matrix          │
│  └── Phase C: Calibrated Few-Shot Feasibility Predictor  │
└──────────────────────────────────────────────────────────┘
                         ▼
┌──────────────────────────────────────────────────────────┐
│  LAYER 3: INTERFACE (Analytics)                          │
│  └── Streamlit App (4 Tabs, ASR Matrix, Predictor)       │
└──────────────────────────────────────────────────────────┘
```

---

## 3. Stratified Dataset (1,120 Claims)

| Property | Value |
| :--- | :--- |
| **File** | `sampled_dataset_1120.csv` |
| **Total Claims** | **1,120 rows** |
| **Domains** | 6 Hindi Fact-Checking Domains |
| **Label Distribution** | 571 SUP / 350 REF / 199 NEI |
| **Stratification Seed** | `--seed 42` (deterministic & reproducible) |

### Domain Breakdown

| Domain | Rows | SUP | REF | NEI |
| :--- | :---: | :---: | :---: | :---: |
| Crime & Public Safety | 175 | 70 | 105 | 0 |
| Celebrity News | 189 | 66 | 60 | 63 |
| Disaster & Breaking News | 189 | 63 | 63 | 63 |
| Government Schemes | 189 | 173 | 10 | 6 |
| Health & Medicine | 189 | 63 | 63 | 63 |
| Politics & Election | 189 | 136 | 49 | 4 |
| **TOTAL** | **1,120** | **571** | **350** | **199** |

---

## 4. 22-Attack Taxonomy

### A. 14 Rule-Based Attacks (Pure Python — $0.00 Cost)
| # | Attack ID | Type |
| :--- | :--- | :--- |
| 1 | `CA_CHAR_01_CharacterSwapping` | Character-level |
| 2 | `CA_CHAR_02_CharacterRepetition` | Character-level |
| 3 | `CA_CHAR_03_CharacterInsertion` | Character-level |
| 4 | `CA_CHAR_04_CharacterDeletion` | Character-level |
| 5 | `CA_CHAR_05_HomoglyphPerturbation` | Character-level |
| 6 | `CA_WORD_02_EntityDisambiguation` | Word-level |
| 7 | `CA_WORD_03_Jumbling` | Word-level |
| 8 | `CA_WORD_04_Typos` | Word-level |
| 9 | `CA_WORD_08_LexicalSubstitution` | Word-level |
| 10 | `CA_WORD_12_Synonyms` | Word-level |
| 11 | `CA_WORD_13_PhoneticPerturbation` | Word-level |
| 12 | `CA_03_LexicallyInformed` | Lexical |
| 13 | `EA_IMP_01_ImperceptibleVerification` | Embedding |
| 14 | `EA_OMITOMISSION_01_OmissionGeneration` | Embedding |

### B. 8 LLM-Based Attacks (Replicate API: `gpt-4o-mini`)
| # | Attack ID | Injected Evidence? |
| :--- | :--- | :---: |
| 1 | `CA_07_AdvTrigger` | No |
| 2 | `CA_06_FactMixing` | No |
| 3 | `CA_16_Colloquial` | No |
| 4 | `EA_CLAIMREWRITE_01_ClaimRewrite` | No |
| 5 | `EA_CTXREP_01_ContextualizedReplace` | No |
| 6 | `EA_ADVADD_01_AdvAdd` | ✅ Yes |
| 7 | `EA_FACT2FICT_01_Fact2Fiction` | ✅ Yes |
| 8 | `EA_IMPRET_01_ImperceptibleRetrieval` | ✅ Yes |

> **Injected Evidence Workaround:** For the 3 evidence-poisoning attacks, the verifier receives:  
> `Original Evidence + " एक अन्य स्रोत के अनुसार: " + Fabricated Evidence`  
> This simulates small-scale corpus poisoning.

---

## 5. Pipeline Execution Log

### Step 1 — Dataset Sampling (✅ 100% Completed)
* **Output:** `sampled_dataset_1120.csv` (1.08 MB) | **API Cost:** $0.00 (Pure Python)

### Step 2 — Rule-Based Attack Generation (✅ 100% Completed)
* **Output Dir:** `output/full_run/` (14 CSV files, 15,680 attacked claims) | **API Cost:** $0.00

### Step 3 — LLM-Based Attack Generation (✅ 100% Completed)
* **Output Dir:** `output_llm/full_run/` (8 CSV files, 8,960 attacked claims) | **Cost:** ~$1.20 USD
* **Engineering Feature:** WinError 1450 retry loop (5 attempts + exponential sleep) for Windows file handle locking on `.cache/` (8,960 files).

### Step 4 — Phase A: Verification & Quality Judging (✅ 100% COMPLETED)
* **Total Evaluations Completed:** **25,760 / 25,760** (1,120 clean baseline + 24,640 attack instances).
* **Clean Baseline Accuracy:** **74.29%** (832 / 1,120 clean claims correctly verified).
* **Outputs:** `results/full_run/summary.json`, 22 per-attack CSV files, `results/full_run/.verify_cache/` (21,045 cached JSON files).

#### Empirical Key Findings (Gated ASR Summary)
| Rank | Attack Module | Attack Type | Gated ASR (%) | Raw ASR (%) | Empirical Bucket |
| :---: | :--- | :--- | :---: | :---: | :---: |
| 1 | `EA_CTXREP_01_ContextualizedReplace` | Evidence Replace | **59.57%** | 63.52% | **POS** |
| 2 | `EA_ADVADD_01_AdvAdd` | Poisoned Evidence | **58.47%** | 61.00% | **POS** |
| 3 | `EA_FACT2FICT_01_Fact2Fiction` | Fictional Evidence | **57.60%** | 61.33% | **POS** |
| 4 | `CA_06_FactMixing` | Fact Blending | **55.81%** | 59.82% | **POS** |
| 5 | `EA_CLAIMREWRITE_01_ClaimRewrite` | Masked Rewrite | **25.39%** | 28.49% | **MID** |
| 6 | `EA_OMITOMISSION_01_OmissionGeneration` | Syntactic Omission | **19.62%** | 21.72% | **MID** |
| 7 | `CA_WORD_03_Jumbling` | Word Shuffle | **12.57%** | 12.57% | **NEG** |
| 8-22 | Character Swaps, Typos, Homoglyphs | Mechanical Noise | **< 3.50%** | < 4.00% | **NEG** |

---

## 6. Phase B — 5-LLM Empirical Comparison Matrix (✅ 100% COMPLETED, $0.00 Cost)

* **Script:** `phase_b_comparison.py` | **Output:** `results/full_run/llm_comparison.csv`

### Model Accuracy Leaderboard
| Rank | Model Architecture | Prediction Accuracy (%) | Correct / 22 Attacks | Primary Finding |
| :---: | :--- | :---: | :---: | :--- |
| **1** | **DeepSeek-V3** | **72.73%** | **16 / 22** | Accurately recognized LLM resilience to character noise |
| **2** | **Sarvam AI** *(Indic Native)* | **40.91%** | **9 / 22** | Better calibrated on Devanagari phonetic noise |
| **3** | **OpenAI (GPT-4o)** | **27.27%** | **6 / 22** | Severely overestimated character/typo attack feasibility |
| **4** | **Anthropic (Claude 3.5)** | **27.27%** | **6 / 22** | Overestimated character/typo attack feasibility |
| **5** | **Moonshot (Kimi-k1.5)** | **27.27%** | **6 / 22** | Overestimated character/typo attack feasibility |
| **-** | **5-LLM Consensus Vote** | **27.27%** | **6 / 22** | Majority vote failed due to collective overestimation |

---

## 7. Phase C — Calibrated Few-Shot Predictor (✅ 100% COMPLETED, $0.00 Cost)

* **Script:** `run_predictor.py` | **Output:** `results/full_run/calibrated_predictions.json`

### SOTA Predictor Evaluation (Leave-One-Out Cross-Validation)
| Evaluation Metric | Baseline / Predictor | Accuracy (%) | Performance |
| :--- | :--- | :---: | :---: |
| **Uncalibrated Baseline** | Raw 5-LLM Zero-Shot Guessing | **27.27%** | 6 / 22 attacks correct |
| **Calibrated Predictor** | Ground-Truth Few-Shot In-Context Engine | **86.36%** | **19 / 22 attacks correct** |
| **SOTA Accuracy Jump** | **Calibrated vs. Raw Zero-Shot** | 🚀 **+59.09%** | **Massive calibration boost!** |

---

## 8. Artifacts & Audit Files Summary

| Category | Path / File | Purpose / Status |
| :--- | :--- | :--- |
| Stratified Sample | `sampled_dataset_1120.csv` (1.08 MB) | 1,120 Hindi claims across 6 domains |
| Rule Attack Output | `output/full_run/` (14 CSV files) | 15,680 rule-perturbed claims |
| LLM Attack Output | `output_llm/full_run/` (8 CSV files) | 8,960 LLM-generated claims |
| LLM Generation Audit | `llm_audit.jsonl` (17.4 MB) | Audit log for attack generation |
| Verifier Audit | `verifier_audit.jsonl` (~91 MB) | Audit log for all verifier API calls |
| Judge Audit | `judge_audit.jsonl` (~3.6 MB) | Audit log for quality judge calls |
| Verification Cache | `results/full_run/.verify_cache/` | 21,045 cached evaluation JSON files |
| Final Summary JSON | `results/full_run/summary.json` | Master Phase A ground-truth metrics |
| 5-LLM Matrix CSV | `results/full_run/llm_comparison.csv` | Phase B empirical comparison table |
| Phase B Summary | `results/full_run/phase_b_summary.json` | 5-LLM Leaderboard summary metrics |
| Calibrated Predictions | `results/full_run/calibrated_predictions.json` | Phase C Leave-One-Out predictor results |

---

## 9. Final Phase Status & Roadmap

| Phase | Status | Description |
| :--- | :---: | :--- |
| **Phase A** | ✅ **100%** | Ground Truth Benchmark across 1,120 claims $\times$ 22 attacks |
| **Phase B** | ✅ **100%** | 5-LLM Empirical Comparison Matrix (`llm_comparison.csv`) |
| **Phase C** | ✅ **100%** | Calibrated Few-Shot Predictor (`calibrated_predictions.json`) |
| **Phase D (Interface)** | 🟡 **NEXT** | 4-tab Streamlit web application (`app.py`) |

---

*Report fully updated following Phase C completion on 2026-09-04T01:27 IST.*
