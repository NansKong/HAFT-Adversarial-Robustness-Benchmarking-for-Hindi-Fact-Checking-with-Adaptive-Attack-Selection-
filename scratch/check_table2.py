import sys, os, re, json
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r"e:\Attack\Attack")
import numpy as np

# Load summary.json if available
summary_path = r"e:\Attack\Attack\results\full_run\summary.json"
if os.path.exists(summary_path):
    with open(summary_path, "r", encoding="utf-8") as f:
        summary = json.load(f)
    print("Loaded summary.json, total attacks:", len(summary.get("attacks", summary)))
else:
    print("summary.json not found")

# Let's extract rows of Table 2 from acl_latex.tex
with open(r"e:\Attack\naacl\acl_latex.tex", "r", encoding="utf-8") as f:
    text = f.read()

t2 = re.search(r"\\begin\{table\}.*?\\label\{tab:attacks\}(.*?)\\end\{table\}", text, re.DOTALL).group(1)
rows = re.findall(r"([A-Za-z0-9\\& \(\)\-`_]+)\s*&\s*([A-Za-z0-9\\. \(\)]+)\s*&\s*([0-9\.]+)\s*&\s*([0-9\.\\textbf\{\}]+)\s*&\s*([0-9\.\\textbf\{\}]+)\s*&\s*(\[[0-9\., ]+\])\s*&\s*([A-Z]+)", t2)
print(f"Extracted {len(rows)} rows from Table 2 in tex")

for r in rows:
    name, fam, raw, cond, uncond, ci, tier = r
    clean_cond = cond.replace("\\textbf{", "").replace("}", "")
    clean_uncond = uncond.replace("\\textbf{", "").replace("}", "")
    print(f"{name.strip()[:35]:35} | {fam.strip():10} | Raw:{raw.strip():5} | Cond:{clean_cond.strip():5} | Uncond:{clean_uncond.strip():5} | CI:{ci.strip():16} | Tier:{tier.strip()}")

