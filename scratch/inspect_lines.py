with open(r"e:\Attack\naacl\acl_latex.tex", "r", encoding="utf-8") as f:
    lines = f.readlines()

print(f"Total lines in source: {len(lines)}")
for idx, line in enumerate(lines):
    if "tab:selection" in line:
        print(f"Table 4 declared around line {idx+1}")
    if "Coverage-Aware Auditing" in line:
        print(f"Coverage-aware text around line {idx+1}")
    if "sec:transfer" in line:
        print(f"Section transfer around line {idx+1}")
