# Project Flow — Start to End (Simple Version)

## Step 1 — Sample the Data
- Take 140 rows per domain × 8 domains = 1,120 rows from the 4,000-row Hindi dataset.
- Stratify by label (roughly 47 SUP, 47 REF, 46 NEI per domain).
- Save as `sampled_dataset_1120.csv`.

## Step 2 — Validate Labels (Cohen's Kappa)
- From the 1,120 rows, take 50 per domain (400 total).
- Two people independently label each row (SUP/REF/NEI) without looking at gold labels.
- Calculate Kappa per domain + overall. Target: > 0.60.
- Resolve disagreements through discussion.
- If any domain < 0.40, fix labeling guidelines and redo.

## Step 3 — Validate the Verifier
- Build the verifier: takes (claim, evidence), returns SUP/REF/NEI.
- Run it on 50 clean (unattacked) rows.
- Calculate baseline accuracy. Target: > 70%.
- If < 50%, switch to a stronger model.

## Step 4 — Build the Attack Engine
- 14 rule-based attacks (pure Python, no GPT).
- 8 LLM-based attacks (need GPT call to generate the attack).
- 3 of the 8 need the injected-evidence workaround (original + fabricated evidence together).
- Spot-check LLM-based attacks manually before the full run.

## Step 5 — Build the Judge
- Compares verdict vs gold label → attack succeeded or not.
- Checks fluency (is the attacked text natural Hindi?).
- Checks meaning preservation (does it still mean the same thing?).
- Excludes bad attacks (broken text, meaning drift) from results.

## Step 6 — Build the Runner (Orchestration)
- Connects everything: `apply_attack → verify → judge`.
- Loops over all 1,120 rows × 22 attacks = 24,640 test instances.
- Runs 20 calls in parallel.
- Logs every API call.

## Step 7 — Run the Full Experiment (Phase A)
- Run all 22 attacks on all 1,120 rows.
- Produces a measured success rate (%) for each attack, per domain.
- ~59,360 API calls, ~$8.90 on gpt-4o-mini (or free on Groq).

## Step 8 — Compare with LLM Guesses (Phase B)
- Convert each attack's measured success rate → Pos/Mid/Neg.
- Compare against what the 5 LLMs predicted.
- Answer: which LLM guessed best, and by how much?

## Step 9 — Build Calibrated Predictor (Phase C)
- Use Phase A results as few-shot examples.
- Ask an LLM to predict feasibility for unseen attacks.
- Compare calibrated accuracy vs raw LLM guessing.
- If better → this is the SOTA claim.

## Step 10 — Build the Streamlit UI
- Tab 1: Home (overview, stats).
- Tab 2: Browse tested attacks (success rates, LLM comparison, sample attacked text).
- Tab 3: Predict new attacks (calibrated predictor).
- Tab 4: Dashboard (charts, heatmap, LLM accuracy).

## Step 11 — Write the Report
1. Problem & motivation (LLMs disagree on 45% of attacks).
2. Architecture (3-layer: research → intelligence → interface).
3. Method (pipeline, 22 attacks, sampling, Kappa).
4. Phase A results (measured success rates).
5. Phase B results (which LLM guesses best).
6. Phase C results (calibrated predictor vs raw guessing — SOTA).
7. UI demonstration (screenshots).
8. Limitations (no defense, Hindi-only, single-evidence schema, sampling).
9. Conclusion & future work (add defense, multi-hop attacks, full dataset, multilingual).

## Step 12 — Submit

---

## Quick Reference: What Validates What

| Check | What it proves | Target |
|-------|---------------|--------|
| Cohen's Kappa (400 rows, 2 humans) | Gold labels are trustworthy | > 0.60 |
| Verifier baseline accuracy (50 rows, 1 LLM) | Verifier is reasonable on clean data | > 70% |
| Attack spot-check (5-10 samples, manual) | LLM-based attacks are not garbage | Eyeball test |

All three must pass before the full experiment runs.

## Quick Reference: API Calls

| Component | Calls per instance | 
|-----------|-------------------|
| Rule-based attack | 2 (verify + judge) |
| LLM-based attack | 3 (generate + verify + judge) |
| Total (1,120 rows × 22 attacks) | ~59,360 |
| Cost (gpt-4o-mini) | ~$8.90 |
| Free option | Groq (Llama 3, free) |
