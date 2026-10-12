import sys, os
sys.path.insert(0, r"e:\Attack\Attack")
import numpy as np
from scipy import stats
from replay_env import OfflineAttackEnv, ATTACK_KEYS_22

env = OfflineAttackEnv(base_dir=r"e:\Attack\Attack", max_budget_k=5, exclude_baseline_failures=True)
all_claims = env.valid_claim_ids # 832 claims
N = len(all_claims)

# Taxonomy from Table 1 / tab:attacks:
# Evid: AdvAdd, ContextReplace, Fact2Fiction, Syntactic omission, Imperceptible verification, Imperceptible retrieval
# Char: Character insertion, Character deletion, Homoglyph perturbation, Character repetition, Character swapping
# Word: Word jumbling, Typos, Phonetic, Lexical substitution, Synonym, Entity disambiguation
# Sent: Fact mixing, Claim rewrite, Adv trigger, Colloquial, Lexically informed

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

char_indices = [env.attack_to_idx[k] for k in char_keys if k in env.attack_to_idx]
evid_indices = [env.attack_to_idx[k] for k in evid_keys if k in env.attack_to_idx]

print("Char attack count:", len(char_indices))
print("Evid attack count:", len(evid_indices))

# Check flips per claim
evid_flips_claim = np.array([any(env.outcomes[cid, idx, 0] > 0 for idx in evid_indices) for cid in all_claims], dtype=bool)
char_flips_claim = np.array([any(env.outcomes[cid, idx, 0] > 0 for idx in char_indices) for cid in all_claims], dtype=bool)

print(f"Evidence flips: {evid_flips_claim.sum()} / {N} ({evid_flips_claim.mean()*100:.2f}%)")
print(f"Character flips: {char_flips_claim.sum()} / {N} ({char_flips_claim.mean()*100:.2f}%)")

# 2x2 table at claim level
# a: both flip
# b: evid flips, char does not
# c: char flips, evid does not
# d: neither flips
a = np.sum(evid_flips_claim & char_flips_claim)
b = np.sum(evid_flips_claim & (~char_flips_claim))
c = np.sum((~evid_flips_claim) & char_flips_claim)
d = np.sum((~evid_flips_claim) & (~char_flips_claim))

print("\nClaim-level 2x2 table:")
print(f"a (both): {a}")
print(f"b (evid only): {b}")
print(f"c (char only): {c}")
print(f"d (neither): {d}")
print(f"b - c = {b - c}")
print(f"553 - 53 = {553 - 53}")

# McNemar test
# Chi-sq with continuity correction: (|b - c| - 1)^2 / (b + c)
chi2_claim = (abs(b - c) - 1)**2 / (b + c)
p_val_claim = stats.chi2.sf(chi2_claim, 1)
print(f"Claim-level McNemar chi2: {chi2_claim:.2f}, p-val: {p_val_claim:.4e}")

# What if instance level?
# Total evaluations = 832 * 6 (evid) vs 832 * 5 (char)? But how would instance-level paired test even be constructed?
# What about across individual attack evaluations?
# Let's check where b=622, c=11 came from!
# Could it be b=something else, or across some subset of attacks or pairs?
