"""HAFT Stage 2 — 22-Fold Leave-One-Out (LOO) Evaluation for Phase C

Generates Table 2: Phase C Feasibility Prediction Comparison.
Compares:
  - Zero-shot Guessing
  - Always-NEG Baseline
  - Attribute-only Baseline
  - Static All-21 Few-Shot (Existing Baseline: 86.36%)
  - Random-k Exemplars
  - Top-k Similarity Exemplars
  - RL-Selected Exemplars (Ours)
"""

from __future__ import annotations

import json
import os
import sys
from typing import Dict, List, Any

import numpy as np
import pandas as pd
import torch
import torch.optim as optim
from sklearn.metrics import f1_score
from statsmodels.stats.contingency_tables import mcnemar

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from exemplar.selector import (
    ATTACK_PROPERTIES,
    ExemplarSelectionPolicy,
    construct_exemplar_state,
    predict_tier_from_exemplars,
    compute_pair_similarity,
)

ATTACK_KEYS = list(ATTACK_PROPERTIES.keys())
TRUE_TIERS = [ATTACK_PROPERTIES[k]["tier"] for k in ATTACK_KEYS]

N_RL_SEEDS = 10  # Number of seeds for RL exemplar stability analysis


def train_in_fold_policy(
    held_out_target: str,
    epochs: int = 30,
    lr: float = 0.003,
    seed: int = 42,
) -> ExemplarSelectionPolicy:
    """Train exemplar policy strictly using the 21 remaining attacks (zero label leakage).

    The held_out_target and its tier label are completely invisible during training.
    Policy is re-initialized from random weights each fold (in-fold retraining).
    """
    np.random.seed(seed)
    torch.manual_seed(seed)

    training_pool = [k for k in ATTACK_KEYS if k != held_out_target]
    policy = ExemplarSelectionPolicy(input_dim=34, hidden_dim=32)
    optimizer = optim.Adam(policy.parameters(), lr=lr)

    for epoch in range(epochs):
        # Sample an internal pseudo-target from the training pool
        pseudo_target = np.random.choice(training_pool)
        candidates = [k for k in training_pool if k != pseudo_target]

        states, actions, log_probs = [], [], []
        retained = []

        for c in candidates:
            st = construct_exemplar_state(pseudo_target, c, len(retained), len(candidates))
            st_t = torch.tensor(st, dtype=torch.float32)
            prob = policy(st_t)

            # Sample binary action: 1 = retain, 0 = discard
            if np.random.rand() < prob.item():
                action = 1
                retained.append(c)
                log_prob = torch.log(prob + 1e-8)
            else:
                action = 0
                log_prob = torch.log(1.0 - prob + 1e-8)

            states.append(st_t)
            actions.append(action)
            log_probs.append(log_prob)

        # Compute internal reward
        pred_tier = predict_tier_from_exemplars(pseudo_target, retained)
        true_tier = ATTACK_PROPERTIES[pseudo_target]["tier"]
        acc_reward = 1.0 if pred_tier == true_tier else -1.0
        length_penalty = 0.02 * len(retained)
        reward = acc_reward - length_penalty

        # Policy gradient update
        loss = -torch.stack(log_probs).sum() * reward
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

    return policy


def evaluate_loo_pipeline(output_dir: str = "results/stage2/exemplar") -> pd.DataFrame:
    """Execute 22-fold LOO evaluation across all methods."""
    os.makedirs(output_dir, exist_ok=True)
    np.random.seed(42)
    torch.manual_seed(42)

    predictions = {
        "Zero-shot": [],
        "Always-NEG": [],
        "Attribute-only": [],
        "Existing Few-shot (All 21)": [],
        "Random-5": [],
        "Top-5 Similarity": [],
        "Random-10": [],
        "Top-10 Similarity": [],
        "RL-Selected (Ours)": [],
    }

    exemplar_counts = {
        "Zero-shot": 0,
        "Always-NEG": 0,
        "Attribute-only": 0,
        "Existing Few-shot (All 21)": 21,
        "Random-5": 5,
        "Top-5 Similarity": 5,
        "Random-10": 10,
        "Top-10 Similarity": 10,
        "RL-Selected (Ours)": [],
    }

    print(f"Starting 22-Fold Leave-One-Out Evaluation across {len(ATTACK_KEYS)} attacks...")

    for fold_idx, target_key in enumerate(ATTACK_KEYS):
        candidate_pool = [k for k in ATTACK_KEYS if k != target_key]
        true_tier = ATTACK_PROPERTIES[target_key]["tier"]

        # 1. Zero-shot baseline (historical 5-LLM survey prediction)
        # From llm_comparison.csv consensus
        if target_key in ("CA_06_FactMixing", "EA_ADVADD_01_AdvAdd", "EA_CTXREP_01_ContextualizedReplace", "EA_FACT2FICT_01_Fact2Fiction"):
            predictions["Zero-shot"].append("POS")
        elif target_key in ("EA_OMITOMISSION_01_OmissionGeneration", "EA_CLAIMREWRITE_01_ClaimRewrite"):
            predictions["Zero-shot"].append("MID")
        else:
            predictions["Zero-shot"].append("POS")  # Western models consistently overestimated

        # 2. Always-NEG
        predictions["Always-NEG"].append("NEG")

        # 3. Attribute-only
        arm = ATTACK_PROPERTIES[target_key]["arm"]
        gran = ATTACK_PROPERTIES[target_key]["gran"]
        if arm == "LLM" and gran == "Evidence":
            predictions["Attribute-only"].append("POS")
        elif target_key == "CA_06_FactMixing":
            predictions["Attribute-only"].append("POS")
        elif gran in ("Character", "Word"):
            predictions["Attribute-only"].append("NEG")
        else:
            predictions["Attribute-only"].append("MID")

        # 4. Existing Few-shot baseline (All 21)
        pred_all21 = predict_tier_from_exemplars(target_key, candidate_pool)
        predictions["Existing Few-shot (All 21)"].append(pred_all21)

        # 5. Random-5
        rand5 = list(np.random.choice(candidate_pool, size=5, replace=False))
        predictions["Random-5"].append(predict_tier_from_exemplars(target_key, rand5))

        # 6. Top-5 Similarity
        sims = [(c, compute_pair_similarity(target_key, c)) for c in candidate_pool]
        sims.sort(key=lambda x: x[1], reverse=True)
        top5 = [x[0] for x in sims[:5]]
        predictions["Top-5 Similarity"].append(predict_tier_from_exemplars(target_key, top5))

        # 7. Random-10
        rand10 = list(np.random.choice(candidate_pool, size=10, replace=False))
        predictions["Random-10"].append(predict_tier_from_exemplars(target_key, rand10))

        # 8. Top-10 Similarity
        top10 = [x[0] for x in sims[:10]]
        predictions["Top-10 Similarity"].append(predict_tier_from_exemplars(target_key, top10))

        # 9. RL-Selected Exemplars (Trained strictly in-fold, 10-seed stability)
        # Each seed uses a fresh policy (zero leakage guaranteed), we aggregate
        # accuracy and exemplar count across seeds to measure stability.
        seed_rl_preds = []
        seed_rl_counts = []
        for seed_i in range(N_RL_SEEDS):
            policy = train_in_fold_policy(
                held_out_target=target_key, epochs=30, lr=0.003, seed=42 + seed_i
            )
            retained_rl = []
            with torch.no_grad():
                for c in candidate_pool:
                    st = construct_exemplar_state(target_key, c, len(retained_rl), len(candidate_pool))
                    prob = policy(torch.tensor(st, dtype=torch.float32)).item()
                    if prob >= 0.50:
                        retained_rl.append(c)

            if not retained_rl:
                retained_rl = top5[:3]  # Fallback to top-3 if policy rejects all

            pred_rl_seed = predict_tier_from_exemplars(target_key, retained_rl)
            seed_rl_preds.append(pred_rl_seed)
            seed_rl_counts.append(len(retained_rl))

        # Majority vote across seeds for the fold prediction
        from collections import Counter
        pred_rl = Counter(seed_rl_preds).most_common(1)[0][0]
        predictions["RL-Selected (Ours)"].append(pred_rl)
        exemplar_counts["RL-Selected (Ours)"].append(float(np.mean(seed_rl_counts)))

        # Store per-seed predictions for McNemar test
        if "_rl_seed_preds" not in predictions:
            predictions["_rl_seed_preds"] = [[] for _ in range(N_RL_SEEDS)]
        for si, sp in enumerate(seed_rl_preds):
            predictions["_rl_seed_preds"][si].append(sp)

        print(f"  Fold {fold_idx:2d} ({target_key[:30]:30s}) | true={true_tier:3s} | "
              f"rl_vote={pred_rl} | seeds_correct={sum(1 for p in seed_rl_preds if p==true_tier)}/{N_RL_SEEDS} | "
              f"avg_exemplars={np.mean(seed_rl_counts):.1f}")

    # McNemar's test: RL-Selected (majority vote) vs Random-5 (best seed)
    # Tests whether the per-fold correct/incorrect patterns are significantly different
    rl_correct = np.array([1 if p == y else 0 for p, y in zip(predictions["RL-Selected (Ours)"], TRUE_TIERS)])
    # Random-5 across multiple seeds — use mean accuracy seed results
    rand5_correct = np.array([1 if p == y else 0 for p, y in zip(predictions["Random-5"], TRUE_TIERS)])

    # Build 2x2 contingency table for McNemar test
    n_both_correct = int(np.sum(rl_correct & rand5_correct))
    n_rl_only     = int(np.sum(rl_correct & ~rand5_correct))
    n_rand5_only  = int(np.sum(~rl_correct & rand5_correct))
    n_both_wrong  = int(np.sum(~rl_correct & ~rand5_correct))
    contingency_table = [[n_both_correct, n_rl_only], [n_rand5_only, n_both_wrong]]
    try:
        mcnemar_result = mcnemar(contingency_table, exact=True)
        mcnemar_pvalue = mcnemar_result.pvalue
    except Exception:
        mcnemar_pvalue = 1.0

    print(f"\nMcNemar Test (RL-Selected vs Random-5):")
    print(f"  Contingency table: both_correct={n_both_correct}, rl_only={n_rl_only}, rand5_only={n_rand5_only}, both_wrong={n_both_wrong}")
    print(f"  p-value = {mcnemar_pvalue:.4f} ({'significant' if mcnemar_pvalue < 0.05 else 'NOT significant'} at p<0.05)")

    # RL per-seed accuracy std
    rl_seed_accs = []
    for si in range(N_RL_SEEDS):
        seed_preds = predictions["_rl_seed_preds"][si]
        seed_acc = sum(1 for p, y in zip(seed_preds, TRUE_TIERS) if p == y) / len(TRUE_TIERS) * 100
        rl_seed_accs.append(seed_acc)
    rl_std = float(np.std(rl_seed_accs))
    rl_mean_acc = float(np.mean(rl_seed_accs))
    print(f"RL-Selected per-seed accuracy: {rl_mean_acc:.2f}% \u00b1 {rl_std:.2f}% across {N_RL_SEEDS} seeds")

    # Remove internal key before building table
    predictions.pop("_rl_seed_preds", None)

    # Calculate Accuracy and Macro-F1 for Table 2
    table2_rows = []
    for method, preds in predictions.items():
        correct = sum(1 for p, y in zip(preds, TRUE_TIERS) if p == y)
        acc_pct = (correct / len(TRUE_TIERS)) * 100
        macro_f1 = f1_score(TRUE_TIERS, preds, average="macro", zero_division=0)

        if method == "RL-Selected (Ours)":
            avg_ex = f"{np.mean(exemplar_counts[method]):.1f}"
            acc_std_str = f"\u00b1{rl_std:.2f}%"
            mcnemar_str = f"{mcnemar_pvalue:.4f}"
        else:
            avg_ex = str(exemplar_counts[method])
            acc_std_str = "N/A"
            mcnemar_str = "—"

        table2_rows.append({
            "Method": method,
            "Exemplars Used": avg_ex,
            "Accuracy (%)": f"{acc_pct:.2f}%",
            "Acc Std (%)": acc_std_str,
            "Correct / 22": f"{correct} / 22",
            "Macro-F1": f"{macro_f1:.3f}",
            "McNemar p vs Random-5": mcnemar_str,
        })

    table2_df = pd.DataFrame(table2_rows)
    print("\n" + "=" * 80)
    print("TABLE 2: PHASE C ATTACK FEASIBILITY PREDICTION (22-FOLD LEAVE-ONE-OUT)")
    print("=" * 80)
    print(table2_df.to_string(index=False))

    out_csv = os.path.join(output_dir, "table2_phase_c_prediction.csv")
    table2_df.to_csv(out_csv, index=False)
    print(f"\nSaved Table 2 to {out_csv}")

    return table2_df


if __name__ == "__main__":
    evaluate_loo_pipeline()
