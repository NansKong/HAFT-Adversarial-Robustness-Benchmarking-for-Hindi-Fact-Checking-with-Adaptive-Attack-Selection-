import re

with open(r"e:\Attack\naacl\custom.bib", "r", encoding="utf-8") as f:
    text = f.read()

# Find all entries
entries = re.findall(r"@([a-zA-Z]+)\{([^,]+),", text)
print(f"Total entries found: {len(entries)}")

# Check required entries
keys_to_check = [
    "gupta2021xfact",
    "liu2025adversarial",
    "wang2021textflint",
    "abdelnabi23usenix",
    "wang2017liar",
    "kumar2022hindi",
    "fact2fiction2026",
    "zou2025poisonedrag",
    "laurer2023building"
]

all_keys = [e[1] for e in entries]
for k in keys_to_check:
    if k in all_keys:
        print(f"[FOUND] {k}")
    else:
        print(f"[MISSING] {k}")

# Check brackets matching
open_b = text.count('{')
close_b = text.count('}')
print(f"Brackets: open={open_b}, close={close_b}")
if open_b == close_b:
    print("[PASS] Bracket balance valid!")
else:
    print("[FAIL] Bracket imbalance!")
