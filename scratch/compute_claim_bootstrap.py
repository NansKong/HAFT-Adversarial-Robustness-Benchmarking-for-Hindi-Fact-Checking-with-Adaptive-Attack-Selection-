import sys, os
sys.path.insert(0, r"e:\Attack\Attack")
import numpy as np
from replay_env import OfflineAttackEnv, ATTACK_KEYS_22
from rl.baselines import STATIC_TOP_5_KEYS

env = OfflineAttackEnv(base_dir=r"e:\Attack\Attack", max_budget_k=5, exclude_baseline_failures=True)
all_claims = env.valid_claim_ids # 832 claims
N = len(all_claims)

# Precompute per-claim outcomes under policies
# 1. Static Top-5 on each claim:
top5_indices = [env.attack_to_idx[k] for k in STATIC_TOP_5_KEYS]
top5_flipped = np.array([any(env.outcomes[cid, idx, 0] > 0 for idx in top5_indices) for cid in all_claims], dtype=float)

# 2. Top-2 + Random:
# On any claim, Top-2 flips it if either of top 2 flips it.
# If not, it has probability of being flipped by 3 random picks from the remaining 20 attacks.
top2_indices = top5_indices[:2]
top2_flipped = np.array([any(env.outcomes[cid, idx, 0] > 0 for idx in top2_indices) for cid in all_claims], dtype=float)
other_20_indices = [idx for idx in range(env.num_attacks) if idx not in top2_indices]

# For each claim, how many of the other 20 attacks flip it?
k_other_flips = np.array([sum(1 for idx in other_20_indices if env.outcomes[cid, idx, 0] > 0) for cid in all_claims])
# Prob of >=1 flip in 3 hypergeometric draws from 20 without replacement:
# P = 1 - binom(20 - k, 3) / binom(20, 3)
from scipy.special import comb
prob_random_flip = np.zeros(N)
for i in range(N):
    if top2_flipped[i] > 0:
        prob_random_flip[i] = 1.0
    else:
        k = k_other_flips[i]
        prob_random_flip[i] = 1.0 - comb(20 - k, 3) / comb(20, 3)

# 3. Hybrid Auditor:
# Let's load the actual hybrid evaluations across seeds or compute empirical per-claim flip rates
# Let's run a bootstrap of 10,000 resamples of the 832 claims
rng = np.random.RandomState(42)
boot_diffs_top5_vs_top2rand = []

for _ in range(10000):
    sample_idx = rng.choice(N, size=N, replace=True)
    mean_top5 = np.mean(top5_flipped[sample_idx]) * 100
    mean_top2rand = np.mean(prob_random_flip[sample_idx]) * 100
    boot_diffs_top5_vs_top2rand.append(mean_top5 - mean_top2rand)

ci_lower = np.percentile(boot_diffs_top5_vs_top2rand, 2.5)
ci_upper = np.percentile(boot_diffs_top5_vs_top2rand, 97.5)
print(f"Top-5 vs Top-2+Random Claim-level Bootstrap: +{np.mean(boot_diffs_top5_vs_top2rand):.2f} pp, 95% CI [{ci_lower:.2f}, {ci_upper:.2f}] pp")
