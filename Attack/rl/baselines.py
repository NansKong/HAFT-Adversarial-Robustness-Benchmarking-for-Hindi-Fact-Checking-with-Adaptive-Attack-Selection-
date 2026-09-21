"""HAFT Stage 2 — Baseline Attack Selection Policies

Baseline 1: Random-5 (Randomly selects 5 unique untried attacks)
Baseline 2: Static Global Top-5 (Selects the 5 globally highest-ASR attacks)
Baseline 3: Claim-Agnostic Bandit (UCB-based global attack selection)
Baseline 4: Oracle-22 (Exhaustive reference evaluating all 22 attacks)
"""

from __future__ import annotations
from typing import List, Dict, Any, Tuple
import numpy as np
from replay_env import OfflineAttackEnv, ATTACK_KEYS_22

# Top 5 attacks sorted by global Phase A Gated ASR
STATIC_TOP_5_KEYS = [
    "EA_CTXREP_01_ContextualizedReplace",  # 59.57%
    "EA_ADVADD_01_AdvAdd",                 # 58.47%
    "EA_FACT2FICT_01_Fact2Fiction",        # 57.60%
    "CA_06_FactMixing",                    # 55.81%
    "EA_CLAIMREWRITE_01_ClaimRewrite",     # 25.39%
]


def evaluate_random_5(env: OfflineAttackEnv, claim_ids: List[int], seed: int = 42) -> Dict[str, Any]:
    """Evaluate Random-5 baseline: selects 5 random unique attacks per claim."""
    np.random.seed(seed)
    flips_discovered = []
    steps_to_first_flip = []
    total_calls = 0

    for cid in claim_ids:
        env.reset(claim_id=cid)
        available_attacks = list(range(env.num_attacks))
        np.random.shuffle(available_attacks)
        selected_5 = available_attacks[:env.max_budget_k]

        found_flip = False
        steps = 0
        for step_idx, action in enumerate(selected_5):
            steps += 1
            total_calls += 1
            _, _, done, info = env.step(action)
            if info["gated_flip"] and not found_flip:
                found_flip = True
                steps_to_first_flip.append(step_idx + 1)

        flips_discovered.append(1 if found_flip else 0)

    success_rate = float(np.mean(flips_discovered) * 100)
    median_steps = float(np.median(steps_to_first_flip)) if steps_to_first_flip else 0.0
    mean_steps = float(np.mean(steps_to_first_flip)) if steps_to_first_flip else 0.0

    return {
        "method": "Random-5",
        "budget": env.max_budget_k,
        "success_rate_pct": success_rate,
        "total_claims": len(claim_ids),
        "claims_with_flip": int(sum(flips_discovered)),
        "median_steps_to_flip": median_steps,
        "mean_steps_to_flip": mean_steps,
        "total_api_calls": total_calls,
        "calls_per_claim": total_calls / max(1, len(claim_ids)),
    }


def evaluate_static_top_5(env: OfflineAttackEnv, claim_ids: List[int]) -> Dict[str, Any]:
    """Evaluate Static Global Top-5 baseline."""
    top5_indices = [env.attack_to_idx[k] for k in STATIC_TOP_5_KEYS]
    flips_discovered = []
    steps_to_first_flip = []
    total_calls = 0

    for cid in claim_ids:
        env.reset(claim_id=cid)
        found_flip = False
        for step_idx, action in enumerate(top5_indices):
            total_calls += 1
            _, _, done, info = env.step(action)
            if info["gated_flip"] and not found_flip:
                found_flip = True
                steps_to_first_flip.append(step_idx + 1)

        flips_discovered.append(1 if found_flip else 0)

    success_rate = float(np.mean(flips_discovered) * 100)
    median_steps = float(np.median(steps_to_first_flip)) if steps_to_first_flip else 0.0
    mean_steps = float(np.mean(steps_to_first_flip)) if steps_to_first_flip else 0.0

    return {
        "method": "Static Top-5",
        "budget": env.max_budget_k,
        "success_rate_pct": success_rate,
        "total_claims": len(claim_ids),
        "claims_with_flip": int(sum(flips_discovered)),
        "median_steps_to_flip": median_steps,
        "mean_steps_to_flip": mean_steps,
        "total_api_calls": total_calls,
        "calls_per_claim": total_calls / max(1, len(claim_ids)),
    }


def evaluate_bandit(env: OfflineAttackEnv, claim_ids: List[int], exploration_c: float = 1.0) -> Dict[str, Any]:
    """Evaluate Claim-Agnostic UCB Bandit baseline."""
    counts = np.zeros(env.num_attacks, dtype=np.float32)
    rewards = np.zeros(env.num_attacks, dtype=np.float32)

    flips_discovered = []
    steps_to_first_flip = []
    total_calls = 0

    for cid in claim_ids:
        env.reset(claim_id=cid)
        found_flip = False

        for step in range(env.max_budget_k):
            # Compute UCB scores for untried attacks in this episode
            untried = np.where(env.tried_mask < 0.5)[0]
            total_t = np.sum(counts) + 1.0

            ucb_scores = np.zeros(len(untried))
            for i, a in enumerate(untried):
                if counts[a] == 0:
                    ucb_scores[i] = 1e6  # Force initial exploration
                else:
                    mean_r = rewards[a] / counts[a]
                    bonus = exploration_c * np.sqrt(np.log(total_t) / counts[a])
                    ucb_scores[i] = mean_r + bonus

            best_action = untried[np.argmax(ucb_scores)]
            total_calls += 1

            _, step_reward, done, info = env.step(best_action)
            counts[best_action] += 1
            rewards[best_action] += 1.0 if info["gated_flip"] else 0.0

            if info["gated_flip"] and not found_flip:
                found_flip = True
                steps_to_first_flip.append(step + 1)

        flips_discovered.append(1 if found_flip else 0)

    success_rate = float(np.mean(flips_discovered) * 100)
    median_steps = float(np.median(steps_to_first_flip)) if steps_to_first_flip else 0.0
    mean_steps = float(np.mean(steps_to_first_flip)) if steps_to_first_flip else 0.0

    return {
        "method": "Bandit (UCB)",
        "budget": env.max_budget_k,
        "success_rate_pct": success_rate,
        "total_claims": len(claim_ids),
        "claims_with_flip": int(sum(flips_discovered)),
        "median_steps_to_flip": median_steps,
        "mean_steps_to_flip": mean_steps,
        "total_api_calls": total_calls,
        "calls_per_claim": total_calls / max(1, len(claim_ids)),
    }


def evaluate_oracle_22(env: OfflineAttackEnv, claim_ids: List[int]) -> Dict[str, Any]:
    """Evaluate Oracle-22 (Exhaustive Reference testing all 22 attacks)."""
    flips_discovered = []
    steps_to_first_flip = []
    total_calls = 0

    for cid in claim_ids:
        # Check ground truth outcomes across all 22 attacks
        # outcomes shape: (1120, 22, 3) -> [0] is gated_flip
        claim_flips = env.outcomes[cid, :, 0] > 0.5
        has_any_flip = np.any(claim_flips)
        flips_discovered.append(1 if has_any_flip else 0)
        total_calls += 22

        if has_any_flip:
            first_idx = int(np.where(claim_flips)[0][0]) + 1
            steps_to_first_flip.append(first_idx)

    success_rate = float(np.mean(flips_discovered) * 100)
    median_steps = float(np.median(steps_to_first_flip)) if steps_to_first_flip else 0.0
    mean_steps = float(np.mean(steps_to_first_flip)) if steps_to_first_flip else 0.0

    return {
        "method": "Oracle-22 (Exhaustive)",
        "budget": 22,
        "success_rate_pct": success_rate,
        "total_claims": len(claim_ids),
        "claims_with_flip": int(sum(flips_discovered)),
        "median_steps_to_flip": median_steps,
        "mean_steps_to_flip": mean_steps,
        "total_api_calls": total_calls,
        "calls_per_claim": 22.0,
    }
