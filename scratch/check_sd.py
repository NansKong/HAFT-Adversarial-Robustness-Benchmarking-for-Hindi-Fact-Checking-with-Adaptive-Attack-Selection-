import json, numpy as np

with open(r"e:\Attack\Attack\results\stage2\rl\rl_5seed_runs.json") as f:
    d = json.load(f)

# check seeds
runs = d.get("seed_runs", d)
print("Keys in rl_5seed_runs:", list(d.keys()))
if "seed_runs" in d:
    scores = [r["test_discovery_rate"] * 100 if r["test_discovery_rate"] < 1 else r["test_discovery_rate"] for r in d["seed_runs"]]
    print("Scores:", scores)
    print("Mean:", np.mean(scores))
    print("SD (ddof=0):", np.std(scores, ddof=0))
    print("SD (ddof=1):", np.std(scores, ddof=1))
