with open(r"e:\Attack\naacl\acl_latex.tex", "r", encoding="utf-8") as f:
    text = f.read()

# Let's count words in Section 5
sec5_start = text.find(r"\section{Coverage-Aware Budgeted Auditing Methodology (RQ3)}")
sec6_start = text.find(r"\section{Cross-Architecture Generalization")

sec5_text = text[sec5_start:sec6_start]
print("Section 5 character length:", len(sec5_text))
print("Section 5 word count:", len(sec5_text.split()))

# Where is table 4 in Section 5?
tab4_pos = sec5_text.find(r"\begin{table}[!t]")
print("Table 4 offset in Section 5:", tab4_pos)
print("Before Table 4 character length:", tab4_pos)
print("After Table 4 character length:", len(sec5_text) - tab4_pos)
