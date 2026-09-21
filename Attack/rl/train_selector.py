"""HAFT Stage 2 — RL Attack Selector Training & Benchmark Evaluation

Evaluates across 5 random seeds using claim-level 60/20/20 splits:
  - 832 valid baseline claims (500 train / 166 val / 166 test)
  - Epsilon exploration tuned on the validation split
  - Compares against Random-5, Static Top-5, Bandit, and Oracle-22
  - Zero API calls (100% offline replay)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Dict, List, Any

import numpy as np
import pandas as pd
import torch

# Ensure Attack root is on path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from replay_env import OfflineAttackEnv, ATTACK_KEYS_22
from rl.reinforce import REINFORCEAgent
from rl.baselines import (
    evaluate_random_5,
    evaluate_static_top_5,
    evaluate_bandit,
    evaluate_oracle_22,
)


def split_claims(claim_ids: np.ndarray, seed: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Deterministic 60/20/20 claim-level train/val/test split."""
    rng = np.random.RandomState(seed)
    shuffled = claim_ids.copy()
    rng.shuffle(shuffled)

    n_total = len(shuffled)
    n_train = int(0.60 * n_total)
    n_val = int(0.20 * n_total)

    train_ids = shuffled[:n_train]
    val_ids = shuffled[n_train : n_train + n_val]
    test_ids = shuffled[n_train + n_val :]

    return train_ids, val_ids, test_ids


def train_rl_agent(
    env: OfflineAttackEnv,
    train_ids: np.ndarray,
    val_ids: np.ndarray,
    epochs: int = 15,
    epsilon: float = 0.30,
    seed: int = 42,
) -> Tuple[REINFORCEAgent, List[Dict[str, Any]]]:
    """Train the REINFORCE attack selector."""
    torch.manual_seed(seed)
    np.random.seed(seed)

    agent = REINFORCEAgent(state_dim=859, hidden_dim=256, num_actions=env.num_attacks)
    history = []

    for epoch in range(epochs):
        perm_train = np.random.permutation(train_ids)
        epoch_flips = 0
        epoch_rewards = []

        for cid in perm_train:
            state = env.reset(claim_id=int(cid))
            done = False

            states, actions, rewards, log_probs, masks = [], [], [], [], []

            while not done:
                action, log_prob, _ = agent.select_action(state, env.tried_mask, epsilon=epsilon)
                next_state, reward, done, info = env.step(action)

                states.append(state)
                actions.append(action)
                rewards.append(reward)
                log_probs.append(log_prob)
                masks.append(env.tried_mask.copy())

                state = next_state

            update_metrics = agent.update(states, actions, rewards, log_probs, masks)
            epoch_rewards.append(sum(rewards))
            if env.episode_flips > 0:
                epoch_flips += 1

        train_discovery_pct = (epoch_flips / len(train_ids)) * 100
        mean_reward = float(np.mean(epoch_rewards))

        # Evaluate on validation split (zero exploration)
        val_metrics = evaluate_rl_agent(env, agent, val_ids)

        history.append({
            "epoch": epoch + 1,
            "train_discovery_pct": train_discovery_pct,
            "train_mean_reward": mean_reward,
            "val_discovery_pct": val_metrics["success_rate_pct"],
            "val_median_steps": val_metrics["median_steps_to_flip"],
        })

    return agent, history


def evaluate_rl_agent(
    env: OfflineAttackEnv, agent: REINFORCEAgent, claim_ids: np.ndarray
) -> Dict[str, Any]:
    """Evaluate trained policy deterministically without exploration on test claims."""
    flips_discovered = []
    steps_to_first_flip = []
    action_counts = np.zeros(env.num_attacks, dtype=int)
    total_calls = 0

    cumulative_discovery_at_k = {k: 0 for k in range(1, env.max_budget_k + 1)}

    for cid in claim_ids:
        state = env.reset(claim_id=int(cid))
        done = False
        found_flip = False
        first_step = None

        while not done:
            # Deterministic greedy evaluation
            action, _, probs = agent.select_action(state, env.tried_mask, epsilon=0.0)
            next_state, reward, done, info = env.step(action)
            action_counts[action] += 1
            total_calls += 1

            if info["gated_flip"]:
                if not found_flip:
                    found_flip = True
                    first_step = info["step"]
                    steps_to_first_flip.append(first_step)

                # Record discovery at each k
                for k in range(info["step"], env.max_budget_k + 1):
                    cumulative_discovery_at_k[k] += 1

            state = next_state

        flips_discovered.append(1 if found_flip else 0)

    success_rate = float(np.mean(flips_discovered) * 100)
    median_steps = float(np.median(steps_to_first_flip)) if steps_to_first_flip else 0.0
    mean_steps = float(np.mean(steps_to_first_flip)) if steps_to_first_flip else 0.0

    return {
        "method": "RL-Selector (Ours)",
        "budget": env.max_budget_k,
        "success_rate_pct": success_rate,
        "total_claims": len(claim_ids),
        "claims_with_flip": int(sum(flips_discovered)),
        "median_steps_to_flip": median_steps,
        "mean_steps_to_flip": mean_steps,
        "total_api_calls": total_calls,
        "calls_per_claim": total_calls / max(1, len(claim_ids)),
        "action_distribution": action_counts.tolist(),
        "discovery_at_k": {
            k: float(cumulative_discovery_at_k[k] / len(claim_ids) * 100)
            for k in cumulative_discovery_at_k
        },
    }


def main():
    parser = argparse.ArgumentParser(description="HAFT Stage 2: Train and evaluate RL Attack Selector.")
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 43, 44, 45, 46])
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--output-dir", default="results/stage2/rl")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    embeddings_path = os.path.join(BASE_DIR, "data", "claim_embeddings_indicbert_1120.pt")

    print(f"Loading IndicBERT embeddings from {embeddings_path}...")
    embeddings = torch.load(embeddings_path, weights_only=True)

    env = OfflineAttackEnv(
        base_dir=BASE_DIR,
        max_budget_k=5,
        claim_embeddings=embeddings,
        exclude_baseline_failures=True,
    )

    print(f"Loaded Offline Environment: {len(env.valid_claim_ids)} valid baseline claims.")
    valid_ids = env.valid_claim_ids

    # Epsilon Grid Search on Seed 42
    print("\n--- Tuning Epsilon on Validation Split (Seed 42) ---")
    train_ids, val_ids, test_ids = split_claims(valid_ids, seed=42)
    eps_candidates = [0.05, 0.10, 0.20, 0.30, 0.40]
    best_eps = 0.30
    best_val_score = -1.0

    for eps in eps_candidates:
        agent, _ = train_rl_agent(env, train_ids, val_ids, epochs=8, epsilon=eps, seed=42)
        val_eval = evaluate_rl_agent(env, agent, val_ids)
        score = val_eval["success_rate_pct"]
        print(f"  Epsilon {eps:.2f} -> Val Discovery Rate: {score:.2f}%, Median Steps: {val_eval['median_steps_to_flip']}")
        if score > best_val_score:
            best_val_score = score
            best_eps = eps

    print(f"Selected Optimal Epsilon: {best_eps:.2f}\n")

    # Multi-seed Evaluation
    all_runs = []
    print(f"--- Running 5-Seed Evaluation across seeds: {args.seeds} ---")

    for seed in args.seeds:
        train_ids, val_ids, test_ids = split_claims(valid_ids, seed=seed)
        print(f"\n[Seed {seed}] Training RL Selector (Train: {len(train_ids)}, Val: {len(val_ids)}, Test: {len(test_ids)})...")

        agent, history = train_rl_agent(env, train_ids, val_ids, epochs=args.epochs, epsilon=best_eps, seed=seed)

        # Evaluate on held-out test set
        rl_res = evaluate_rl_agent(env, agent, test_ids)
        rand_res = evaluate_random_5(env, test_ids, seed=seed)
        top5_res = evaluate_static_top_5(env, test_ids)
        bandit_res = evaluate_bandit(env, test_ids)
        oracle_res = evaluate_oracle_22(env, test_ids)

        all_runs.append({
            "seed": seed,
            "RL": rl_res,
            "Random-5": rand_res,
            "Static-Top5": top5_res,
            "Bandit": bandit_res,
            "Oracle-22": oracle_res,
        })

        print(f"  Test Discovery: RL={rl_res['success_rate_pct']:.2f}%, StaticTop5={top5_res['success_rate_pct']:.2f}%, Random={rand_res['success_rate_pct']:.2f}%")

    # Aggregate & Summarize Table 1
    methods = ["Random-5", "Static-Top5", "Bandit", "RL", "Oracle-22"]
    summary_rows = []

    for m in methods:
        success_rates = [run[m]["success_rate_pct"] for run in all_runs]
        median_steps = [run[m]["median_steps_to_flip"] for run in all_runs]
        calls_per_claim = [run[m]["calls_per_claim"] for run in all_runs]

        # Cost reduction vs Oracle (22 calls)
        mean_calls = np.mean(calls_per_claim)
        reduction_pct = ((22.0 - mean_calls) / 22.0) * 100

        summary_rows.append({
            "Method": m,
            "Budget (K)": 22 if m == "Oracle-22" else 5,
            "Claims with >=1 Flip (%)": f"{np.mean(success_rates):.2f} ± {np.std(success_rates):.2f}",
            "Median Steps to Flip": f"{np.mean(median_steps):.2f}",
            "API Calls / Claim": f"{mean_calls:.2f}",
            "Cost Reduction (%)": f"{reduction_pct:.2f}%",
        })

    summary_df = pd.DataFrame(summary_rows)
    print("\n" + "=" * 80)
    print("TABLE 1: RL ATTACK SELECTION EFFICIENCY & BASELINE COMPARISON (5 SEEDS)")
    print("=" * 80)
    print(summary_df.to_string(index=False))

    # Save outputs
    out_table_path = os.path.join(args.output_dir, "table1_rl_efficiency.csv")
    summary_df.to_csv(out_table_path, index=False)

    out_metrics_path = os.path.join(args.output_dir, "rl_5seed_runs.json")
    with open(out_metrics_path, "w", encoding="utf-8") as f:
        json.dump(all_runs, f, indent=2)

    print(f"\nSaved Table 1 to {out_table_path}")
    print(f"Saved complete 5-seed run data to {out_metrics_path}")


if __name__ == "__main__":
    main()
