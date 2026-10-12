import json, math

with open(r"e:\Attack\Attack\results\full_run\summary.json") as f:
    d = json.load(f)["per_attack"]

# Table 2 rows in tex:
# (attack_key, displayed_raw, displayed_cond, displayed_uncond)
table2_data = [
    ("EA_ADVADD_01_AdvAdd", 61.00, 58.47, 47.72),
    ("EA_CTXREP_01_ContextualizedReplace", 63.52, 59.57, 43.75),
    ("CA_06_FactMixing", 59.82, 55.81, 41.59),
    ("EA_FACT2FICT_01_Fact2Fiction", 61.33, 57.60, 40.99),
    ("EA_CLAIMREWRITE_01_ClaimRewrite", 28.49, 25.39, 19.71),
    ("CA_WORD_03_Jumbling", 12.57, 12.57, 11.42),
    ("EA_OMITOMISSION_01_OmissionGeneration", 21.72, 19.62, 6.13),
    ("CA_CHAR_03_CharacterInsertion", 4.35, 3.63, 3.49),
    ("CA_CHAR_04_CharacterDeletion", 7.73, 3.30, 2.88),
    ("CA_WORD_04_Typos", 3.44, 2.95, 2.76),
    ("CA_07_AdvTrigger", 18.25, 4.28, 2.76),
    ("CA_CHAR_05_HomoglyphPerturbation", 3.12, 2.75, 2.52),
    ("CA_WORD_13_PhoneticPerturbation", 3.75, 3.25, 2.28),
    ("CA_16_Colloquial", 3.81, 2.43, 2.04),
    ("CA_CHAR_02_CharacterRepetition", 3.79, 2.46, 1.92),
    ("CA_WORD_08_LexicalSubstitution", 2.95, 2.47, 1.80),
    ("CA_CHAR_01_CharacterSwapping", 7.24, 1.85, 1.68),
    ("CA_03_LexicallyInformed", 2.45, 1.39, 1.08),
    ("CA_WORD_12_Synonyms", 4.73, 3.59, 0.72),
    ("EA_IMP_01_ImperceptibleVerification", 3.25, 0.40, 0.36),
    ("EA_IMPRET_01_ImperceptibleRetrieval", 2.66, 0.26, 0.24),
    ("CA_WORD_02_EntityDisambiguation", 0.00, 0.00, 0.00)
]

print(f"{'Attack':38} | {'Raw diff':8} | {'Cond diff':9} | {'Uncond calc':11} | {'Uncond diff':11}")
for k, tr, tc, tu in table2_data:
    info = d[k]
    raw = info["raw_asr"] * 100
    cond = info["gated_asr"] * 100
    uncond_calc = (info["flips_gated"] / 832.0) * 100
    print(f"{k:38} | {raw - tr:+7.2f}% | {cond - tc:+8.2f}% | {uncond_calc:10.2f}% | {uncond_calc - tu:+10.2f}%")
