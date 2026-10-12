import re, sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r"e:\Attack\naacl\acl_latex.tex", "r", encoding="utf-8") as f:
    text = f.read()

# 1. Check all section references
# Find all \label{sec:...}
sec_labels = set(re.findall(r"\\label\{(sec:[^}]+)\}", text))
print("Defined section labels:", sec_labels)
# Find all \ref{sec:...}
sec_refs = re.findall(r"\\ref\{(sec:[^}]+)\}", text)
print("Referenced section labels:", set(sec_refs))
for r in sec_refs:
    if r not in sec_labels:
        print("  [ERROR] Undefined section label referenced:", r)

# 2. Check all table references
tab_labels = set(re.findall(r"\\label\{(tab:[^}]+)\}", text))
print("\nDefined table labels:", tab_labels)
tab_refs = re.findall(r"\\ref\{(tab:[^}]+)\}", text)
print("Referenced table labels:", set(tab_refs))
for r in tab_refs:
    if r not in tab_labels:
        print("  [ERROR] Undefined table label referenced:", r)

# 3. Check all equation references
eq_labels = set(re.findall(r"\\label\{(eq:[^}]+)\}", text))
print("\nDefined eq labels:", eq_labels)
eq_refs = re.findall(r"\\ref\{(eq:[^}]+)\}", text)
print("Referenced eq labels:", set(eq_refs))
for r in eq_refs:
    if r not in eq_labels:
        print("  [ERROR] Undefined eq label referenced:", r)

# 4. Check all figure references
fig_labels = set(re.findall(r"\\label\{(fig:[^}]+)\}", text))
print("\nDefined fig labels:", fig_labels)
fig_refs = re.findall(r"\\ref\{(fig:[^}]+)\}", text)
print("Referenced fig labels:", set(fig_refs))
for r in fig_refs:
    if r not in fig_labels:
        print("  [ERROR] Undefined fig label referenced:", r)

