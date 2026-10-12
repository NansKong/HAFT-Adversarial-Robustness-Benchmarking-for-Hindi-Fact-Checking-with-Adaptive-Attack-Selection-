import sys, os, glob, json
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r"e:\Attack\Attack")
import pandas as pd

# Check each of the 22 attack result files in results/full_run
result_files = glob.glob(r"e:\Attack\Attack\results\full_run\*_results.csv")
print(f"Total result files found: {len(result_files)}")

eligible_counts = []
for rf in result_files:
    df = pd.read_csv(rf)
    # Check baseline_failure column if exists
    # Baseline-correct claims: baseline_failure == False
    if "baseline_failure" in df.columns:
        df_clean = df[df["baseline_failure"] == False]
    else:
        df_clean = df
    
    # Check quality gate / eligible
    # Look at columns in df
    cols = df.columns.tolist()
    # Let's inspect columns of one file
    # print(rf, cols)
    # Typically gated means quality_passed == True or is_eligible / flip
    eligible_counts.append((os.path.basename(rf), len(df_clean)))

print("Sample clean counts:", eligible_counts[:5])
