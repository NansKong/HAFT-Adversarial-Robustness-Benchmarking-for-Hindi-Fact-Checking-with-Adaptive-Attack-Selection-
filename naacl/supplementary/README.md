# HAFT: Anonymous Supplementary Material
## Hindi Automated Fact-Checking Adversarial Robustness Benchmark

This supplementary package accompanies the manuscript:
**"HAFT: Adversarial Robustness Benchmarking and Budget-Aware Adaptive Auditing Framework for Hindi Automated Fact-Checking"**
Submitted to NAACL (Double-Blind Review).

---

### Package Contents

1. **Quality Gating Rules (`quality_gating_rules.py`)**:
   - Deterministic, LLM-free dual-layer quality gate in pure Python.
   - Layer 1: Devanagari orthographic integrity (Unicode block `U+0900`--`U+097F`, illegal stacked diacritics, orphaned viramas/halants, akshara repetition $\ge 4$).
   - Layer 2: Surface invariance check (token Jaccard $\ge 0.50$ or ChrF++ character $n$-gram $F \ge 0.60$) for meaning-preserving attacks; meaning-drift bypass for evidence-injection attacks.

2. **Human Calibration & Confusion Tables (`human_calibration_confusion_tables.md`)**:
   - Double-annotation protocol on 300 stratified instances across 4 tiers (75 per tier).
   - Confusion Matrix: Annotator 1 vs. Annotator 2 ($96.7\%$ agreement, Cohen's $\kappa = 0.946$).
   - Confusion Matrix: Consensus Human vs. Automated Quality Gate ($93.3\%$ agreement, Cohen's $\kappa = 0.881$).
   - Fluency ($94.7\%$) and Task Adherence ($92.0\%$) metric decompositions.
   - Error analysis for the 40 disagreement judgments across 600 evaluations (16 in fluency: 6 dialectal diacritics/nuktas + 10 colloquial spacing/conjunct variants; 24 in task adherence: 14 colloquial register shifts + 10 borderline semantic shifts).

3. **Accepted and Rejected Devanagari Perturbation Examples (`accepted_rejected_devanagari_examples.md`)**:
   - Paired original vs. perturbed Devanagari text examples across all 4 attack tiers.
   - English translations, specific failure mechanisms, gate verdict (Accept/Reject), and gating rule triggered.

4. **Attack Implementations & Tooling (`attacks/`, `llm_attacks/`)**:
   - 14 rule-based Devanagari perturbation algorithms.
   - 8 LLM-based generative prompt templates and harness scripts.

5. **Budgeted Auditing & Reinforcement Learning (`rl/`, `replay_env.py`)**:
   - Gym-style frozen environment (`replay_env.py`) for reproducible budgeted auditing ($K \le 5$).
   - REINFORCE policy network with invalid action masking (`rl/`).
   - 5-seed evaluation logs and offline coverage-aware greedy policy implementation.

6. **Benchmark Dataset Sample (`sampled_dataset_1120.csv`)**:
   - 1,120 claims across 6 civic domains with gold labels, source attribution URLs, and domain partitions.
