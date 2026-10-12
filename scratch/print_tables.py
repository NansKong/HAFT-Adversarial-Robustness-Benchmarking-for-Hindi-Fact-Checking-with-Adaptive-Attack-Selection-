import re

with open(r"e:\Attack\naacl\acl_latex.tex", "r", encoding="utf-8") as f:
    text = f.read()

# Let's inspect Table 1
t1 = re.search(r"(\\begin\{table\}.*?\\label\{tab:comparison\}.*?\\end\{table\})", text, re.DOTALL).group(1)
# Table 2
t2 = re.search(r"(\\begin\{table\}.*?\\label\{tab:attacks\}.*?\\end\{table\})", text, re.DOTALL).group(1)
# Table 3
t3 = re.search(r"(\\begin\{table\}.*?\\label\{tab:llm_metrics\}.*?\\end\{table\})", text, re.DOTALL).group(1)
# Table 4
t4 = re.search(r"(\\begin\{table\}.*?\\label\{tab:selection\}.*?\\end\{table\})", text, re.DOTALL).group(1)
# Table 5
t5 = re.search(r"(\\begin\{table\}.*?\\label\{tab:transfer\}.*?\\end\{table\})", text, re.DOTALL).group(1)

print("=== TABLE 2 (tab:attacks) ===")
print(t2)
print("=== TABLE 3 (tab:llm_metrics) ===")
print(t3)
print("=== TABLE 4 (tab:selection) ===")
print(t4)
print("=== TABLE 5 (tab:transfer) ===")
print(t5)
