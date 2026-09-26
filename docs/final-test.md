# Step 11: final House 5 evaluation, protocol v1

Written and committed before House 5 was parsed, plotted or scored.

**Research question.** Does training on multiple real households with
background-relative features generalize better to an unseen household than a
model trained on synthetic appliance behaviour?

## Frozen choices

- **House 5 data:** the reserved split-v1 slice
  (`data/holdout/house5-replay-10000.csv`, SHA-256 `813ff846…`) with its
  `Appliance1` refrigerator mapping. It is thinned with `thin_to_cadence(16 s)`,
  followed by the trailing 30-minute background, exactly as in v4r.
- **Real-data candidate (chosen from the House 2 evidence):** the v4r Decision
  Tree (depth 8, minimum leaf 5, seed 42), trained on Houses 1, 3 and 4 with
  relative features, 16 s cadence, five readings and strict timing. Retraining is
  deterministic and must reproduce model version `92d52feba60f9800`, the same
  model that scored F1 0.781 on House 2. The run aborts if the version differs.
  It was chosen over the v4r Random Forest because the tree was better on every
  House 2 metric (F1 0.781 vs 0.439, MAE 14.8 vs 19.7 W, energy 0.386 vs
  0.303 / 0.453 kWh).
- **Synthetic comparator:** the same Decision Tree settings, relative features
  and fridge-only output, but trained on the research simulator
  (`realistic_sessions(42, 10, 1800)`, the cadence-v1 training seed). Each
  session is subsampled to every 16th one-second reading, as in the cadence
  protocol, so only the training data differs.
  The live model `3132ae99ccd11d4c` is **excluded from the scored comparison**.
  It was trained on one-second windows, and under strict timing it produces
  zero windows on 16 s data. Scoring it would need a different timing policy on
  different windows.
- **Baseline:** always-off.
- **Same windows:** all three are scored on identical House 5 timestamps. The
  run aborts otherwise.

## Failure criteria (decided now)

The real-data candidate **passes** only if all three hold on House 5:

1. F1 is higher than the always-off F1.
2. MAE is lower than the always-off MAE.
3. Estimated fridge energy is between 0.5× and 1.5× the measured energy.

It is **better than synthetic** only if its F1 is higher, its MAE is lower and
its energy ratio is closer to 1.0 than the synthetic comparator's. Anything
else is reported as mixed or worse, exactly as measured.

## Process rules

- `final_test.py` runs once. It writes `data/holdout/final-test-v1.json` and
  refuses to run again if that file exists.
- Nothing is tuned, reselected or re-thresholded afterwards. A bad result is
  still the result.
- Reports record F1, precision, recall, accuracy, MAE, and measured and
  estimated fridge kWh, plus support and coverage.
- The live model is not replaced. After this, House 5 is no longer untouched,
  and any later iteration needs new, independent final data.

## Result (2026-09-26, run once, code at `417dd81`)

All three models scored the same 4,335 House 5 windows (1,956 on / 2,379 off),
with 60,720 s of energy coverage. The real-data model reproduced the
preregistered version `92d52feba60f9800`. The full result is in
`data/holdout/final-test-v1.json`, which is local and ignored by Git. The
dashboard reports are named `FINAL House 5 / …`.

| House 5 | F1 | Precision | Recall | Accuracy | MAE W | Measured kWh | Estimated kWh (ratio) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Real v4r Decision Tree (Houses 1, 3, 4) | 0.297 | 0.557 | 0.202 | 56.75% | 38.92 | 0.819 | 0.480 (0.59×) |
| Synthetic Decision Tree (simulator) | **0.686** | **0.769** | **0.620** | **74.44%** | 39.38 | 0.819 | 0.539 (0.66×) |
| Always off | 0.000 | — | 0.000 | 54.88% | 48.46 | 0.819 | 0 (0×) |

Confusion matrices (TP / FP / FN / TN): real 396 / 315 / 1,560 / 2,064;
synthetic 1,212 / 364 / 744 / 2,015; always-off 0 / 0 / 1,956 / 2,379.

**Preregistered verdict:**
- **The real-data candidate passes, narrowly.** F1 0.297 beats 0, MAE 38.9 W
  beats 48.5 W, and its energy ratio of 0.59 is inside the 0.5–1.5 range.
- **It is not better than synthetic.** The synthetic model had higher F1
  (0.686 vs 0.297), recall, precision and accuracy, and its energy ratio is
  closer to 1 (0.66 vs 0.59). The real model's MAE is lower only by 0.5 W.

**Answer to the research question: no.** On this unseen household, training on
multiple real households did not generalize better than training on the
research simulator. Both used the same background-relative Decision Tree. Both
models underestimate fridge energy by 34–41%.

## Interpretation (after the fact; nothing tuned)

- **The House 2 score did not carry over.** The real model dropped from F1 0.781
  on House 2 to 0.297 on House 5, and recall fell from 71% to 20%. Choosing a
  model after five comparisons on a single development house overestimated its
  quality. House 2 is also the only house where the household total clearly
  tracks the fridge channel, so it may have been an unusually easy house.
- **The real training houses carry a weak switch-on signal.** In Houses 1, 3 and
  4, the household total barely changes when the fridge starts, so the real
  model may have learned to expect small, hard-to-see fridge signatures. The
  simulator's clean, large switch-on steps may match House 5 better. This is
  a hypothesis only; House 5's behaviour was not profiled before scoring.
- **Relative features did the most work.** The synthetic model's features were
  designed during real-data development (v3), so the comparison is between
  training data under one shared feature design, not between two independent
  systems. The live one-second model was excluded; see the frozen choices above.
- **The limits are real:** one final house, one seed, a 10,000-reading slice
  (about 17 hours), a single appliance category, and nothing passing the
  uncertainty heuristic. None of this is validation for real-world deployment.

House 5 is no longer untouched. Any further model iteration needs new,
independent final data. The live model (`3132ae99ccd11d4c`) is unchanged.
