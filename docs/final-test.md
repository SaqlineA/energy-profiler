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
