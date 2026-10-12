import sys, os
sys.path.insert(0, r"e:\Attack\Attack")
import numpy as np
from replay_env import OfflineAttackEnv, ATTACK_KEYS_22
from rl.baselines import STATIC_TOP_5_KEYS
from scipy.stats import fisher_exact

env = OfflineAttackEnv(base_dir=r"e:\Attack\Attack", max_budget_k=5, exclude_baseline_failures=True)
all_claims = env.valid_claim_ids

top5_indices = [env.attack_to_idx[k] for k in STATIC_TOP_5_KEYS]
jumbling_idx = env.attack_to_idx["CA_WORD_03_Jumbling"]
omission_idx = env.attack_to_idx["EA_OMITOMISSION_01_OmissionGeneration"]

# Categorize the 34 blind spot claims:
all_34 = []
ex_jumbling_20 = []
pure_surface_15 = []
strictly_surface_10 = []

surface_indices = [
    env.attack_to_idx[k] for k in [
        "CA_CHAR_01_CharacterSwapping", "CA_CHAR_02_CharacterRepetition",
        "CA_CHAR_03_CharacterInsertion", "CA_CHAR_04_CharacterDeletion",
        "CA_CHAR_05_HomoglyphPerturbation", "CA_WORD_02_EntityDisambiguation",
        "CA_WORD_04_Typos", "CA_WORD_08_LexicalSubstitution",
        "CA_WORD_12_Synonyms", "CA_WORD_13_PhoneticPerturbation",
        "CA_03_LexicallyInformed", "CA_07_AdvTrigger", "CA_16_Colloquial",
        "EA_IMP_01_ImperceptibleVerification", "EA_IMPRET_01_ImperceptibleRetrieval"
    ]
]

for cid in all_claims:
    is_top5 = any(env.outcomes[cid, idx, 0] > 0 for idx in top5_indices)
    is_any = any(env.outcomes[cid, idx, 0] > 0 for idx in range(env.num_attacks))
    if not is_top5 and is_any:
        all_34.append(cid)
        is_jumble = env.outcomes[cid, jumbling_idx, 0] > 0
        is_omission = env.outcomes[cid, omission_idx, 0] > 0
        is_surf = any(env.outcomes[cid, idx, 0] > 0 for idx in surface_indices)
        
        if not is_jumble:
            ex_jumbling_20.append(cid)
        if is_surf:
            pure_surface_15.append(cid)
        if is_surf and not is_jumble and not is_omission:
            strictly_surface_10.append(cid)

print(f"Counts: All 34={len(all_34)}, Ex-Jumbling={len(ex_jumbling_20)}, Pure Surface={len(pure_surface_15)}, Strictly Surface={len(strictly_surface_10)}")

# Domain breakdown in all 832 claims:
domain_counts_832 = {}
for cid in all_claims:
    d = env.claims[cid]["domain"]
    domain_counts_832[d] = domain_counts_832.get(d, 0) + 1

print("\nDomain counts in 832 clean claims:", domain_counts_832)

def test_domain_enrichment(subset_cids, subset_name):
    print(f"\n--- Testing Domain Enrichment for {subset_name} (N={len(subset_cids)}) ---")
    sub_counts = {}
    for cid in subset_cids:
        d = env.claims[cid]["domain"]
        sub_counts[d] = sub_counts.get(d, 0) + 1
    
    for d, total_d in domain_counts_832.items():
        k_d = sub_counts.get(d, 0)
        k_other = len(subset_cids) - k_d
        rest_d = total_d - k_d
        rest_other = (len(all_claims) - total_d) - k_other
        table = [[k_d, rest_d], [k_other, rest_other]]
        res = fisher_exact(table, alternative='greater')
        raw_p = res.pvalue
        bonf_p = min(1.0, raw_p * 6)
        print(f"  {d:25s}: {k_d}/{len(subset_cids)} ({k_d/len(subset_cids)*100:5.1f}%) vs {total_d}/832 ({total_d/832*100:5.1f}%) | raw p={raw_p:.4f}, Bonferroni p={bonf_p:.4f}")

test_domain_enrichment(all_34, "All 34 Blind Spots")
test_domain_enrichment(pure_surface_15, "15 Pure Surface Claims")
test_domain_enrichment(strictly_surface_10, "10 Strictly Surface Claims")
