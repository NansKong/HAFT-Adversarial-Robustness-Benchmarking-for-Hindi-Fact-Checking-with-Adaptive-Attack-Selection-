import sys, os
sys.path.insert(0, r"e:\Attack\Attack")
import numpy as np
from scipy import stats
from replay_env import OfflineAttackEnv

env_all = OfflineAttackEnv(base_dir=r"e:\Attack\Attack", max_budget_k=5, exclude_baseline_failures=False)
all_claims_1120 = env_all.valid_claim_ids

char_keys = [
    "CA_CHAR_03_CharacterInsertion",
    "CA_CHAR_04_CharacterDeletion",
    "CA_CHAR_05_HomoglyphPerturbation",
    "CA_CHAR_02_CharacterRepetition",
    "CA_CHAR_01_CharacterSwapping"
]

evid_keys = [
    "EA_ADVADD_01_AdvAdd",
    "EA_CTXREP_01_ContextualizedReplace",
    "EA_FACT2FICT_01_Fact2Fiction",
    "EA_OMITOMISSION_01_OmissionGeneration",
    "EA_IMP_01_ImperceptibleVerification",
    "EA_IMPRET_01_ImperceptibleRetrieval"
]

char_idx = [env_all.attack_to_idx[k] for k in char_keys if k in env_all.attack_to_idx]
evid_idx = [env_all.attack_to_idx[k] for k in evid_keys if k in env_all.attack_to_idx]

evid_flips_1120 = np.array([any(env_all.outcomes[cid, idx, 0] > 0 for idx in evid_idx) for cid in all_claims_1120], dtype=bool)
char_flips_1120 = np.array([any(env_all.outcomes[cid, idx, 0] > 0 for idx in char_idx) for cid in all_claims_1120], dtype=bool)

a_1120 = np.sum(evid_flips_1120 & char_flips_1120)
b_1120 = np.sum(evid_flips_1120 & (~char_flips_1120))
c_1120 = np.sum((~evid_flips_1120) & char_flips_1120)
d_1120 = np.sum((~evid_flips_1120) & (~char_flips_1120))

print(f"1,120 claims: a={a_1120}, b={b_1120}, c={c_1120}, d={d_1120}")
print(f"Total evid flips: {evid_flips_1120.sum()}, total char flips: {char_flips_1120.sum()}")
