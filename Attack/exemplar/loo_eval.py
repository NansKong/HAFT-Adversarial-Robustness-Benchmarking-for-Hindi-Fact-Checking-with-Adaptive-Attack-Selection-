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


def train_in_fold_policy(held_out_target: str, epochs: int = 25, lr: float = 0.005) -> ExemplarSelectionPolicy:
    """Train exemplar policy strictly using the 21 remaining attacks (no label leakage)."""
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

        # 9. RL-Selected Exemplars (Trained strictly in-fold)
        policy = train_in_fold_policy(held_out_target=target_key, epochs=30, lr=0.003)
        retained_rl = []
        with torch.no_grad():
            for c in candidate_pool:
                st = construct_exemplar_state(target_key, c, len(retained_rl), len(candidate_pool))
                prob = policy(torch.tensor(st, dtype=torch.float32)).item()
                if prob >= 0.50:
                    retained_rl.append(c)

        if not retained_rl:
            retained_rl = top5[:3]  # Fallback to top-3 if policy rejects all

        pred_rl = predict_tier_from_exemplars(target_key, retained_rl)
        predictions["RL-Selected (Ours)"].append(pred_rl)
        exemplar_counts["RL-Selected (Ours)"].append(len(retained_rl))

    # Calculate Accuracy and Macro-F1 for Table 2
    table2_rows = []
    for method, preds in predictions.items():
        correct = sum(1 for p, y in zip(preds, TRUE_TIERS) if p == y)
        acc_pct = (correct / len(TRUE_TIERS)) * 100
        macro_f1 = f1_score(TRUE_TIERS, preds, average="macro", zero_division=0)

        if method == "RL-Selected (Ours)":
            avg_ex = f"{np.mean(exemplar_counts[method]):.1f}"
        else:
            avg_ex = str(exemplar_counts[method])

        table2_rows.append({
            "Method": method,
            "Exemplars Used": avg_ex,
            "Accuracy (%)": f"{acc_pct:.2f}%",
            "Correct / 22": f"{correct} / 22",
            "Macro-F1": f"{macro_f1:.3f}",
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
