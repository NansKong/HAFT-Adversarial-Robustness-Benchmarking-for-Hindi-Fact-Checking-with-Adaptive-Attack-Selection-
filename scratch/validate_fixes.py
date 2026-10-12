import re

with open(r"e:\Attack\naacl\acl_latex.tex", "r", encoding="utf-8") as f:
    text = f.read()

# Check begin/end environments
begins = re.findall(r"\\begin\{(.*?)\}", text)
ends = re.findall(r"\\end\{(.*?)\}", text)

print(f"Total \\begin: {len(begins)}, Total \\end: {len(ends)}")
if len(begins) != len(ends):
    print("MISMATCH in begin/end counts!")
else:
    # check stack
    stack = []
    tokens = re.findall(r"(\\begin\{.*?\}|\\end\{.*?\})", text)
    error = False
    for tok in tokens:
        if tok.startswith("\\begin"):
            env = tok[7:-1]
            stack.append(env)
        else:
            env = tok[5:-1]
            if not stack or stack[-1] != env:
                print(f"Env mismatch: expected {stack[-1] if stack else 'None'}, got {env}")
                error = True
                break
            stack.pop()
    if not error and not stack:
        print("All LaTeX environments are perfectly matched and nested!")

# Check specific edited phrases
checks = [
    ("b=511, c=11", "McNemar counts"),
    ("optimizes return-maximizing yield", "Abstract hybrid yield"),
    ("Top evidence poisoning", "Intro contribution"),
    ("41--799 eligible claims", "Table 2 caption"),
    ("optimizes discovery yield", "Sec 4.2 hybrid yield"),
    ("82.16 $\\pm$ 2.26", "Table 4 Pure RL score"),
    ("recovering \\textbf{37.0 test claims/split} that resisted Top-2 anchors", "Disambiguated rescue terminology"),
    ("vs.\\ 22.86\\% for Top-2 + Random", "Fixed uniform random label")
]

for phrase, desc in checks:
    if phrase in text:
        print(f"[PASS] {desc}")
    else:
        print(f"[FAIL] {desc}: NOT FOUND")
