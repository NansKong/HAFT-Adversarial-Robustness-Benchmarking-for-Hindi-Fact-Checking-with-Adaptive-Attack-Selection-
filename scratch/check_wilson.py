from statsmodels.stats.proportion import proportion_confint

# Test Wilson CI for AdvAdd: flips=397, n=832
ci_low, ci_high = proportion_confint(397, 832, method="wilson")
print(f"AdvAdd Uncond Wilson CI: [{ci_low*100:.2f}, {ci_high*100:.2f}] (Table 2 says [44.34, 51.11])")

# CTXREP: flips=364, n=832
ci_low, ci_high = proportion_confint(364, 832, method="wilson")
print(f"CTXREP Uncond Wilson CI: [{ci_low*100:.2f}, {ci_high*100:.2f}] (Table 2 says [40.42, 47.14])")

# FactMixing: flips=346, n=832
ci_low, ci_high = proportion_confint(346, 832, method="wilson")
print(f"FactMixing Uncond Wilson CI: [{ci_low*100:.2f}, {ci_high*100:.2f}] (Table 2 says [38.28, 44.97])")

# Fact2Fiction: flips=341, n=832
ci_low, ci_high = proportion_confint(341, 832, method="wilson")
print(f"Fact2Fiction Uncond Wilson CI: [{ci_low*100:.2f}, {ci_high*100:.2f}] (Table 2 says [37.69, 44.36])")

# Entity Disambiguation: flips=0, n=832
ci_low, ci_high = proportion_confint(0, 832, method="wilson")
print(f"EntityDisamb Uncond Wilson CI: [{ci_low*100:.2f}, {ci_high*100:.2f}] (Table 2 says [0.00, 0.46])")
