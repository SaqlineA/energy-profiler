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

## Result (2026-09-27, run once, code at `3618205`)

- **Training:** 20 homes, 161,420–161,920 windows, of which **3,410 are
  washer-on (2.1%)**. The same positives were available to every candidate.
- **Evaluation:** 20 separate homes. Every candidate scored the same 8,071
  windows per home, 161,420 in total.
- **Energy:** measured washer energy was 11.79 kWh, from about one cycle per home.

| Candidate | F1 | Precision | Recall | Accuracy | MAE W | Estimated / measured kWh | FPs during ≥1 kW unmetered load |
|---|---:|---:|---:|---:|---:|---:|---:|
| Always off | 0.000 | — | 0.000 | 97.7% | 16.4 | 0.00 / 11.79 | — |
| Decision Tree, 5 readings (64 s) | 0.654 | 0.693 | 0.619 | 98.5% | 10.5 | 11.41 / 11.79 | 13% |
| Decision Tree, 30 readings (8 min) | 0.610 | 0.760 | 0.509 | 98.5% | 11.3 | 11.55 / 11.79 | 37% |
| **Random Forest, 5 readings** | **0.701** | 0.876 | 0.583 | 98.8% | **10.1** | 11.37 / 11.79 | 26% |
| Random Forest, 30 readings | 0.623 | 0.890 | 0.479 | 98.6% | 10.3 | 11.51 / 11.79 | 38% |

**Recall by washer stage (share of "on" windows found):**

| Candidate | Fill | Heat | Wash | Drain | Spin |
|---|---:|---:|---:|---:|---:|
| DT w5 | 0.44 | 0.74 | 0.64 | 0.30 | 0.45 |
| DT w30 | 0.25 | 0.80 | 0.49 | 0.12 | 0.22 |
| RF w5 | 0.36 | 0.77 | 0.57 | 0.25 | 0.44 |
| RF w30 | 0.16 | 0.77 | 0.44 | 0.09 | 0.30 |

The pause stage (2 W) is below the 10 W "on" threshold, so it is not a target.

**Preregistered verdict: the longer window does not help; it hurt.** F1 fell
for both models (DT 0.654 → 0.610, RF 0.701 → 0.623). Recall dropped in every
stage except heating. More of the remaining false positives happened during
kettle-sized loads (13–26% → 37–38%), which is the opposite of what was expected.

**What this means:**
- **Accuracy is misleading here.** Always-off reaches 97.7% because the washer
  is on only about 2% of the time. F1, recall and energy are the useful measures.
- **The best synthetic candidate is RF with 5 readings:** F1 0.70, 88% precision,
  58% recall, pooled energy 3.6% low. It finds about three quarters of heating
  windows and just over half of wash windows. The low-power fill and drain stages
  are mostly missed.
- **Pooled energy looks close (within 2–4%) partly because errors cancel across
  homes.** Home 1's reports show individual errors of up to about 11%.
- **Why the longer window hurt is unknown.** Possible reasons, all untested:
  - A 30-reading summary (mean, max, min over 8 min) blurs the moment the washer
    starts and stops.
  - The 8-minute window overlaps more other loads.
  - The trees split on different features.

  Nothing was re-run to find out.

**Limits.**
- This is synthetic evaluation on the same simulator family used for training.
- The Step 11 final test showed synthetic-trained scores can fall a long way on
  a real home (fridge: 0.69 synthetic-trained vs real-house results).
- There is one seed per split.
- No candidate is promoted; the live model is unchanged; House 5 and all REFIT
  data were untouched.

**A real check is still possible, but would need its own preregistration.**
REFIT Houses 1–4 have labelled washer channels (see
[washing-machine-profile.md](washing-machine-profile.md)) and could serve as a
first real test of washer detection. Those houses have already been inspected,
so it would be development evidence, not a final test.

Home 1's report for each candidate is in the dashboard under **Other
experiments → "Washer v1 / … / sim home 1"**.
