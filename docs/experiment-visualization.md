# Experiment visualization (Step 14)

The **Experiments** section of the dashboard explains saved results to someone
who does not know ML. It reads existing reports only. No experiment was rerun,
and House 5 was not scored again.

## What was added

- **Grouped report picker.** The groups are *Final test (held-out house, scored
  once)*, *Development (House 2)* and *Other experiments*. Key groups show the
  newest report per name, and every option says what the model was trained and
  tested on. For example:
  `FINAL House 5 — Synthetic-trained Decision Tree · trained on synthetic data, tested on real data`.
- **Data-source badges.** *TESTED ON REAL DATA* or *SYNTHETIC DATA*, and
  *TRAINED ON REAL DATA*, *SYNTHETIC DATA*, or *BASELINE · NO TRAINING*.
  Real data is green; synthetic data is purple.
- **Summary card.** It shows the dataset, model, training houses, appliance,
  F1, MAE, and actual vs. predicted energy.
- **Plain-language explanation.** It is generated from the saved metrics by
  `experiment_routes.describe()`, which has a Python test. For the House 5
  real-trained model it reads: *"The model detected some refrigerator activity
  but missed many ON periods (20% found). 44% of its ON predictions were false
  alarms. It underestimated total refrigerator energy by 41%."*
- **Three charts,** described below.

## What each graph means

1. **Was it on? (ON/OFF strip).** The top row shows when the appliance was
   actually on (measured watts at or above the report's threshold, 20 W for
   the fridge). The bottom row shows when the model said it was on (its raw
   prediction, the same value the metrics score). Matching bars mean a caught
   cycle. A text line counts the ON periods. House 5 has 36 actual ON periods;
   the real-trained model predicted 257 short bursts, and the synthetic-trained
   model predicted 211.
2. **Power: actual vs. predicted.** The solid line is measured watts and the
   dashed line is the model's estimate, on the recording's real timeline.
   Gaps are not joined.
3. **Prediction error.** Each point shows *predicted − actual*. Orange above zero
   means an overestimate; blue below zero means an underestimate. The line above
   the chart gives the average error and how often each happens. For House 5, the
   real-trained model underestimates during fridge ON cycles and overestimates
   between them.

The power and error charts scale to the 99th percentile, so a single startup
spike (for example 1,287 W) cannot flatten everything else. The page says how
many readings were drawn at the edge.

## Verification (2026-09-26)

For all three House 5 reports, values recomputed from the raw report points
matched the page:
- Predicted-ON readings equal TP + FP (711, 1,576 and 0).
- Actual-ON readings equal the positive support (1,956).
- MAE recomputed from *predicted − actual* equals the saved MAE, which confirms
  the error sign.
- Every measured and estimated reading is plotted.
- The ON-run counts match an independent count.

Layout was checked at 375, 768 and 1,440 CSS px, with no page-level horizontal
overflow, in both light and dark mode. On narrow screens each chart scrolls
sideways inside its own box, with a minimum width of 560 px. The page itself does
not scroll sideways.

## Known limitations

- Chart labels are drawn inside the SVG, so on a phone they are small (about
  8 px) even with sideways scrolling.
- Chart surfaces stay white in dark mode, matching the existing chart.
- The explanation wording uses fixed bands (80% and 50% recall, 80% precision,
  ±20% energy). These describe the result; they are not pass/fail criteria. The
  preregistered House 5 criteria are in [final-test.md](final-test.md).
- Data sources are inferred from report metadata: the house number, a REFIT name
  or training-source text. Older reports without that metadata may be labelled
  by name only.
- The ON/OFF strip uses raw predictions before the uncertainty heuristic.
  Dashed estimates in the power chart can be uncertain.
- The detail view loads up to 10,000 points per report, so very large reports
  are truncated, and the page says so.
- Everything is local: reports live in ignored `data/experiments/` and are not
  in Git or Codespaces.
