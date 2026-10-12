with open(r"naacl/acl_latex.tex", encoding="utf-8") as f:
    text = f.read()

print("File size:", len(text), "bytes")
print("Total lines:", len(text.splitlines()))

checks = [
    "third most spoken language",
    "consistent with subword robustness",
    "Static Top-5 (ASR-Ranked)",
    "claim-level bootstrap 95% CI",
    "account for over 92% of RL-handover rescues",
    "0 / 35 seed-level evaluation instances",
    "Fisher's exact $p = 0.005$",
    "swaps \\texttt{Fact2Fiction} for \\texttt{Word Jumbling}",
    "75.00\\%, Bonferroni $p = 0.00018$",
    "96.33\\% reproduction rate",
]

all_pass = True
for c in checks:
    found = c in text
    if not found:
        all_pass = False
    print(f"Check [{c[:45]}]: {'PASS' if found else 'FAIL'}")

print("\nOVERALL INTEGRITY:", "100% PASS - FULLY UPDATED" if all_pass else "ISSUES FOUND")
