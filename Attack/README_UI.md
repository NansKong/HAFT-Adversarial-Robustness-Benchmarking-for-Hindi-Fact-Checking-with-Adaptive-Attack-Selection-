# 🛡️ Hindi Fact-Checking Adversarial Attack Benchmark UI

A Streamlit web application for exploring the empirical benchmark results of 22 adversarial attack vectors on Hindi Fact-Checking AI models and testing the Leave-One-Out (LOO) Calibrated Few-Shot Feasibility Predictor.

---

## 🚀 Quick Start

To launch the web interface in your browser, open a terminal in the project directory (`e:\Attack\Attack`) and run:

```bash
streamlit run app.py
```

---

## 🎨 Features & Tabs

### 🏛️ Tab 1: Overview & Architecture
* **Key Metrics Banner**: 22 evaluated attack vectors, 1,120 benchmarked Hindi news rows, 86.36% SOTA calibrated predictor accuracy (+59.09% jump vs zero-shot LLMs).
* **3-Layer System Architecture**: Visual map of Research Layer → Ground Truth Intelligence → Web Interface.
* **Core Findings**: Summary of mechanical surface noise ineffectiveness vs semantic evidence poisoning dominance across 8 domains.

### 🔬 Tab 2: Ground Truth KB Explorer
* **Interactive Filters**: Filter 22 attack techniques by engine type (Rule-based vs LLM-based) and edit granularity (Character, Word, Sentence, Evidence).
* **Gated ASR & Vulnerability Tier**: Displays exact Gated ASR %, Raw ASR %, and Pos/Mid/Neg classification.
* **5-LLM Empirical Comparison Matrix**: Detailed table comparing zero-shot predictions from GPT-4o, Claude 3.5 Sonnet, DeepSeek V3, Kimi 1.5, Sarvam 2B, and 5-LLM Consensus against ground truth.
* **Real Hindi Sample Showcase**: Side-by-side comparison of original clean Hindi claims/evidence vs attacked versions with highlighted diffs and verifier verdicts.

### 🔮 Tab 3: Predict Custom Attack
* **Interactive Feasibility Predictor**: Input any custom adversarial attack proposal or choose from preset scenarios (e.g. Emoji insertion, syntactic negation removal, agentic deep fake news).
* **Instant Calibrated Inference**: Powered by Leave-One-Out (LOO) few-shot exemplars from ground-truth data.

### 📊 Tab 4: Benchmark Analytics & LLM Leaderboard
* **Vulnerability Leaderboard**: All 22 attacks sorted by Gated ASR %.
* **5-LLM Accuracy Leaderboard**: Empirical comparison showing DeepSeek V3 (72.73%) outperforming generalist models (27.27%).
* **LLM Miscalibration Analysis**: Top overestimation & underestimation patterns.
