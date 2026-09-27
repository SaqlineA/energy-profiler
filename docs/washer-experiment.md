# Washing-machine detection experiment v1 (synthetic)

Written and committed before implementation and before any result.

**Question.** Using aggregate power alone, can the existing simple models tell
when the simulated washing machine is running, and estimate its energy, in homes
where kettle-sized loads (1–3 kW for 1–5 min) share its heating power level
(about 2 kW for 10–15 min)? And does a longer feature window help separate them?

**Data (synthetic only).** No REFIT data is used, and House 5 stays retired.

- **Simulator:** every component v2, i.e. `realistic_sessions(..., washer='v2',
  fridge='v2', microwave='v2', background='v2')`.
- **Training:** 20 homes from `realistic_sessions(42, 20, …)`.
- **Evaluation:** 20 separate homes from `realistic_sessions(70042, 20, …)`.
  The seeds do not overlap.
- **Length:** each home is simulated for 36 h at 1 s, then every 16th reading is
  kept (8,100 readings, within the evaluator's 10,000 limit).
- **Washer start:** the first washer cycle starts at a uniform random time
  1–24 h in, using a new `washer_first_start` option. The default stays 2–10 min
  (the dashboard demo convenience), so every existing result reproduces. This
  keeps positive examples from always sitting at the start of a session, with
  a short background history. Most homes get one cycle; the next one is 36–120 h
  later.
- **Target:** `washing_machine` is on at 10 W or more (any stage). This is a
  one-output model, like the fridge-only models.

**Candidates (fixed; no tuning):**
- Background-relative features, the Step 11 feature choice (trailing 30-minute
  aggregate minimum, computed on the thinned readings), 16 s cadence, strict
  timing, seed 42.
- The unchanged always-off baseline, a depth-8 Decision Tree and a 40-tree
  depth-12 Random Forest.
- The one declared comparison is the window: **5 readings (64 s)** vs
  **30 readings (8 min)**.
- Every candidate is scored with `min_history=30`, so all score identical
  windows.

**Reporting.** Results are pooled over the 20 evaluation homes (confusion counts
and energy are summed, not averaged per home). Reported for each candidate:
- F1, precision, recall, accuracy, MAE, and measured vs estimated washer kWh.
- **Recall by washer stage** (fill, heat, wash, pause, drain, spin), from the
  simulator's saved stage.
- **The share of false positives that happen while unmetered load is 1 kW or
  more,** i.e. during kettle-like confusion.

**Decision rule (descriptive only; nothing is promoted).** "The longer window
helps" only if both the Decision Tree and the Random Forest gain at least 0.05
F1 at window 30 compared with window 5, without a worse MAE. Otherwise the
result is reported as mixed or no help. One run; no re-running with other
settings.

**Outputs.**
- A summary in ignored `data/washer-experiment/v1.json`.
- For each candidate, evaluation home 1's report in `data/experiments/`, so the
  Step 14 dashboard can show its charts.
- The live model is not changed.

**Known limits.** The simulator is simplified: regular drum reversals, no
rinse or spin repeats, no time-of-day pattern, and one seed per split. Synthetic
results are **not** real-household accuracy; the Step 11 final test already
showed how far synthetic numbers can be from real ones.
