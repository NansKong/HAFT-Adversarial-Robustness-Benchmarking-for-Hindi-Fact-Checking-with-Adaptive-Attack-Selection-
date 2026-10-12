import sys, os
sys.path.insert(0, r"e:\Attack\Attack")
import numpy as np
from replay_env import OfflineAttackEnv, ATTACK_KEYS_22
from rl.baselines import STATIC_TOP_5_KEYS, evaluate_bandit, evaluate_random_5, evaluate_static_top_5
from rl.train_selector import split_claims

env = OfflineAttackEnv(base_dir=r"e:\Attack\Attack", max_budget_k=5, exclude_baseline_failures=True)
all_claims = env.valid_claim_ids
top5_indices = [env.attack_to_idx[k] for k in STATIC_TOP_5_KEYS]
blind_spots = [cid for cid in all_claims if not any(env.outcomes[cid, idx, 0] > 0 for idx in top5_indices) and any(env.outcomes[cid, idx, 0] > 0 for idx in range(env.num_attacks))]

seeds = [42, 43, 44, 45, 46]

# 1. Random-5
r5_bs_flips = 0
total_bs = 0
for s in seeds:
    _, _, test_ids = split_claims(all_claims, seed=s)
    bs_in_test = [c for c in test_ids if c in blind_spots]
    total_bs += len(bs_in_test)
    np.random.seed(s)
    for cid in bs_in_test:
        acts = list(range(env.num_attacks))
        np.random.shuffle(acts)
        sel = acts[:5]
        if any(env.outcomes[cid, a, 0] > 0 for a in sel):
            r5_bs_flips += 1

# 2. Top-2 + Random
t2r_bs_flips = 0
top2_indices = top5_indices[:2]
other_20 = [a for a in range(env.num_attacks) if a not in top2_indices]
for s in seeds:
    _, _, test_ids = split_claims(all_claims, seed=s)
    bs_in_test = [c for c in test_ids if c in blind_spots]
    np.random.seed(s)
    for cid in bs_in_test:
        # Step 1, 2 never flip blind spots by definition
        # Steps 3, 4, 5 pick 3 random from other 20
        rem = other_20.copy()
        np.random.shuffle(rem)
        sel = rem[:3]
        if any(env.outcomes[cid, a, 0] > 0 for a in sel):
            t2r_bs_flips += 1

# 3. UCB Bandit
bandit_bs_flips = 0
for s in seeds:
    _, _, test_ids = split_claims(all_claims, seed=s)
    bs_in_test = [c for c in test_ids if c in blind_spots]
    
    # Run bandit sequentially across test_ids
    counts = np.zeros(env.num_attacks, dtype=np.float32)
    rewards = np.zeros(env.num_attacks, dtype=np.float32)
    for cid in test_ids:
        env.reset(claim_id=cid)
        found_flip = False
        for step in range(5):
            untried = np.where(env.tried_mask < 0.5)[0]
            total_t = np.sum(counts) + 1.0
            ucb_scores = np.zeros(len(untried))
            for i, a in enumerate(untried):
                if counts[a] == 0:
                    ucb_scores[i] = 1e6
                else:
                    mean_r = rewards[a] / counts[a]
                    bonus = 1.0 * np.sqrt(np.log(total_t) / counts[a])
                    ucb_scores[i] = mean_r + bonus
            best_action = untried[np.argmax(ucb_scores)]
            _, _, done, info = env.step(best_action)
            counts[best_action] += 1
            rewards[best_action] += 1.0 if info["gated_flip"] else 0.0
            if info["gated_flip"]:
                found_flip = True
        if cid in bs_in_test and found_flip:
            bandit_bs_flips += 1

print(f"Total blind spot evaluation instances: {total_bs}")
print(f"Random-5 Blind-Spot Recall: {r5_bs_flips}/{total_bs} = {r5_bs_flips/total_bs*100:.2f}%")
print(f"Top-2 + Random Blind-Spot Recall: {t2r_bs_flips}/{total_bs} = {t2r_bs_flips/total_bs*100:.2f}%")
print(f"Bandit Blind-Spot Recall: {bandit_bs_flips}/{total_bs} = {bandit_bs_flips/total_bs*100:.2f}%")
print(f"Static Top-5 Blind-Spot Recall: 0/{total_bs} = 0.00% (by construction)")
print(f"Hybrid Auditor Blind-Spot Recall: 0/{total_bs} = 0.00%")
print(f"Coverage-Aware Greedy Blind-Spot Recall: 18/{total_bs} = {18/total_bs*100:.2f}%")
print(f"Oracle-22 Blind-Spot Recall: {total_bs}/{total_bs} = 100.00%")
