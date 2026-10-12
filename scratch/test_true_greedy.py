import sys, os
sys.path.insert(0, r"e:\Attack\Attack")
import numpy as np
from replay_env import OfflineAttackEnv, ATTACK_KEYS_22
from rl.train_selector import split_claims

env = OfflineAttackEnv(base_dir=r"e:\Attack\Attack", max_budget_k=5, exclude_baseline_failures=True)
all_claims = env.valid_claim_ids
seeds = [42, 43, 44, 45, 46]

# Blind spots
top5_indices = [env.attack_to_idx[k] for k in [
    "EA_CTXREP_01_ContextualizedReplace", "EA_ADVADD_01_AdvAdd", 
    "EA_FACT2FICT_01_Fact2Fiction", "CA_06_FactMixing", "EA_CLAIMREWRITE_01_ClaimRewrite"
]]
blind_spots = [cid for cid in all_claims if not any(env.outcomes[cid, idx, 0] > 0 for idx in top5_indices) and any(env.outcomes[cid, idx, 0] > 0 for idx in range(env.num_attacks))]

greedy_test_scores = []
greedy_bs_recalls = []

print("=== TRUE PER-FOLD GREEDY COVERAGE ON TRAIN SPLIT ===")
for s in seeds:
    train_ids, val_ids, test_ids = split_claims(all_claims, seed=s)
    
    # Compute greedy coverage on train split
    greedy_covered = set()
    greedy_arm_indices = []
    available_attacks = list(range(env.num_attacks))
    for step in range(5):
        best_arm = None
        best_gain = -1
        for a in available_attacks:
            gain = sum(1 for cid in train_ids if cid not in greedy_covered and env.outcomes[cid, a, 0] > 0)
            if gain > best_gain:
                best_gain = gain
                best_arm = a
        greedy_arm_indices.append(best_arm)
        available_attacks.remove(best_arm)
        for cid in train_ids:
            if env.outcomes[cid, best_arm, 0] > 0:
                greedy_covered.add(cid)
    
    arm_names = [env.idx_to_attack[a].split('_')[1] if '_' in env.idx_to_attack[a] else env.idx_to_attack[a] for a in greedy_arm_indices]
    
    # Evaluate on test split
    test_flips = sum(1 for cid in test_ids if any(env.outcomes[cid, a, 0] > 0 for a in greedy_arm_indices))
    test_rate = test_flips / len(test_ids) * 100
    greedy_test_scores.append(test_rate)
    
    # Evaluate on blind spots in test split
    bs_in_test = [cid for cid in test_ids if cid in blind_spots]
    bs_flips = sum(1 for cid in bs_in_test if any(env.outcomes[cid, a, 0] > 0 for a in greedy_arm_indices))
    greedy_bs_recalls.append((bs_flips, len(bs_in_test)))
    
    print(f"Seed {s}:")
    print(f"  Greedy arms: {arm_names}")
    print(f"  Test Score: {test_flips}/{len(test_ids)} = {test_rate:.2f}%")
    print(f"  Blind spot recall: {bs_flips}/{len(bs_in_test)}")

print(f"\nMean Greedy Test Score: {np.mean(greedy_test_scores):.2f}% +/- {np.std(greedy_test_scores, ddof=1):.2f}%")
total_bs_flips = sum(x[0] for x in greedy_bs_recalls)
total_bs_opps = sum(x[1] for x in greedy_bs_recalls)
print(f"Total blind spot recall for Greedy: {total_bs_flips} / {total_bs_opps} ({total_bs_flips/total_bs_opps*100:.2f}%)")
