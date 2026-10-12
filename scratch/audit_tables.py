import sys, os, re
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r"e:\Attack\Attack")
import numpy as np

with open(r"e:\Attack\naacl\acl_latex.tex", "r", encoding="utf-8") as f:
    text = f.read()

# Let's extract each table and analyze it
tables = re.findall(r"(\\begin\{table\}.*?\\end\{table\})", text, re.DOTALL)

for i, t in enumerate(tables):
    lbl_m = re.search(r"\\label\{(.*?)\}", t)
    lbl = lbl_m.group(1) if lbl_m else f"table_{i+1}"
    print(f"\n{'='*20} {lbl} {'='*20}")
    cap_m = re.search(r"\\caption\{(.*?)\}", t, re.DOTALL)
    print("CAPTION:", cap_m.group(1).replace('\n', ' ') if cap_m else "None")
    
    # Check in-text references to this table
    refs = re.findall(rf"[^.\n]*?\\ref\{{{lbl}\}}[^.\n]*", text)
    print(f"REFERENCES in text ({len(refs)}):")
    for r in refs:
        print("  ->", r.strip())

