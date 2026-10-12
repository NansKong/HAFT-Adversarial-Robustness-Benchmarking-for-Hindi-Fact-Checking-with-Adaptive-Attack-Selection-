import pandas as pd
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, cohen_kappa_score

df = pd.read_csv(r"e:\Attack\Attack\results\full_run\llm_comparison.csv")
y_true = df["empirical_tier"].values
models = ["gpt4o", "claude", "kimi", "sarvam", "deepseek"]

print("Truth counts:", pd.Series(y_true).value_counts().to_dict())

for m in models:
    pred_col = f"{m}_pred"
    y_pred = df[pred_col].values
    acc = accuracy_score(y_true, y_pred) * 100
    bal_acc = balanced_accuracy_score(y_true, y_pred) * 100
    macro_f1 = f1_score(y_true, y_pred, average="macro") * 100
    kappa = cohen_kappa_score(y_true, y_pred)
    counts = pd.Series(y_pred).value_counts().to_dict()
    p_count = counts.get("POS", 0)
    m_count = counts.get("MID", 0)
    n_count = counts.get("NEG", 0)
    print(f"{m:10}: Acc={acc:.2f}%, BalAcc={bal_acc:.2f}%, MacroF1={macro_f1:.2f}%, Kappa={kappa:.3f}, Pred=[{p_count}/{m_count}/{n_count}]")
