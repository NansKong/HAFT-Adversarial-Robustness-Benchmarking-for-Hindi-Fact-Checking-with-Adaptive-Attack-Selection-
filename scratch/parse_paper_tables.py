import re

with open(r"e:\Attack\naacl\acl_latex.tex", "r", encoding="utf-8") as f:
    text = f.read()

print("File length characters:", len(text))

# Find all tables
tables = re.findall(r"(\\begin\{table\}.*?\\end\{table\})", text, re.DOTALL)
print(f"Total tables found: {len(tables)}")

for i, t in enumerate(tables):
    # extract caption and label
    cap = re.search(r"\\caption\{(.*?)\}", t, re.DOTALL)
    lbl = re.search(r"\\label\{(.*?)\}", t)
    cap_text = cap.group(1).strip() if cap else "NO CAPTION"
    lbl_text = lbl.group(1).strip() if lbl else "NO LABEL"
    print(f"\n--- TABLE {i+1}: {lbl_text} ---")
    print(f"Caption: {cap_text[:120]}...")
