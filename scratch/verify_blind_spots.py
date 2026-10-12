import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r"e:\Attack\Attack")
import numpy as np
from replay_env import OfflineAttackEnv
from rl.baselines import STATIC_TOP_5_KEYS

env = OfflineAttackEnv(base_dir=r"e:\Attack\Attack", max_budget_k=5, exclude_baseline_failures=True)
all_claims = env.valid_claim_ids # 832
top5_idx = [env.attack_to_idx[k] for k in STATIC_TOP_5_KEYS]

# Which claims have 0 flips under top 5?
zero_top5 = [cid for cid in all_claims if not any(env.outcomes[cid, a, 0] > 0 for a in top5_idx)]
print(f"Claims with zero flips under Top-5: {len(zero_top5)} (paper says 128)")

# Out of these, which flip under ANY other attack?
blind_spots = [cid for cid in zero_top5 if any(env.outcomes[cid, a, 0] > 0 for a in range(env.num_attacks))]
print(f"Blind spot claims (rescued): {len(blind_spots)} (paper says 34)")
print(f"Blind spot pct of 832: {len(blind_spots)/832*100:.2f}% (paper says 4.09%)")
print(f"Blind spot pct of 1120: {len(blind_spots)/1120*100:.2f}% (paper says 3.04%)")

# Robust to all 22 attacks:
all_22_robust = [cid for cid in zero_top5 if not any(env.outcomes[cid, a, 0] > 0 for a in range(env.num_attacks))]
print(f"Robust to all 22 attacks: {len(all_22_robust)} (paper says 94, 11.30%)")
print(f"94/832 = {len(all_22_robust)/832*100:.2f}%")
print(f"Flipped by at least one attack: {832 - len(all_22_robust)} (paper says 738, 88.70%)")

# Total rescue instances across the 34 claims:
rescue_instances = sum(sum(1 for a in range(env.num_attacks) if a not in top5_idx and env.outcomes[cid, a, 0] > 0) for cid in blind_spots)
print(f"Total rescue instances across 34: {rescue_instances} (paper says 76, mean 2.24)")

# Word jumbling rescues:
jumbling_idx = env.attack_to_idx["CA_WORD_03_Jumbling"]
jumbling_rescues = [cid for cid in blind_spots if env.outcomes[cid, jumbling_idx, 0] > 0]
print(f"Word jumbling rescues: {len(jumbling_rescues)} (paper says 19)")

# Non-jumbling rescues:
non_jumbling_rescues = [cid for cid in blind_spots if any(env.outcomes[cid, a, 0] > 0 for a in range(env.num_attacks) if a not in top5_idx and a != jumbling_idx)]
print(f"Non-jumbling rescues: {len(non_jumbling_rescues)} (paper says 20)")

# Surface perturbations rescues:
# Char + Word (excluding jumbling)
char_keys = ["CA_CHAR_01_CharacterSwapping", "CA_CHAR_02_CharacterRepetition", "CA_CHAR_03_CharacterInsertion", "CA_CHAR_04_CharacterDeletion", "CA_CHAR_05_HomoglyphPerturbation"]
word_surface_keys = ["CA_WORD_04_Typos", "CA_WORD_13_PhoneticPerturbation", "CA_WORD_08_LexicalSubstitution", "CA_WORD_12_Synonyms", "CA_WORD_02_EntityDisambiguation"]
surface_idx = [env.attack_to_idx[k] for k in char_keys + word_surface_keys if k in env.attack_to_idx]

surface_rescues = [cid for cid in blind_spots if any(env.outcomes[cid, a, 0] > 0 for a in surface_idx)]
print(f"Surface rescues: {len(surface_rescues)} (paper says 15)")

# Strictly surface-only (excluding both jumbling and syntactic omission):
omission_idx = env.attack_to_idx["EA_OMITOMISSION_01_OmissionGeneration"]
strict_surface = [cid for cid in blind_spots if any(env.outcomes[cid, a, 0] > 0 for a in surface_idx) and not env.outcomes[cid, jumbling_idx, 0] > 0 and not env.outcomes[cid, omission_idx, 0] > 0]
print(f"Strict surface-only rescues: {len(strict_surface)} (paper says 8)")
