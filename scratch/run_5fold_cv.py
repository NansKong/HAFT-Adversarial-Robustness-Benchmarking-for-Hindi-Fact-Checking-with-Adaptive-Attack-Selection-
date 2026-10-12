import sys, os
sys.path.insert(0, r"e:\Attack\Attack")
import numpy as np
from replay_env import OfflineAttackEnv, ATTACK_KEYS_22
from rl.baselines import STATIC_TOP_5_KEYS, evaluate_static_top_5

env = OfflineAttackEnv(base_dir=r"e:\Attack\Attack", max_budget_k=5, exclude_baseline_failures=True)
all_claims = env.valid_claim_ids # 832 claims

top5_indices = [env.attack_to_idx[k] for k in STATIC_TOP_5_KEYS]
blind_spots = [cid for cid in all_claims if not any(env.outcomes[cid, idx, 0] > 0 for idx in top5_indices) and any(env.outcomes[cid, idx, 0] > 0 for idx in range(env.num_attacks))]
print(f"Total blind spot claims in 832: {len(blind_spots)}")

# In a true 5-fold CV:
# Divide 832 claims into 5 disjoint folds: 167, 167, 166, 166, 166 claims
rng = np.random.RandomState(42)
shuffled = all_claims.copy()
rng.shuffle(shuffled)
folds = np.array_split(shuffled, 5)

for i, fold in enumerate(folds):
    flips = evaluate_static_top_5(env, fold)
    bs_in_fold = [c for c in fold if c in blind_spots]
    print(f"Fold {i+1}: N={len(fold)}, Static Top-5 Flips={flips['claims_with_flip']} ({flips['success_rate_pct']:.2f}%), Blind spots={len(bs_in_fold)}")

total_static_flips = sum(evaluate_static_top_5(env, f)['claims_with_flip'] for f in folds)
print(f"Total across all 5 folds: {total_static_flips} / 832 = {total_static_flips/832*100:.2f}%")
