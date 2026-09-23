# Seed-Level RL Evaluation Summary

**Source:** `rl_5seed_runs.json`  
**Configuration:** Flat RL, 859-dimensional state, hidden width 512, budget K=5, seeds 42-46  
**Evaluation:** Held-out test split from the claim-level 60/20/20 split; greedy evaluation with epsilon=0.0  
**Claims per seed:** 167  
**Training:** 25 epochs per seed, offline replay, zero new API calls

## Per-Seed Results

| Seed | Test claims | Claims with flip | Discovery rate | Median steps | Mean steps | API calls/claim |
|---:|---:|---:|---:|---:|---:|---:|
| 42 | 167 | 135 | 80.8383% | 1.0 | 1.3778 | 5.0 |
| 43 | 167 | 133 | 79.6407% | 1.0 | 1.7669 | 5.0 |
| 44 | 167 | 137 | 82.0359% | 1.0 | 1.2190 | 5.0 |
| 45 | 167 | 138 | 82.6347% | 2.0 | 1.9348 | 5.0 |
| 46 | 167 | 143 | 85.6287% | 1.0 | 1.7203 | 5.0 |
| **Mean +/- population SD** | **167** | **137.2** | **82.1557% +/- 2.0182%** | **1.2** | **1.6038** | **5.0** |

## Reporting Note

This file is a seed-level **held-out test evaluation summary**, not a validation-history summary. The committed `rl_5seed_runs.json` stores final per-seed test results but does not store the epoch-by-epoch validation histories or the epsilon-grid scores. Do not describe this artifact as validation performance. The report may state that epsilon=0.10 was the selected training configuration only when the separate epsilon-grid/validation output is included.
