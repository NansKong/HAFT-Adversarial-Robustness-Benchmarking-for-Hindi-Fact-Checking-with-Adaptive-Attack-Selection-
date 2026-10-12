import sys, os
sys.path.insert(0, r"e:\Attack\Attack")
import numpy as np
import pandas as pd
from replay_env import OfflineAttackEnv, ATTACK_KEYS_22
from rl.baselines import STATIC_TOP_5_KEYS, evaluate_static_top_5
from rl.train_selector import split_claims

env = OfflineAttackEnv(base_dir=r"e:\Attack\Attack", max_budget_k=5, exclude_baseline_failures=True)
all_claims = env.valid_claim_ids # 832 claims
print(f"Total valid clean-baseline claims: {len(all_claims)}")

# Identify the 34 blind spots
top5_indices = [env.attack_to_idx[k] for k in STATIC_TOP_5_KEYS]
blind_spots = []
for cid in all_claims:
    # check if flipped by any of top 5
    top5_flip = any(env.outcomes[cid, idx, 0] > 0 for idx in top5_indices)
    any_flip = any(env.outcomes[cid, idx, 0] > 0 for idx in range(env.num_attacks))
    if not top5_flip and any_flip:
        blind_spots.append(cid)
print(f"Total blind spot claims (immune to global top-5, flipped by another attack): {len(blind_spots)}")

seeds = [42, 43, 44, 45, 46]
print("\n" + "="*80)
print("PER-SEED TRAIN/VAL/TEST ANALYSIS")
print("="*80)

test_rates = []
val_rates = []
train_rates = []

for s in seeds:
    train_ids, val_ids, test_ids = split_claims(all_claims, seed=s)
    
    # 1. Train ASR ranking
    train_asrs = {}
    for k in ATTACK_KEYS_22:
        idx = env.attack_to_idx[k]
        flips = sum(1 for cid in train_ids if env.outcomes[cid, idx, 0] > 0)
        train_asrs[k] = flips / len(train_ids)
    
    sorted_by_asr = sorted(train_asrs.items(), key=lambda x: x[1], reverse=True)
    top5_by_asr = [k for k, v in sorted_by_asr[:5]]
    
    # 2. Greedy coverage ranking on train fold
    # Greedy picks arm that flips the most currently un-flipped claims
    greedy_covered = set()
    greedy_arms = []
    available_attacks = list(range(env.num_attacks))
    for _ in range(5):
        best_arm = None
        best_gain = -1
        for a in available_attacks:
            gain = sum(1 for cid in train_ids if cid not in greedy_covered and env.outcomes[cid, a, 0] > 0)
            if gain > best_gain:
                best_gain = gain
                best_arm = a
        greedy_arms.append(env.idx_to_attack[best_arm])
        available_attacks.remove(best_arm)
        for cid in train_ids:
            if env.outcomes[cid, best_arm, 0] > 0:
                greedy_covered.add(cid)
                
    # Evaluate global static top-5 on test, val, train
    res_test = evaluate_static_top_5(env, test_ids)
    res_val = evaluate_static_top_5(env, val_ids)
    res_train = evaluate_static_top_5(env, train_ids)
    
    test_rates.append(res_test["success_rate_pct"])
    val_rates.append(res_val["success_rate_pct"])
    train_rates.append(res_train["success_rate_pct"])
    
    # Check blind spots in this test split
    bs_in_test = [cid for cid in test_ids if cid in blind_spots]
    
    print(f"\nSeed {s}:")
    print(f"  Test N={len(test_ids)}:  {res_test['claims_with_flip']} flips ({res_test['success_rate_pct']:.2f}%)")
    print(f"  Val  N={len(val_ids)}:  {res_val['claims_with_flip']} flips ({res_val['success_rate_pct']:.2f}%)")
    print(f"  Train N={len(train_ids)}: {res_train['claims_with_flip']} flips ({res_train['success_rate_pct']:.2f}%)")
    print(f"  Top-5 by Train ASR: {top5_by_asr == STATIC_TOP_5_KEYS}")
    if top5_by_asr != STATIC_TOP_5_KEYS:
        print(f"    Train ASR top-5: {[k.split('_')[1] for k in top5_by_asr]}")
    print(f"  Greedy Coverage Top-5 on Train: {[k.split('_')[1] for k in greedy_arms]}")
    print(f"  Blind spots in Test split: {len(bs_in_test)} claims: {bs_in_test}")
    # Flips by global static top-5 on blind spots in test split:
    bs_flips_static = sum(1 for cid in bs_in_test if any(env.outcomes[cid, idx, 0] > 0 for idx in top5_indices))
    print(f"  STATIC_TOP_5 flips on test blind spots: {bs_flips_static} / {len(bs_in_test)}")

print("\n" + "="*80)
print(f"Test split rates: {test_rates}")
print(f"Mean Test:  {np.mean(test_rates):.4f}% +/- {np.std(test_rates, ddof=1):.4f}% (sample SD), +/- {np.std(test_rates):.4f}% (pop SD)")
print(f"Val split rates:  {val_rates}")
print(f"Mean Val:   {np.mean(val_rates):.4f}% +/- {np.std(val_rates, ddof=1):.4f}%")
print(f"Train split rates: {train_rates}")
print(f"Mean Train: {np.mean(train_rates):.4f}% +/- {np.std(train_rates, ddof=1):.4f}%")
print(f"Full corpus (all 832): 704 / 832 = {704/832*100:.4f}%")
