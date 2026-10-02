"""HAFT Stage 2 — Hybrid Warm-Start Auditor

Combines the strong empirical prior of top evidence attacks with adaptive
reinforcement learning exploration for resilient claims:
  - Step 1: Probe EA_CTXREP_01_ContextualizedReplace (Global Top-1, 59.57% ASR)
  - Step 2: Probe EA_ADVADD_01_AdvAdd (Global Top-2, 58.47% ASR)
  - Steps 3-5: If un-flipped, hand over to the trained REINFORCE policy
    to dynamically probe linguistic, syntactic, and structural perturbations.
"""

from __future__ import annotations
import os
import sys
from typing import Dict, List, Any, Tuple
import numpy as np
import torch

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from replay_env import OfflineAttackEnv, ATTACK_KEYS_22
from rl.reinforce import REINFORCEAgent
from rl.train_selector import split_claims, train_rl_agent, evaluate_rl_agent
from rl.baselines import evaluate_static_top_5, evaluate_random_5, evaluate_bandit, evaluate_oracle_22

WARM_START_TOP_2_KEYS = [
    "EA_CTXREP_01_ContextualizedReplace",
    "EA_ADVADD_01_AdvAdd",
]


def evaluate_hybrid_auditor(
    env: OfflineAttackEnv,
    agent: REINFORCEAgent,
    claim_ids: np.ndarray,
    warm_start_steps: int = 2,
) -> Dict[str, Any]:
    """Evaluate Hybrid Warm-Start Auditor on test claims."""
    flips_discovered = []
    steps_to_first_flip = []
    action_counts = np.zeros(env.num_attacks, dtype=int)
    total_calls = 0
    rescued_by_rl = 0

    top2_indices = [env.attack_to_idx[k] for k in WARM_START_TOP_2_KEYS[:warm_start_steps]]

    for cid in claim_ids:
        state = env.reset(claim_id=int(cid))
        done = False
        found_flip = False
        first_step = None

        # Step 1 & 2: Static Warm-Start Anchors
        for step_idx, warm_action in enumerate(top2_indices):
            next_state, reward, done, info = env.step(warm_action)
            action_counts[warm_action] += 1
            total_calls += 1

            if info["gated_flip"] and not found_flip:
                found_flip = True
                first_step = step_idx + 1
                steps_to_first_flip.append(first_step)

            state = next_state
            if done:
                break

        # Steps 3-5: Adaptive RL handover if still not flipped
        while not done:
            action, _, probs = agent.select_action(state, env.tried_mask, epsilon=0.0)
            next_state, reward, done, info = env.step(action)
            action_counts[action] += 1
            total_calls += 1

            if info["gated_flip"]:
                if not found_flip:
                    found_flip = True
                    first_step = info["step"]
                    steps_to_first_flip.append(first_step)
                    rescued_by_rl += 1

            state = next_state

        flips_discovered.append(1 if found_flip else 0)

    success_rate = float(np.mean(flips_discovered) * 100)
    median_steps = float(np.median(steps_to_first_flip)) if steps_to_first_flip else 0.0
    mean_steps = float(np.mean(steps_to_first_flip)) if steps_to_first_flip else 0.0

    return {
        "method": "Hybrid Warm-Start Auditor (Ours)",
        "budget": env.max_budget_k,
        "success_rate_pct": success_rate,
        "total_claims": len(claim_ids),
        "claims_with_flip": int(sum(flips_discovered)),
        "median_steps_to_flip": median_steps,
        "mean_steps_to_flip": mean_steps,
        "total_api_calls": total_calls,
        "calls_per_claim": total_calls / max(1, len(claim_ids)),
        "rescued_by_rl": rescued_by_rl,
        "action_distribution": action_counts.tolist(),
    }


def run_benchmark(seeds: List[int] = [42, 43, 44, 45, 46], epochs: int = 20):
    emb_path = os.path.join(BASE_DIR, "data", "claim_embeddings_indicbert_1120.pt")
    embeddings = torch.load(emb_path, weights_only=True) if os.path.exists(emb_path) else None

    env = OfflineAttackEnv(
        base_dir=BASE_DIR,
        max_budget_k=5,
        claim_embeddings=embeddings,
        exclude_baseline_failures=True,
    )
    all_claims = env.valid_claim_ids

    results = {
        "Random-5": [],
        "Bandit-UCB": [],
        "Static-Top5": [],
        "Pure-RL": [],
        "Hybrid-Auditor": [],
        "Oracle-22": [],
    }
    rescues = []

    print("=" * 85, flush=True)
    print("HAFT MULTI-SEED POLICY BENCHMARK (5 SEEDS, K <= 5)", flush=True)
    print("=" * 85, flush=True)

    for seed in seeds:
        train_ids, val_ids, test_ids = split_claims(all_claims, seed=seed)

        # Train pure RL agent
        agent, _ = train_rl_agent(env, train_ids, val_ids, epochs=epochs, epsilon=0.10, seed=seed)

        # Evaluate baselines and policies
        res_rand = evaluate_random_5(env, list(test_ids), seed=seed)
        res_band = evaluate_bandit(env, list(test_ids))
        res_stat = evaluate_static_top_5(env, list(test_ids))
        res_rl = evaluate_rl_agent(env, agent, test_ids)
        res_hyb = evaluate_hybrid_auditor(env, agent, test_ids, warm_start_steps=2)
        res_orc = evaluate_oracle_22(env, list(test_ids))

        results["Random-5"].append(res_rand["success_rate_pct"])
        results["Bandit-UCB"].append(res_band["success_rate_pct"])
        results["Static-Top5"].append(res_stat["success_rate_pct"])
        results["Pure-RL"].append(res_rl["success_rate_pct"])
        results["Hybrid-Auditor"].append(res_hyb["success_rate_pct"])
        results["Oracle-22"].append(res_orc["success_rate_pct"])
        rescues.append(res_hyb["rescued_by_rl"])

        print(f"Seed {seed:2d} -> Static: {res_stat['success_rate_pct']:.2f}% | "
              f"Pure-RL: {res_rl['success_rate_pct']:.2f}% | "
              f"Hybrid (Ours): {res_hyb['success_rate_pct']:.2f}% (Rescued: {res_hyb['rescued_by_rl']} claims)", flush=True)

    print("\n" + "=" * 85, flush=True)
    print("AGGREGATE BENCHMARK RESULTS (Mean ± SD across 5 Seeds)", flush=True)
    print("=" * 85, flush=True)
    for m, vals in results.items():
        mean_val = np.mean(vals)
        std_val = np.std(vals)
        print(f"{m:<28}: {mean_val:6.2f}% ± {std_val:4.2f}%", flush=True)
    print(f"Total RL-Rescued Claims Across Seeds: {sum(rescues)} (Avg {np.mean(rescues):.1f} per test split)", flush=True)
    print("=" * 85, flush=True)


if __name__ == "__main__":
    run_benchmark(epochs=15)
