import sys, os
sys.path.insert(0, r"e:\Attack\Attack")
import numpy as np
import torch
from replay_env import OfflineAttackEnv, ATTACK_KEYS_22
from rl.train_selector import split_claims
from rl.baselines import STATIC_TOP_5_KEYS

env = OfflineAttackEnv(base_dir=r"e:\Attack\Attack", max_budget_k=5, exclude_baseline_failures=True)
all_claims = env.valid_claim_ids
seeds = [42, 43, 44, 45, 46]

# For each baseline, compute discovery@k for k=1..5 and mean queries per claim
# Let's inspect Static Top-5, Top-2 + Random, Random-5
top5_indices = [env.attack_to_idx[k] for k in STATIC_TOP_5_KEYS]
top2_indices = top5_indices[:2]

def eval_policy_discovery_at_k(policy_type="static_top5", seed=42):
    train_ids, val_ids, test_ids = split_claims(all_claims, seed=seed)
    # k = 1..5 cumulative flips
    k_flips = {k: 0 for k in range(1, 6)}
    queries = []
    
    if policy_type == "static_top5":
        for cid in test_ids:
            found_step = None
            for step, act in enumerate(top5_indices, 1):
                if env.outcomes[cid, act, 0] > 0:
                    found_step = step
                    break
            queries.append(found_step if found_step else 5)
            for k in range(1, 6):
                if found_step and found_step <= k:
                    k_flips[k] += 1
    elif policy_type == "random5":
        np.random.seed(seed)
        for cid in test_ids:
            acts = list(range(env.num_attacks))
            np.random.shuffle(acts)
            sel = acts[:5]
            found_step = None
            for step, act in enumerate(sel, 1):
                if env.outcomes[cid, act, 0] > 0:
                    found_step = step
                    break
            queries.append(found_step if found_step else 5)
            for k in range(1, 6):
                if found_step and found_step <= k:
                    k_flips[k] += 1
    elif policy_type == "top2_random":
        np.random.seed(seed)
        for cid in test_ids:
            found_step = None
            # Step 1, 2
            for step, act in enumerate(top2_indices, 1):
                if env.outcomes[cid, act, 0] > 0:
                    found_step = step
                    break
            if not found_step:
                rem = [a for a in range(env.num_attacks) if a not in top2_indices]
                np.random.shuffle(rem)
                for step, act in enumerate(rem[:3], 3):
                    if env.outcomes[cid, act, 0] > 0:
                        found_step = step
                        break
            queries.append(found_step if found_step else 5)
            for k in range(1, 6):
                if found_step and found_step <= k:
                    k_flips[k] += 1
                    
    rates = {k: v / len(test_ids) * 100 for k, v in k_flips.items()}
    return rates, np.mean(queries)

print("=== DISCOVERY @ K (K=1..5) & MEAN QUERIES PER CLAIM ===")
for pol in ["random5", "top2_random", "static_top5"]:
    all_k = {k: [] for k in range(1, 6)}
    all_q = []
    for s in seeds:
        rates, q = eval_policy_discovery_at_k(pol, s)
        for k in range(1, 6):
            all_k[k].append(rates[k])
        all_q.append(q)
    print(f"\nPolicy: {pol}")
    for k in range(1, 6):
        print(f"  @K={k}: {np.mean(all_k[k]):.2f}% +/- {np.std(all_k[k], ddof=1):.2f}%")
    print(f"  Mean queries/claim: {np.mean(all_q):.2f} +/- {np.std(all_q, ddof=1):.2f}")
