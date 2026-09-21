# Project Execution Plan v4 — No Defense, Scaled Rows, Reassigned Team

**Version:** v4 — Defense removed, rows scaled to 1,120 (140/domain), M5 reassigned to UI, budget optimized to $9
**Team size:** 7 members (M1–M7)
**Budget:** ~$9 (approx. ₹750) — uses ~$8.90 at 1,120 rows
**Timeline:** No hard deadline — recommended 5 days at comfortable pace, 3 days if pushing.

---

# PART 0 — THE BIG PICTURE (Read This First, All Members)

## What are we building?

We are building a system that answers one question: **"Will this adversarial attack work on a Hindi fact-checking model?"**

Instead of guessing (like an LLM does), we actually RUN the attack on real Hindi data and measure the result. This is the difference between guessing "Character Swapping probably works" and knowing "Character Swapping works 67% of the time."

## The 3-layer architecture

Think of this project as building a hospital. The research lab runs experiments once. The results become published guidelines. The patient walks in and gets a diagnosis — they never touch the lab equipment.

```
LAYER 1 — RESEARCH LAYER (our team does this once, behind the scenes)
┌──────────────────────────────────────────────────────────┐
│                                                          │
│  Hindi Dataset (sampled 1,120 rows from 4,000)           │
│        │                                                 │
│        ▼                                                 │
│  Phase A: Run 22 attacks through the pipeline            │
│        │  → produces measured success rates per attack    │
│        ▼                                                 │
│  Phase B: Compare measured rates vs 5-LLM predictions     │
│        │  → produces "which LLM was right" analysis      │
│        ▼                                                 │
│  Phase C: Calibrated Predictor                           │
│  (LLM + Phase A results as few-shot examples)            │
│        │  → this IS the model                            │
│        ▼                                                 │
│  GROUND TRUTH KNOWLEDGE BASE (saved as structured data)   │
│                                                          │
└──────────────────────────────────────────────────────────┘
                         │
                         ▼
LAYER 2 — INTELLIGENCE LAYER (always available, pre-computed)
┌──────────────────────────────────────────────────────────┐
│                                                          │
│  The ground truth from Phase A/B/C is baked into the     │
│  system as saved data files (JSON/CSV). The calibrated    │
│  predictor uses these as few-shot examples.              │
│                                                          │
│  NO user ever needs to touch the dataset.                │
│  NO user ever runs the pipeline.                         │
│  The research is already done and stored.                │
│                                                          │
└──────────────────────────────────────────────────────────┘
                         │
                         ▼
LAYER 3 — INTERFACE LAYER (user-facing, what the end user sees)
┌──────────────────────────────────────────────────────────┐
│                                                          │
│  Streamlit Web UI                                        │
│                                                          │
│  User opens browser → asks a question → gets an          │
│  evidence-backed answer. No dataset, no code, no setup.   │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

## The dataset is NOT the user's input

The dataset is OUR team's research material — used once, in Phase A, to build the ground truth. The end user's input is just a question: "will this attack work?" The ground truth is already baked into our system as saved data files. The user never sees the dataset, never collects data, never runs the pipeline. They just ask and get an evidence-backed answer.

## What the end user experiences

The user opens our Streamlit web app. They see two main options:

**Mode 1 — Browse Tested Attacks:**
The user selects an attack from a dropdown (e.g., "Character Swapping"). The UI shows the measured success rate, what each of the 5 LLMs predicted vs what actually happened, and a sample of an attacked Hindi claim.

**Mode 2 — Predict New Attacks:**
The user describes an attack they're worried about in a text box. Our calibrated predictor (Phase C) uses the Phase A ground truth as few-shot examples and predicts whether it would work — returning Pos/Mid/Neg with a confidence level. This is our SOTA claim in action.

---

# PART 1 — WHAT IS AN API CALL? (All Members Read This)

## The simple explanation

Think of an API call like sending a WhatsApp message to a very smart friend (the LLM — like GPT, Gemini, Llama, etc.) and getting a reply.

You send a message: "Here is a Hindi claim and some evidence. Is this claim SUPPORTED, REFUTED, or NOT ENOUGH INFO?"

The friend reads it, thinks, and replies: "SUPPORTED"

That back-and-forth — one message sent, one reply received — is **one API call**.

Every time our code needs the LLM to do something (verify a claim, generate an attack, judge a result), that's one API call. Our project needs the LLM to do thousands of these small tasks, so the calls add up.

## The two types of calls in our pipeline (NO DEFENSE)

Our pipeline is now simpler since we removed defense. Here's what happens for one row × one attack:

The row is:
- **Claim:** "दिल्ली भारत की राजधानी है" (Delhi is the capital of India)
- **Evidence:** "नई दिल्ली भारत का राजधानी शहर है" (New Delhi is the capital city of India)
- **Gold label:** SUPPORTED

And the attack is **Character Swapping** (swaps two adjacent characters in the claim).

**Call 1 (only once per row, reused for all 22 attacks): Original verification.**
Our Verifier checks the ORIGINAL, unattacked claim against the evidence. The LLM replies: SUPPORTED. This matches the gold label, so we know the baseline is correct. We do this once per row and reuse the result for all 22 attacks.

**Now the attack runs.** Character Swapping is a rule-based attack — it's pure Python code, no LLM needed. The code swaps two characters in the claim and produces: "दिल्ली भारत की राजधानी हsi" (last word scrambled).

**Call 2: Verifier.**
Our Verifier checks the ATTACKED claim against the evidence. The LLM replies: NOT ENOUGH INFO. That's wrong — the gold label is SUPPORTED. The attack caused a wrong verdict. Attack succeeded.

**Call 3: Judge.**
Our Judge module looks at the gold label and the verdict, and decides: did the attack succeed? Was the text still fluent? It may use the LLM for a fluency check (asking "is this text natural Hindi?").

So for this one rule-based attack on this one row: **2 API calls** (verify + judge). The original verification was already done and reused.

Now, for an **LLM-based attack** (like Fact Mixing, where GPT generates the attack itself), there's one extra call:

**Call 0: Attack generation.**
The LLM is asked to generate the attack — "blend facts from this evidence into a misleading claim." This is an extra call that rule-based attacks don't need.

So for an LLM-based attack on one row: **3 API calls** (generate attack + verify + judge).

## How many total calls does our project need?

For 1,120 rows (140 per domain × 8 domains):

| Component | Calculation | Calls |
|-----------|------------|-------|
| Original verify (once per row) | 1,120 rows × 1 call | 1,120 |
| Rule-based attacks (14 attacks) | 1,120 rows × 14 attacks × 2 calls | 31,360 |
| LLM-based attacks (8 attacks) | 1,120 rows × 8 attacks × 3 calls | 26,880 |
| **Total** | | **~59,360** |

**Cost on gpt-4o-mini: ~$8.90** — fits perfectly in our $9 budget.

## How we scaled up by removing defense

| Strategy | Rows | Calls | Cost | Why |
|----------|------|-------|------|-----|
| v3 (with defense, 800 rows) | 800 | 60,000 | ~$9.00 | Defense took extra calls |
| **v4 (no defense, 1,120 rows)** | **1,120** | **59,360** | **~$8.90** | Removed defense, added more rows |
| Savings | +320 rows | -640 calls | -$0.10 | Same budget, more data |

By removing defense, each test instance needs fewer calls (2 instead of 3 for rule-based, 3 instead of 4 for LLM-based). We used those savings to test 320 more rows — that's 40 more rows per domain, giving us tighter, more reliable statistics.

## Our API strategy: $9 budget

**Option 1 — Groq (FREE, recommended as primary)**
Groq offers free API access to open-source models like Llama 3, Mixtral, and Gemma. It's extremely fast. The free tier allows around 30 requests per minute, which is about 43,200 calls per day. At that rate, ~59,000 calls would take about 1.4 days of continuous running.

How to use it: sign up at groq.com, get an API key. The API format is OpenAI-compatible, so our code barely changes.

**Option 2 — OpenRouter (FREE, backup)**
OpenRouter is an aggregator — one API key that can access many different models. Some models are completely free. Free models have rate limits around 20 requests per minute.

**Option 3 — OpenAI gpt-4o-mini (paid, ~$8.90 for 1,120 rows)**
If free options don't work out, OpenAI's gpt-4o-mini is cheap and reliable. The full 1,120-row run costs approximately $8.90. That's ₹750 split across 7 people — roughly ₹107 per person.

**Option 4 — Hybrid (best approach)**
Use Groq for the bulk of the run (free), and if it's too slow or hits rate limits, switch to a paid gpt-4o-mini key for the remaining calls.

**IMPORTANT: Consistency rule**
Whichever API we choose, we use the SAME model for all calls within a single run. Don't mix Groq's Llama 3 with OpenRouter's Mistral in the same run — that introduces inconsistency. Pick one model, stick with it for the entire Phase A run, and document which model we used in our report.

---

# PART 2 — THE PIPELINE (What Our Team Builds)

## The pipeline flow — NO DEFENSE (one test instance = one row × one attack)

```
Dataset Row (claim, evidence, gold_label)
        │
        ▼
┌─────────────────┐
│  ATTACK ENGINE   │  ← generates the attacked claim or evidence
│  (22 attacks)    │
└────────┬────────┘
         │  attacked_text
         ▼
┌─────────────────┐
│    VERIFIER      │  ← fact-checking model: returns SUP / REF / NEI
│                  │
└────────┬────────┘
         │  verdict
         ▼
┌─────────────────┐
│     JUDGE        │  ← compares verdict vs gold label, checks fluency
└────────┬────────┘
         │
         ▼
   RESULT RECORD
   (attack_id, row_id, domain, gold_label,
    verdict, attack_succeeded, fluency_ok, raw_responses)
```

**That's it.** Three steps: Attack → Verify → Judge. No defense step.

## What changed from v3

| Component | v3 (with defense) | v4 (no defense) |
|-----------|-------------------|-----------------|
| Pipeline steps | Attack → Verify → Defense → Verify → Judge | Attack → Verify → Judge |
| API calls per rule-based instance | 3 (verify + verify_def + judge) | 2 (verify + judge) |
| API calls per LLM-based instance | 4 (generate + verify + verify_def + judge) | 3 (generate + verify + judge) |
| M5 role | Defense module | **UI specialist** (Streamlit) |
| Rows within $9 budget | 800 | **1,120** |
| Total API calls | ~60,000 | ~59,360 |

## The three phases

| Phase | What | When |
|-------|------|------|
| **A — Ground Truth** | Run all 22 attacks × 1,120 sampled rows through the pipeline. Get a measured success-rate % per attack, per domain. | Build phase → Run phase |
| **B — Comparison** | Convert each attack's measured % into Pos/Mid/Neg. Compare against the 5-LLM votes. Find which LLM guessed best. | After Phase A complete |
| **C — Calibrated Predictor** | Use Phase A results as few-shot examples. Prompt an LLM to predict feasibility for unseen attacks. Compare accuracy vs raw guessing. | After Phase B complete |

---

# PART 3 — THE 22 ATTACKS WE ARE IMPLEMENTING

These are the 22 disputed-and-testable attacks from the Master Attack Knowledge Base. 14 are rule-based (pure Python, no GPT) and 8 are LLM-based (need a GPT call to generate the attack). 3 need the injected-evidence workaround.

## Group A — Rule-based attacks (14) → M2 owns these

**Character-level (5):**
1. CA_CHAR_01 — Character Swapping (randomly swap two adjacent characters within a word)
2. CA_CHAR_02 — Character Repetition (duplicate a non-initial, non-final character within a word)
3. CA_CHAR_03 — Character Insertion (insert a copy of a character immediately after itself)
4. CA_CHAR_04 — Character Deletion (randomly delete a non-initial, non-final character)
5. CA_CHAR_05 — Homoglyph Perturbation (replace characters with visually identical Unicode homoglyphs)

**Word-level (6):**
6. CA_WORD_03 — Jumbling (randomly change the order of words)
7. CA_WORD_04 — Typos (replace words with common misspellings)
8. CA_WORD_08 — Lexical Substitution (replace content words with synonyms, hypernyms, or hyponyms)
9. CA_WORD_12 — Synonyms (replace adjectives with synonyms from a lexical resource)
10. CA_WORD_13 — Phonetic Perturbation (apply phonetic changes using a dictionary)
11. CA_WORD_02 — Entity Disambiguation (replace specific entities with ambiguous mentions)

**Evidence attacks, rule-based (2):**
12. EA-IMP-01 — Imperceptible Char-Level (Verification) — modifies characters in evidence text with homoglyphs
13. EA-OMITOMISSION-01 — Omission Generation — deletes specific syntactic constructs from evidence

**Hybrid (1, split between M2 and M3):**
14. CA-03 — Lexically-informed (synonym swap part is M2 rule-based; paraphrase smoothing is M3 LLM-based)

## Group B — LLM-based attacks (8) → M3 owns these

1. CA-07 — Adv. Trigger (find a trigger phrase that flips the verdict)
2. CA-06 — Fact Mixing (blend facts from multiple evidence sources into one misleading claim)
3. CA-16 — Colloquial (rephrase a formal claim into casual spoken language)
4. EA-CLAIMREWRITE-01 — Claim-Aligned Re-Writing (mask important tokens in evidence, rewrite to mislead)
5. EA-CTXREP-01 — Contextualized Replace (replace salient words in evidence with contextually similar alternatives)
6. EA-ADVADD-01 — AdvAdd (needs injected evidence) — generate synthetic claim-conditioned adversarial evidence passages
7. EA-FACT2FICT-01 — Fact2Fiction (needs injected evidence) — targeted agentic poisoning of evidence
8. EA-IMPRET-01 — ImperceptibleRet (needs injected evidence) — inject imperceptible character perturbations into evidence for retrieval disruption

## The injected-evidence workaround (3 attacks)

For AdvAdd, Fact2Fiction, and ImperceptibleRet: the Verifier must receive the ORIGINAL evidence PLUS the attacker's fabricated evidence together, not just the fabricated text alone. This simulates corpus poisoning without a full retrieval step. M3 implements this.

---

# PART 4 — VERIFIER VALIDATION PROTOCOL (Critical — All Members Read)

## The problem this solves

The verifier is the foundation of our entire experiment. If the verifier is unreliable, every result built on top of it is unreliable. But we don't need a famous published model — we need a model whose accuracy we have MEASURED on our own Hindi data.

## The key insight: we measure change, not absolute truth

Our experiment measures the DIFFERENCE between attacked and unattacked verdicts, not the absolute correctness. The logic is:

1. Take a clean claim, verify it → get a baseline verdict.
2. Attack the claim, verify it again → get an attacked verdict.
3. If the attacked verdict differs from the baseline → the attack worked.

Even if the verifier isn't perfect, as long as it's consistent, the CHANGE in verdict is meaningful. If it says SUPPORTED on the clean claim and NOT ENOUGH INFO on the attacked claim, something about the attack caused that flip.

## But we must handle baseline failures

If the verifier gets the original (clean) claim wrong, that row is contaminated. We can't measure attack success on a row where the baseline is already wrong. So the runner must do this:

```
Step 1: Verify the ORIGINAL (unattacked) claim.
Step 2: If verdict matches gold_label → row is GOOD, proceed with attacks.
        If verdict doesn't match gold_label → row is a BASELINE FAILURE, flag it.
Step 3: For baseline-failure rows, either:
        (a) exclude them from attack success calculation, or
        (b) report them separately as "verifier couldn't handle this claim even without attack"
```

## The Day 1 validation test (M4 owns this)

Before running anything, M4 tests the verifier on 50 clean (unattacked) rows and measures baseline accuracy:

```
baseline_accuracy = (correct verdicts / total rows) × 100
```

- If baseline accuracy is above ~70%: the verifier is good enough — proceed.
- If it's below 50%: the verifier is too weak, and all attacks will "succeed" trivially. Switch to a stronger model.

That baseline accuracy number goes in our report. It becomes our benchmark.

## Which model should the verifier be?

**Best choice: A different model from the attacker.** If our LLM-based attack engine uses Llama 3 (via Groq), use a different model for the verifier — like Gemini Flash (via OpenRouter) or Mistral. Using different models makes our results more credible: "Attack X fooled a Llama-3-based verifier AND a Gemini-based verifier" is stronger than "Attack X fooled Llama 3, which was also the attacker."

**Acceptable choice: Same model, different role.** If we only have access to one free API (say Groq's Llama 3), we can use it for both attacker and verifier — but we must document this limitation in our report.

## Trust comes from measurement, not from fame

A well-known model that we didn't test on our data is less trustworthy than an unknown model whose accuracy we've actually measured on our Hindi dataset.

---

# PART 5 — ATTACK QUALITY CONTROL (Critical — All Members Read)

## The problem this solves

When the LLM-based attack engine (M3) generates an attack, there are two scenarios:

**Scenario A — Good attack (true positive):**
The LLM generates a well-crafted attack that preserves the claim's meaning but tricks the verifier. The verifier gives a wrong verdict. This is a genuine attack success.

**Scenario B — Bad attack (false positive):**
The LLM generates garbage — it changes the meaning entirely, produces broken Hindi, or creates something that doesn't match the attack definition at all. The verifier gives a wrong verdict, but not because the attack was clever — because the input was malformed. This is NOT a real attack success. It's noise.

## The solution: the Judge module filters bad attacks

The Judge does two critical checks:

**Check 1 — Fluency check.** Is the attacked text still fluent, natural Hindi? If not, mark as UNUSABLE — excluded from the success-rate calculation.

**Check 2 — Meaning preservation check.** For attacks that should preserve meaning: does the attacked claim still mean roughly the same thing as the original? If meaning drifted too far, mark as MEANING DRIFT — excluded.

Our Master Attack Knowledge Base already defines this. Every attack's Success_Criteria says: "An instance is usable for evaluation if: (a) meaning is preserved relative to the original claim unless the attack explicitly targets meaning drift, (b) the claim is fluent, natural text in your target language as judged by a native reader, (c) the assigned gold/target label is correct given the evidence, and (d) the failure mode matches the Attack Target."

Think of it like a quality gate: the LLM attacker proposes, the Judge disposes. Bad proposals get filtered out and don't count.

## The Day 1 spot-check (M3 owns this)

Before the full run, M3 takes 5-10 outputs from each LLM-based attack and manually reads them. If the LLM is generating something that doesn't match the attack definition, fix the prompt before running on 1,120 rows. This manual spot-check is the single most important quality step in the entire project.

---

# PART 6 — SAMPLING STRATEGY

## Why 1,120 rows (140 per domain)?

Our full dataset is 8 domains × 500 rows = 4,000 rows. We can't run all of it within our $9 budget. But by removing defense, we freed up API calls and can now test more rows than before.

| Strategy | Rows | Test Instances | API Calls | Cost | Confidence |
|----------|------|---------------|-----------|------|------------|
| v3 (with defense) | 800 | 17,600 | ~60,000 | ~$9.00 | ±5% |
| **v4 (no defense)** | **1,120** | **24,640** | **~59,360** | **~$8.90** | **±4%** |
| Full dataset | 4,000 | 88,000 | ~212,000 | ~$31.80 | ±2% |

1,120 rows × 22 attacks = 24,640 test instances. That's ~1,120 instances per attack across 8 domains — roughly 140 per attack per domain. This gives a success-rate percentage with a confidence interval of about ±4%.

## Sampling rules (M7 owns this)

1. Randomly select 140 rows per domain.
2. Stratify by label (SUP/REF/NEI) so the sample is balanced — roughly 47 SUP, 47 REF, 46 NEI per domain.
3. Save the sampled subset as `sampled_dataset_1120.csv`.
4. Keep the full 4,000-row dataset on file for future work.
5. If the 1,120-row run finishes clean, we can optionally run more rows as a scale validation.

---

# PART 7 — DECISIONS TO LOCK BEFORE CODING STARTS

These must be settled in a kickoff call before anyone writes code.

| # | Decision | Recommended answer | Owner |
|---|----------|-------------------|-------|
| 1 | Pos/Mid/Neg thresholds | >50% success = Pos, 20–50% = Mid, <20% = Neg. Write it down. Do not change after. | M7 |
| 2 | Injected-evidence workaround for 3 attacks | Yes — Verifier gets original + fabricated together. | M3 |
| 3 | Sampling: 140 rows/domain = 1,120 total | Yes. | M1 |
| 4 | API provider | Groq (free) primary, OpenRouter (free) backup, OpenAI ($8.90) emergency. | M1 |
| 5 | Concurrency level | Start at 20 parallel calls. | M1 |
| 6 | Keep 5-LLM consensus results on file | Yes — Phase B needs the exact Pos/Mid/Neg vote per LLM per attack. | M7 |
| 7 | Log every raw API response | Yes — save full JSON response. | M6 |
| 8 | Verifier model choice | Different from attacker if possible. Validate with baseline test (Part 4). | M4 |
| 9 | Attacker model choice | Groq Llama 3 (free) or OpenRouter free model. | M3 |

---

# PART 8 — DETAILED TEAM ASSIGNMENTS (7 Members)

## M1 — Team Lead & Orchestration

### Who you are
You are the team lead. You own the glue that connects all the modules together. Nothing runs without your orchestration layer. You make key decisions and keep everyone coordinated.

### What you build
The orchestration runner — a Python script that:
1. Loads the sampled dataset (1,120 rows)
2. Loads the list of 22 attacks
3. For each (row, attack) pair, calls the modules in sequence: `apply_attack → verify → judge`
4. Handles concurrency (20 parallel calls)
5. Handles retries and errors (if an API call fails, retry 3 times, then log and skip)
6. Writes result records to an output file
7. Logs every API call (working with M6's logger)

### What a result record looks like (NO DEFENSE)
```python
{
    "row_id": "health_001",
    "domain": "health",
    "attack_id": "CA_CHAR_01",
    "original_claim": "दिल्ली भारत की राजधानी है",
    "gold_label": "SUP",
    "baseline_verdict": "SUP",           # original, unattacked — verified once, reused
    "attacked_claim": "दिल्ली भारत की राजधानी हsi",
    "verdict": "NEI",                     # attack fooled the verifier
    "attack_succeeded": true,             # verdict != gold_label
    "fluency_ok": true,
    "meaning_preserved": true,
    "raw_responses": { ... }             # full API responses for auditing
}
```

### Your config file
```yaml
# config.yaml
dataset_path: "data/sampled_dataset_1120.csv"
attacks: "all_22"
concurrency: 20
api_provider: "groq"
api_key: "your-key-here"
model_verifier: "llama3-70b-8192"
model_attacker: "llama3-70b-8192"
output_dir: "results/"
log_file: "logs/run.jsonl"
```

### Your responsibilities across the project
- **Setup phase:** Make the kickoff decisions (Part 7). Confirm API key and provider.
- **Build phase:** Write the runner script and config file. Get ONE attack × ONE row flowing through the entire pipeline end-to-end. This is your build-phase exit criterion.
- **Run phase:** Execute the full 1,120-row run. Monitor for errors. Fix issues as they surface.
- **Analysis phase:** Oversee Phase B/C. Help M7 with analysis if needed.
- **Final:** Review everything, assemble the final submission, sign off.

### Exit criteria
- **Build phase:** Pipeline runs end-to-end on 1 attack × 1 row and produces a valid result record.
- **Run phase:** Full 1,120-row run completes. All result records saved.
- **Final:** Project submitted.

---

## M2 — Rule-based Attack Engine (14 attacks)

### Who you are
You build the attacks that are pure Python code — no GPT calls needed. This is the biggest coding chunk, but also the most reliable since you don't depend on any external API.

### What you build
14 attack functions, each of which takes a clean claim/evidence and produces an attacked version. Your code is deterministic — given the same input, it produces the same (or seeded-random) output.

### Your 14 attacks

**Character-level (5) — these modify individual characters in the claim:**

1. **Character Swapping (CA_CHAR_01):** Randomly swap two adjacent characters within a word. Example: "राजधानी" → "राजधाानी".

2. **Character Repetition (CA_CHAR_02):** Duplicate a randomly selected non-initial, non-final character within a word. Example: "राजधानी" → "राजधाननी".

3. **Character Insertion (CA_CHAR_03):** Select a non-initial, non-final character and insert a copy immediately after it.

4. **Character Deletion (CA_CHAR_04):** Randomly delete a non-initial, non-final character. Truncates the word slightly.

5. **Homoglyph Perturbation (CA_CHAR_05):** Replace characters with visually identical homoglyphs from the Unicode confusables list. BE CAREFUL with Devanagari — some homoglyphs may not exist for Hindi characters. Document which substitutions you used.

**Word-level (6) — these modify whole words in the claim:**

6. **Jumbling (CA_WORD_03):** Randomly change the order of words. Syntax is disrupted but content preserved. Example: "दिल्ली भारत की राजधानी है" → "राजधानी भारत दिल्ली है की".

7. **Typos (CA_WORD_04):** Replace words with common misspellings. For Hindi, you may need to build a small dictionary of common Hindi typos. Consult M7.

8. **Lexical Substitution (CA_WORD_08):** Replace content words (nouns, verbs, adjectives) with their synonyms, hypernyms, or hyponyms. You'll need a Hindi synonym resource.

9. **Synonyms (CA_WORD_12):** Replace adjectives with their synonyms from a lexical resource. Similar to Lexical Substitution but focused on adjectives.

10. **Phonetic Perturbation (CA_WORD_13):** Apply phonetic changes using a dictionary. Replace words with phonetically similar but different words.

11. **Entity Disambiguation (CA_WORD_02):** Replace a specific entity with an ambiguous mention. Example: "दिल्ली" → "वह शहर" (Delhi → "that city").

**Evidence attacks, rule-based (2) — these modify the EVIDENCE, not the claim:**

12. **Imperceptible Char-Level Verification (EA-IMP-01):** Modify characters inside the evidence text by replacing standard Unicode characters with visually identical homoglyphs. Same technique as Homoglyph Perturbation, but applied to evidence.

13. **Omission Generation (EA-OMITOMISSION-01):** Systematically delete specific syntactic constructs from evidence (prepositional phrases, temporal modifiers, negation words). Example: "नई दिल्ली भारत का राजधानी शहर है" → "नई दिल्ली भारत का शहर है" (राजधानी omitted).

**Hybrid (1, split with M3):**

14. **Lexically-informed (CA-03):** The first step is yours — swap nouns and adjectives for related words. The second step (paraphrase smoothing) goes to M3. You produce the intermediate result, M3 finishes it.

### Critical rules for all your attacks
- For CLAIM attacks (1-11, 14): modify the CLAIM, pass EVIDENCE through unchanged.
- For EVIDENCE attacks (12-13): modify the EVIDENCE, pass CLAIM through unchanged.
- Always preserve the original text in the metadata for comparison.
- Use a random seed so results are reproducible.
- If a perturbation can't be applied (e.g., a word is too short to swap characters), skip that word and try another.

### Interface contract (you MUST use this exact function signature)
```python
def apply_attack(claim: str, evidence: str, gold_label: str, attack_id: str) -> dict:
    """
    Applies the specified attack to the claim or evidence.

    Args:
        claim: The original Hindi claim text
        evidence: The original Hindi evidence text
        gold_label: The gold label (SUP / REF / NEI)
        attack_id: Which attack to apply (e.g., "CA_CHAR_01")

    Returns:
        {
            "attack_id": str,
            "attacked_claim": str,       # the perturbed claim
            "attacked_evidence": str,    # same as input if attack only touches claim
            "attack_metadata": dict      # any params used, for reproducibility
        }
    """
```

### Exit criteria
- **Build phase:** All 14 attacks implemented and unit-tested on 5 sample rows.
- **Run phase:** All attacks stable through the full run.

---

## M3 — LLM-based Attack Engine (8 attacks) + Injected Evidence

### Who you are
You build the attacks that need a GPT/LLM call to generate. Each attack needs a carefully designed prompt. You also handle the 3 special attacks that need the injected-evidence workaround.

### What you build
8 attack functions that use the same `apply_attack` interface as M2, but internally make an LLM API call to generate the attack. You also build the injected-evidence workaround for 3 of these attacks.

### Your 8 attacks

1. **Adv. Trigger (CA-07):** Find a short trigger phrase that, when prepended to a claim, flips the model's verdict. The original uses gradient-based optimization (HotFlip). Approximate with an LLM-based trigger search — ask the LLM to generate short trigger phrases. Document this approximation.

2. **Fact Mixing (CA-06):** Blend facts from multiple evidence sources into a single misleading claim. Prompt: "Given these evidence sentences, generate a claim that blends facts from multiple sentences in a way that misleads verification."

3. **Colloquial (CA-16):** Rephrase a formal claim into casual spoken Hindi. Prompt: "Rewrite this formal Hindi claim in casual, colloquial, conversational Hindi."

4. **Claim-Aligned Re-Writing (EA-CLAIMREWRITE-01):** Mask important tokens in gold evidence and rewrite to mislead. Approximate: ask the LLM to identify important tokens and rewrite the evidence to change their meaning.

5. **Contextualized Replace (EA-CTXREP-01):** Replace salient words in evidence with contextually similar alternatives. Prompt: "Identify the most important words in this evidence and replace them with alternatives that change the meaning."

6. **AdvAdd (EA-ADVADD-01) [NEEDS INJECTED EVIDENCE]:** Generate synthetic adversarial evidence passages. Verifier receives ORIGINAL + FABRICATED evidence together.

7. **Fact2Fiction (EA-FACT2FICT-01) [NEEDS INJECTED EVIDENCE]:** Generate fictional evidence that looks factual. Verifier receives ORIGINAL + FABRICATED evidence together.

8. **ImperceptibleRet (EA-IMPRET-01) [NEEDS INJECTED EVIDENCE]:** Inject imperceptible character perturbations into evidence. Verifier receives ORIGINAL + PERTURBED evidence together.

### The injected-evidence workaround (for attacks 6, 7, 8)
Your function returns `attacked_evidence` that is the **original evidence + fabricated evidence concatenated**.

```python
# For AdvAdd:
original_evidence = "नई दिल्ली भारत का राजधानी शहर है"
fabricated_evidence = llm_generate_fake_evidence(claim, original_evidence)
attacked_evidence = original_evidence + "\n\n" + fabricated_evidence
# The Verifier sees both together
```

### Critical: Attack Quality Control (Read Part 5)
Before the full run, you MUST spot-check your attacks. Take 5-10 outputs from each of your 8 attacks and read them manually. If the output doesn't match the attack definition, FIX THE PROMPT before running on 1,120 rows.

### Prompt design tips
- Include the attack definition from the Master Attack KB in the system prompt.
- Include 1-2 examples of clean input and correct attacked output (few-shot prompting).
- Explicitly tell the LLM to preserve meaning (unless the attack targets meaning drift).
- Explicitly tell the LLM to keep text in fluent Hindi.
- Log the generation prompt and response.

### Interface contract (same as M2)
```python
def apply_attack(claim: str, evidence: str, gold_label: str, attack_id: str) -> dict:
    """
    Returns:
        {
            "attack_id": str,
            "attacked_claim": str,
            "attacked_evidence": str,
            "attack_metadata": dict  # includes the prompt used and LLM response
        }
    """
```

### Exit criteria
- **Build phase:** All 8 attack prompts designed. At least 3 tested with manual spot-check. Injected-evidence workaround implemented.
- **Run phase:** All attacks working in the full run.

---

## M4 — Verifier Module

### Who you are
You build the fact-checking model that is being attacked — the "victim." This is the most critical module because every result depends on the verifier being reasonable and consistent.

### What you build
A verification function that takes a (claim, evidence) pair and returns a verdict: SUP, REF, or NEI.

### Your core function
```python
def verify(claim: str, evidence: str, model: str = "llama3-70b-8192") -> dict:
    """
    Verifies a claim against evidence.

    Returns:
        {
            "verdict": "SUP" | "REF" | "NEI",
            "raw_response": str,       # full model output, for auditing
            "model": str,
            "prompt_used": str
        }
    """
```

### The verification prompt
```
You are a fact-checking system. Given a claim and evidence, classify the relationship as:
- SUP (Supported): The evidence supports the claim.
- REF (Refuted): The evidence refutes the claim.
- NEI (Not Enough Info): The evidence is insufficient to determine the claim's veracity.

Claim: {claim}
Evidence: {evidence}

Respond with only one word: SUP, REF, or NEI.
```

### Critical: Verifier Validation Protocol (Read Part 4)
Before running anything, you MUST validate the verifier:
1. Take 50 clean (unattacked) rows from the sampled dataset.
2. Run the verifier on each.
3. Calculate baseline accuracy: `(correct verdicts / 50) × 100`
4. If accuracy > 70%: proceed.
5. If accuracy < 50%: switch to a stronger model.

### Response parsing
Parse defensively — the LLM might say "The claim is SUPPORTED because..." instead of just "SUP".

```python
def parse_verdict(raw_response: str) -> str:
    text = raw_response.upper().strip()
    if "SUP" in text or "SUPPORTED" in text:
        return "SUP"
    elif "REF" in text or "REFUTED" in text:
        return "REF"
    elif "NEI" in text or "NOT ENOUGH" in text:
        return "NEI"
    else:
        return "PARSE_ERROR"
```

### Original verification (once per row)
The original (unattacked) claim is verified once per row and reused across all 22 attacks. If the original verdict doesn't match the gold label, that row is flagged as a baseline failure.

### Model choice
- **Best:** Use a DIFFERENT model from the attacker (M3).
- **Acceptable:** Same model, documented as a limitation.
- Use the SAME model for all calls within a single run.

### Exit criteria
- **Build phase:** Verifier function working. Baseline test on 50 rows. Accuracy > 70%. Robust label parsing.
- **Run phase:** Stable through the full run.

---

## M5 — Streamlit UI Specialist (REASSIGNED from Defense)

### Who you are
You were previously assigned to the Defense module. Since we removed defense from this phase, you are now the **UI specialist**. You build the entire Streamlit web application that turns our research into a usable product. This is a critical role — the UI is what the teacher and end users will actually see and interact with.

### Why this role matters
M7 was previously overloaded with data, analysis, UI, AND report. By taking the UI off M7's plate, M7 can focus on data, Phase B/C analysis, and the report — while you build a polished, functional web interface. This division makes both roles stronger.

### What you build
A Streamlit web app with 4 tabs. You build the entire UI shell with placeholder data first (Day 1-2), then connect it to real results when Phase A completes.

### Tab 1 — Home / Overview
- Project title: "Hindi Adversarial Attack Feasibility Predictor"
- One-paragraph explanation of what the system does
- A simple architecture diagram
- Key stats banner: "22 attacks tested | 1,120 Hindi rows | 8 domains | 5 LLMs compared"

### Tab 2 — Browse Tested Attacks
- Dropdown: select from 22 attacks (by name)
- When selected, display:
  - Attack metadata: category, edit granularity, attack target, source paper
  - Measured success rate (large number + Pos/Mid/Neg badge)
  - 5-LLM comparison: table showing each LLM's prediction vs the measured truth (who was right?)
  - Per-domain breakdown: small bar chart showing success rate across 8 domains
  - Sample attacked text: show an original Hindi claim and its attacked version side by side

### Tab 3 — Predict New Attack
- Text box: user describes an attack in free text (e.g., "What if someone replaces all numbers in the claim with words?")
- Button: "Predict Feasibility"
- Output:
  - Calibrated prediction: Pos / Mid / Neg
  - Confidence level
  - Explanation: "Based on N similar tested attacks, the predicted success rate is X%"
  - Comparison: "Raw LLM guessing accuracy: Y% | Calibrated accuracy: Z%"
- This tab requires Phase C to be complete. If Phase C isn't done, show a "coming soon" message.

### Tab 4 — Results Dashboard
- Bar chart: all 22 attacks' success rates, sorted high to low, color-coded by Pos/Mid/Neg
- Scatter plot: LLM prediction accuracy vs measured truth (which LLMs are good guessers?)
- Heatmap: attack success rate by domain (rows = attacks, columns = 8 domains)
- Summary statistics: average attack success rate, most/least vulnerable domain

### Data files the UI reads (pre-computed, does NOT run the pipeline live)
```
/ui/data/
  attack_results_summary.csv      ← Phase A: one row per attack, success rates
  per_domain_breakdown.csv        ← Phase A: success rate per attack per domain
  llm_comparison.csv              ← Phase B: measured truth vs 5-LLM predictions
  calibrated_predictions.json     ← Phase C: calibrated predictor results
  attack_samples.json             ← sample attacked text for each attack
```

M6 produces the first two. M7 produces the rest. You build the UI that reads them.

### Your timeline
- **Day 1:** Install Streamlit (`pip install streamlit`). Build the UI shell — all 4 tabs with placeholder/dummy data. Get the layout right. This doesn't need Phase A results — just structure.
- **Day 2:** Refine the UI. Add charts (use Streamlit's built-in bar charts or Plotly). Make it look professional. Continue using placeholder data.
- **Day 3 (after Phase A):** Connect real data from M6's summary CSVs. Replace placeholders with actual results.
- **Day 4 (after Phase B/C):** Connect Phase B comparison data and Phase C predictor to Tabs 2, 3, and 4.
- **Day 5:** Polish. Test end-to-end. Take screenshots for the report.

### What you need from other members
- From M6: `attack_results_summary.csv` and `per_domain_breakdown.csv` (Phase A output)
- From M7: `llm_comparison.csv` (Phase B) and `calibrated_predictions.json` (Phase C)
- From M7: `attack_samples.json` (sample attacked text for display)
- From M1: the attack list with metadata (names, categories, descriptions)

### Sample Streamlit code to get started
```python
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Hindi Attack Feasibility Predictor", layout="wide")

# Home tab
st.title("Hindi Adversarial Attack Feasibility Predictor")
st.write("An evidence-backed system for predicting whether adversarial attacks "
         "work on Hindi automated fact-checking models.")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["Home", "Browse Attacks", "Predict New", "Dashboard"])

with tab2:
    attack_name = st.selectbox("Select an attack:", ["Character Swapping", "Typos", ...])
    # Load and display results for selected attack
    # df = pd.read_csv("ui/data/attack_results_summary.csv")
    # row = df[df['attack_name'] == attack_name]
    # st.metric("Success Rate", f"{row['success_rate']}%")
    # st.write(f"Classification: {row['pos_mid_neg']}")
```

### Exit criteria
- **Build phase:** Streamlit app runs with 4 tabs, placeholder data, professional layout.
- **After Phase A:** Tab 2 (Browse) and Tab 4 (Dashboard) connected to real data.
- **After Phase B/C:** Tab 3 (Predict) connected. All tabs fully functional.
- **Final:** UI is polished, tested, and screenshot-ready for the report.

---

## M6 — Judge Module + Logging

### Who you are
You build the module that decides whether each attack succeeded, and the logging infrastructure that records every API call. You are the quality gate of the entire project.

### What you build — two things

### Thing 1: The Judge function (NO DEFENSE — simpler than before)

```python
def judge(gold_label: str, verdict: str,
          attacked_claim: str, attacked_evidence: str, attack_id: str) -> dict:
    """
    Determines whether the attack succeeded.
    NO DEFENSE — only one verdict to compare.

    Returns:
        {
            "attack_succeeded": bool,          # verdict != gold_label
            "fluency_ok": bool,
            "meaning_preserved": bool | None,   # None if not applicable
            "fluency_score": float | None
        }
    """
```

### How the Judge decides (NO DEFENSE)

**Attack success:**
```python
attack_succeeded = (verdict != gold_label)
```
If the verdict differs from the gold label, the attack succeeded. That's it — one comparison, no defense.

### Quality control: fluency and meaning checks (Read Part 5)

**Fluency check:**
Is the attacked text still fluent, natural Hindi?
- An LLM call: "Is this Hindi text fluent and natural? Reply YES or NO: {text}"
- If fluency fails, mark `fluency_ok = False`. These instances are EXCLUDED from the success-rate calculation.

**Meaning preservation check:**
For attacks that should preserve meaning:
- An LLM call: "Does this attacked claim mean roughly the same thing as the original? Reply YES or NO: Original: {original} Attacked: {attacked}"
- If meaning drifted too far, mark `meaning_preserved = False`. These are also excluded.

### Success criteria (from the Master Attack KB)
An instance is usable if:
- (a) meaning is preserved unless the attack explicitly targets meaning drift
- (b) the claim is fluent, natural Hindi
- (c) the gold label is correct given the evidence
- (d) the failure mode matches the attack target

### Thing 2: The Logging layer

Every API call in the entire pipeline must be logged.

```python
def log_api_call(module: str, attack_id: str, row_id: str,
                 prompt: str, response: str, model: str, timestamp: str) -> None:
    log_entry = {
        "timestamp": timestamp,
        "module": module,         # "attack_engine", "verifier", "judge"
        "attack_id": attack_id,
        "row_id": row_id,
        "model": model,
        "prompt": prompt,
        "response": response
    }
    with open("logs/run.jsonl", "a") as f:
        f.write(json.dumps(log_entry) + "\n")
```

### What you produce at the end
A clean summary CSV — one row per attack:

| attack_id | attack_name | category | success_rate | total_instances | usable_instances | excluded_instances | per_domain_rates |
|-----------|-------------|----------|-------------|-----------------|-----------------|-------------------|------------------|

And a per-domain breakdown CSV:

| attack_id | attack_name | health | politics | sports | science | ... (8 domains) |
|-----------|-------------|--------|----------|--------|---------|------------------|

These feed M5's UI and M7's Phase B analysis.

### Exit criteria
- **Build phase:** Judge function + logging layer working. Test on synthetic examples.
- **Run phase:** Produces the per-attack success-rate summary table + per-domain breakdown.

---

## M7 — Data, Sampling, Phase B/C Analysis & Report

### Who you are
You own the dataset, the sampling, the Phase B/C analysis, and the final report. M5 has taken over the UI, so you can now focus entirely on data, analysis, and writing. This is a much more focused role than in v3.

### Your responsibilities, broken into 4 parts

### Part A: Data and Sampling (Build phase)

1. **Load and validate the Hindi dataset** (8 domains × 500 rows = 4,000 rows total).
   - Confirm each row has: claim, evidence, gold_label (SUP/REF/NEI), domain.
   - Check for missing values, empty claims, or malformed text.

2. **Sample 140 rows per domain** (stratified by label) → 1,120 rows.
   ```python
   def sample_dataset(full_dataset_path: str, rows_per_domain: int = 140,
                      stratify_by: str = "label") -> str:
       df = pd.read_csv(full_dataset_path)
       sampled = df.groupby('domain', group_keys=False).apply(
           lambda x: x.groupby('label', group_keys=False).sample(
               n=max(1, rows_per_domain // 3), replace=True
           )
       )
       sampled.to_csv("data/sampled_dataset_1120.csv", index=False)
       return "data/sampled_dataset_1120.csv"
   ```

3. **Locate and organize the 5-LLM consensus vote file** (Pos/Mid/Neg predictions for all 53 attacks). Phase B needs this.

4. **Define the Pos/Mid/Neg thresholds** (must happen before any run):
   - >50% success = Pos
   - 20–50% = Mid
   - <20% = Neg
   - Write it down. Do not change it after the run.

### Part B: Phase B — Comparison (After Phase A)

1. Take M6's success-rate summary table.
2. Convert each attack's measured success rate → Pos/Mid/Neg using the locked thresholds.
3. Build the comparison table: for each of the 22 attacks, show:
   - Measured success rate (%)
   - Converted Pos/Mid/Neg
   - What each of the 5 LLMs predicted (from the consensus vote file)
   - Whether each LLM was right or wrong
4. Compute: which LLM was most accurate? By how much?
5. Produce `llm_comparison.csv` for M5's UI.

### Part C: Phase C — Calibrated Predictor (After Phase B)

1. Use Phase A results as few-shot examples in a prompt.
2. Design a prompt:
   ```
   You are predicting whether an adversarial attack will work on a Hindi
   fact-checking model. Here are real measured results from similar attacks:

   Example 1: Attack "{name}" — character-level swapping. Measured success: 67% → Pos.
   Example 2: Attack "{name}" — word-level synonym replacement. Measured success: 34% → Mid.
   Example 3: Attack "{name}" — sentence-level fact mixing. Measured success: 12% → Neg.

   Now predict: Attack "{new_attack_description}"
   ```
3. Test on held-out attacks (attacks we tested but didn't include in the few-shot examples).
4. Compare calibrated accuracy vs raw 5-LLM accuracy.
5. If the calibrated predictor is measurably better — that number is our SOTA claim.
6. Produce `calibrated_predictions.json` for M5's UI.

### Part D: Final Report

Write the final report with this structure:
1. Problem & motivation (LLM disagreement on 45% of attacks)
2. System architecture (3-layer: research → intelligence → interface)
3. Method (pipeline + 22 attacks + 3 phases + sampling strategy)
4. Phase A results (measured success rates, per-domain breakdown)
5. Phase B results (which LLM guesses best — comparison table)
6. Phase C results (calibrated predictor vs raw guessing — the SOTA claim)
7. UI demonstration (screenshots from M5, usage instructions)
8. Limitations (no defense module, single-evidence schema, Hindi-only, approximate trigger search, sampling)
9. Conclusion & future work (add defense module, multi-hop attacks, full 4,000-row run, multilingual expansion)

**Note on limitations:** The removal of defense is a legitimate scoping decision. Report it honestly: "This phase focuses on measuring attack feasibility without defense. A defense module is planned as future work to measure how effectively each attack can be neutralized."

### Exit criteria
- **Build phase:** Dataset loaded, sampled (1,120 rows), validated. 5-LLM vote file located. Thresholds written.
- **After Phase A:** Support the run.
- **After Phase B/C:** Phase B comparison table. Phase C predictor tested. `llm_comparison.csv` and `calibrated_predictions.json` produced for M5.
- **Final:** Report written.

---

# PART 9 — INTERFACE CONTRACTS (Pin This on the Wall)

Everyone must use these EXACT function signatures. NO DEFENSE function anymore.

```python
# M2/M3: Attack Engine
def apply_attack(claim: str, evidence: str, gold_label: str, attack_id: str) -> dict:
    """
    Returns: {
        "attack_id": str,
        "attacked_claim": str,
        "attacked_evidence": str,   # same as input if attack only touches claim
        "attack_metadata": dict
    }
    """

# M4: Verifier
def verify(claim: str, evidence: str, model: str = "llama3-70b-8192") -> dict:
    """
    Returns: {
        "verdict": "SUP" | "REF" | "NEI",
        "raw_response": str,
        "model": str,
        "prompt_used": str
    }
    """

# M6: Judge (NO DEFENSE — only one verdict)
def judge(gold_label: str, verdict: str,
          attacked_claim: str, attacked_evidence: str, attack_id: str) -> dict:
    """
    Returns: {
        "attack_succeeded": bool,          # verdict != gold_label
        "fluency_ok": bool,
        "meaning_preserved": bool | None,
        "fluency_score": float | None
    }
    """

# M6: Logger
def log_api_call(module: str, attack_id: str, row_id: str,
                 prompt: str, response: str, model: str, timestamp: str) -> None:
    """Appends a JSONL line to the run log."""

# M1: Orchestration (NO DEFENSE — simpler pipeline)
def run_pipeline(rows: list, attack_ids: list, config: dict) -> list:
    """
    For each (row, attack_id):
      apply_attack → verify → judge
    Returns list of result records. Logs every API call.
    """

# M7: Sampling
def sample_dataset(full_dataset_path: str, rows_per_domain: int = 140,
                   stratify_by: str = "label") -> str:
    """
    Loads full dataset, samples N rows per domain (stratified by label),
    saves to sampled_dataset_1120.csv, returns path.
    """
```

---

# PART 10 — PROJECT TIMELINE (Flexible, No Hard Deadline)

## Day 1 — Kickoff and Build Start

**Morning: Kickoff call (all members, 30 minutes)**
- M1 leads. Lock the 9 decisions from Part 7.
- Confirm everyone knows their interface contracts (Part 9).
- Confirm the data file path and the 5-LLM vote file path.
- M7 presents the sampling plan and thresholds.
- Assign someone to get a Groq API key (free) and test it.

**Afternoon–Evening: Build (all members work in parallel)**
| Member | Task | Exit criterion |
|--------|------|---------------|
| M1 | Orchestration runner + config | Pipeline runs on 1 attack × 1 row |
| M2 | All 14 rule-based attacks | Unit-tested on 5 sample rows |
| M3 | All 8 LLM-based attacks + injected evidence | At least 3 tested, manually spot-checked |
| M4 | Verifier function + baseline validation | Baseline accuracy > 70% on 50 rows |
| M5 | Streamlit UI shell with 4 tabs | App runs with placeholder data |
| M6 | Judge + logging | Working on synthetic examples |
| M7 | Data sampling (1,120 rows), thresholds, vote file | Sampled, validated, thresholds locked |

## Day 2 — Integration and Pilot Run

**Morning: Integration test (M1 + anyone needed)**
- Connect all modules. Run 1 attack × 5 rows end-to-end.
- Fix interface mismatches.
- Exit criterion: pipeline produces a valid result record for at least 1 attack on 5 rows.

**Afternoon: Pre-run checklist and smoke test**
- Confirm all 22 attacks implemented.
- Confirm logging active.
- Confirm API key, rate limits, concurrency = 20.
- Run a 5-row smoke test across all 22 attacks.

**Evening: Start the full run**
- Run 22 attacks × 1,120 rows = 24,640 test instances.
- ~59,360 API calls. At 20 concurrent, ~1.6 hours compute time.
- M1 monitors. M2/M3 fix bugs. M6 monitors logs.
- M5 continues refining UI. M7 supports.

## Day 3 — Results and Analysis

**Morning: Results review (M6 + M7)**
- M6 produces the per-attack success-rate summary + per-domain breakdown.
- M7 reviews: do the results make sense?
- Flag anomalies. Re-run specific attacks if needed.

**Afternoon: Phase B — Comparison (M7)**
- Convert measured success rates → Pos/Mid/Neg.
- Build comparison table: measured vs 5-LLM predictions.
- Compute: which LLM was most accurate?

**Evening: Phase C — Calibrated Predictor (M7 + M1)**
- Use Phase A results as few-shot examples.
- Test on held-out attacks.
- Compare calibrated accuracy vs raw guessing.

**M5 connects real data to UI (Tabs 2 and 4).**

## Day 4 — UI Finalization and Report

**Morning: UI completion (M5 + M7)**
- M5 connects Phase B/C data to UI (Tabs 2, 3, 4).
- Test the full UI end-to-end.
- M7 provides `attack_samples.json` for the Browse tab.

**Afternoon: Report writing (M7, all members contribute)**
- M7 writes the final report.
- M5 provides UI screenshots.
- All members review their sections.

## Day 5 — Buffer and Polish

- Fix any remaining bugs.
- Re-run any attacks that had issues.
- Polish the UI.
- Final review of the report.
- Practice a demo walkthrough.
- Submit.

---

# PART 11 — RISK REGISTER

| Risk | Impact | Mitigation | Owner |
|------|--------|------------|-------|
| Interface mismatch between modules | Blocks integration | Define contracts Day 1 (Part 9). Integration test Day 2. | M1 |
| LLM-based attack prompts produce bad output | Invalid Phase A data | M3 spot-checks each prompt on 5 rows (Part 5). | M3 |
| Verifier too weak (low baseline accuracy) | All attacks "succeed" trivially | M4 validates baseline on 50 rows. Switch models if < 70% (Part 4). | M4 |
| Verifier label parsing fails | Wrong success rates | M4 parses defensively. | M4 |
| API rate limits hit mid-run | Run stalls | Start at concurrency 20. Backup: Groq → OpenRouter → OpenAI. | M1 |
| Baseline claims get wrong verdicts | Contaminates results | M1's runner verifies originals first, flags failures. | M1 |
| Hindi-specific issues (typos, homoglyphs) | Attack doesn't work | M2 consults M7. Build small Hindi dictionaries. | M2+M7 |
| Phase C predictor doesn't beat raw guessing | Weakens SOTA claim | Valid negative result — report honestly. Phase A benchmark is still first-of-its-kind. | M7 |
| UI not finished | No demo | UI shell with placeholder data is still a valid demo. Connect real data only if time allows. | M5 |
| Bad attacks inflate success rates | False results | Judge filters by fluency + meaning preservation (Part 5). | M6 |

---

# PART 12 — PRIORITY ORDER IF YOU RUN OUT OF TIME

## Attacks — cut order
1. **Keep:** All 14 rule-based attacks (fastest, most reliable)
2. **Keep:** The 5 LLM-based attacks without injected evidence
3. **Cut if needed:** The 3 injected-evidence attacks (AdvAdd, Fact2Fiction, ImperceptibleRet)

## UI tabs — cut order
1. **Keep:** Tab 1 (Home) + Tab 2 (Browse) — minimum viable UI
2. **Keep if possible:** Tab 4 (Dashboard) — high visual impact
3. **Cut if needed:** Tab 3 (Predict New Attack) — requires Phase C

## Phases — cut order
1. **Keep:** Phase A (ground truth) — core contribution
2. **Keep:** Phase B (comparison) — fast, high value
3. **Cut if needed:** Phase C (calibrated predictor) — report as future work

---

# PART 13 — SUBMISSION CHECKLIST

- [ ] Phase A: measured success rate for all (or most) of the 22 attacks on 1,120 sampled rows, across 8 domains
- [ ] Phase B: comparison table — measured result vs 5-LLM predictions, "which LLM guessed best" answered
- [ ] Phase C: calibrated predictor tested, accuracy compared to raw guessing (positive or negative result, reported honestly)
- [ ] Full raw API logs saved (JSONL)
- [ ] Per-attack success-rate summary table + per-domain breakdown
- [ ] Verifier baseline accuracy documented
- [ ] Streamlit UI with at least 2 functional tabs (Home + Browse)
- [ ] Final report with: motivation, architecture, method, 3-phase results, UI demo, limitations (including no defense), SOTA claim, future work (including adding defense)
- [ ] Code repository organized
- [ ] Pos/Mid/Neg thresholds documented
- [ ] Sampling methodology documented (140 rows/domain, stratified by label)
- [ ] API provider and model documented

---

# PART 14 — REPOSITORY STRUCTURE

```
project-root/
├── data/
│   ├── full_dataset/              ← 8 domains × 500 rows (original)
│   ├── sampled_dataset_1120.csv   ← M7's sampled subset
│   └── llm_consensus_votes.csv    ← 5-LLM Pos/Mid/Neg predictions
├── attack_engine/
│   ├── rule_based/                ← M2's 14 attacks
│   ├── llm_based/                 ← M3's 8 attacks
│   └── attack_registry.py         ← maps attack_id → function
├── verifier/
│   └── verifier.py                ← M4's verifier
├── judge/
│   ├── judge.py                   ← M6's judge (NO DEFENSE)
│   └── logger.py                  ← M6's logging
├── orchestration/
│   ├── runner.py                  ← M1's pipeline runner
│   └── config.yaml                ← run configuration
├── analysis/
│   ├── phase_b_comparison.py      ← M7's Phase B
│   ├── phase_c_predictor.py       ← M7's Phase C
│   └── results/                   ← output CSVs and JSONs
├── ui/
│   ├── app.py                     ← M5's Streamlit app
│   └── data/                      ← pre-computed data for UI
├── logs/
│   └── run_YYYYMMDD.jsonl         ← raw API logs
├── report/
│   └── final_report.pdf
├── tests/
│   ├── test_attacks.py
│   ├── test_verifier.py
│   └── test_judge.py
└── README.md
```

Note: no `/defense/` directory — that module is removed for this phase.

---

# PART 15 — FINAL NOTES FOR THE TEAM

## To all members

1. **Read Part 0 (Big Picture), Part 1 (API), Part 4 (Verifier Validation), and Part 5 (Attack Quality Control) first.** These explain the concepts everyone needs.

2. **No defense module.** The pipeline is: Attack → Verify → Judge. Three steps. Simpler, faster, fewer API calls, more rows tested.

3. **Use the EXACT interface contracts in Part 9.** No `apply_defense` function anymore. The Judge takes one verdict, not two.

4. **Log everything.** Save full raw responses.

5. **If stuck, ask.** Don't silently block.

## To M1 (team lead)
- Your integration test is simpler now — no defense step to connect.
- Pipeline: `apply_attack → verify → judge`. Three calls per instance (two for rule-based).

## To M2 and M3 (attack engine)
- M3: your spot-check (Part 5) is the most important quality step. Do NOT skip it.

## To M4 (verifier)
- Your baseline validation (Part 4) is the most important test. A weak verifier makes every result meaningless.

## To M5 (UI — NEW ROLE)
- You are no longer on defense. You own the entire Streamlit UI.
- Build the shell with placeholder data on Day 1. Connect real data on Day 3.
- The UI is what the teacher and end users will see — make it professional.

## To M6 (judge + logging)
- Your Judge function is simpler now — only one verdict to compare, no defense comparison.
- But your quality gate role (fluency + meaning checks) is unchanged and critical.

## To M7 (data, analysis, report)
- M5 took the UI off your plate. Focus on data, Phase B/C, and the report.
- In the report, document the removal of defense as a scoping decision, not a gap.

---

*This plan supersedes all previous versions. Share with all 7 members. Read Part 0, Part 1, Part 4, and Part 5 together in your kickoff call. Then confirm Part 9 (Interface Contracts) before anyone writes code.*
