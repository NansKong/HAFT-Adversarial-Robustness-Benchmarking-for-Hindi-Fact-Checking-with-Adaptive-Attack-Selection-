import sys, os
sys.path.insert(0, r"e:\Attack\Attack")
import numpy as np
from replay_env import OfflineAttackEnv
from rl.baselines import STATIC_TOP_5_KEYS
from rl.train_selector import split_claims

env = OfflineAttackEnv(base_dir=r"e:\Attack\Attack", max_budget_k=5, exclude_baseline_failures=True)
all_claims = env.valid_claim_ids
seeds = [42, 43, 44, 45, 46]

top5_idx = [env.attack_to_idx[k] for k in STATIC_TOP_5_KEYS]

# Static Top-5 queries:
# For each claim in test split:
# step through top 5 until flip or 5 steps.
top5_queries_per_split = []
for s in seeds:
    _, _, test_ids = split_claims(all_claims, seed=s)
    queries = []
    for cid in test_ids:
        q = 0
        flipped = False
        for a in top5_idx:
            q += 1
            if env.outcomes[cid, a, 0] > 0:
                flipped = True
                break
        queries.append(q)
    top5_queries_per_split.append(np.mean(queries))

print(f"Static Top-5 mean queries per claim across splits: {np.mean(top5_queries_per_split):.2f}")
