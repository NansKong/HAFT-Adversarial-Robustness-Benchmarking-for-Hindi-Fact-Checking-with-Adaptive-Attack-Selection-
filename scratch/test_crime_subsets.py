import sys, os
sys.path.insert(0, r"e:\Attack\Attack")
import numpy as np
from replay_env import OfflineAttackEnv, ATTACK_KEYS_22
from rl.baselines import STATIC_TOP_5_KEYS
from scipy.stats import fisher_exact

env = OfflineAttackEnv(base_dir=r"e:\Attack\Attack", exclude_baseline_failures=True)
top5_indices = [env.attack_to_idx[k] for k in STATIC_TOP_5_KEYS]
outcomes = env.outcomes[env.valid_claim_ids, :, 0]
top5_flips = np.any(outcomes[:, top5_indices] > 0.5, axis=1)

jumble_idx = env.attack_to_idx["CA_WORD_03_Jumbling"]
omission_idx = env.attack_to_idx["EA_OMITOMISSION_01_OmissionGeneration"]
non_top5_non_jumble = [i for i in range(22) if i not in top5_indices and i != jumble_idx]

immune_to_top5 = ~top5_flips
rescued_20_idx = np.where(immune_to_top5 & np.any(outcomes[:, non_top5_non_jumble] > 0.5, axis=1))[0]
rescued_20_cids = env.valid_claim_ids[rescued_20_idx]

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
surface_15_idx = [i for i in rescued_20_idx if np.any(outcomes[i, surface_indices] > 0.5)]
surface_15_cids = env.valid_claim_ids[surface_15_idx]

# 10 surface-only claims (no jumbling, no omission):
surface_10_idx = [i for i in surface_15_idx if outcomes[i, jumble_idx] <= 0.5 and outcomes[i, omission_idx] <= 0.5]
surface_10_cids = env.valid_claim_ids[surface_10_idx]
print(f"Verified lengths: 20 -> {len(rescued_20_cids)}, 15 -> {len(surface_15_cids)}, 10 -> {len(surface_10_cids)}")

domain_counts_832 = {}
for cid in env.valid_claim_ids:
    d = env.claims[cid]["domain"]
    domain_counts_832[d] = domain_counts_832.get(d, 0) + 1

for name, cids in [("20 Non-Jumbling Claims", rescued_20_cids), 
                   ("15 Pure Surface Claims", surface_15_cids), 
                   ("10 Strictly Surface-Only Claims", surface_10_cids)]:
    sub_counts = {}
    for cid in cids:
        d = env.claims[cid]["domain"]
        sub_counts[d] = sub_counts.get(d, 0) + 1
    k_crime = sub_counts.get('Crime_PublicSafety', 0)
    k_other = len(cids) - k_crime
    rest_crime = domain_counts_832['Crime_PublicSafety'] - k_crime
    rest_other = (832 - domain_counts_832['Crime_PublicSafety']) - k_other
    table = [[k_crime, rest_crime], [k_other, rest_other]]
    res = fisher_exact(table, alternative='greater')
    print(f"{name:30s}: Crime {k_crime}/{len(cids)} ({k_crime/len(cids)*100:.1f}%) | raw p={res.pvalue:.5f}, Bonferroni p={min(1.0, res.pvalue*6):.5f}")
