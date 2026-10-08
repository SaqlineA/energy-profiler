# Cross-house test: results

The protocol is in [cross-house-protocol.md](cross-house-protocol.md),
committed in `a3d7e41` before this run. It ran once, on 8 October 2026, with
no tuning before or after. The full numbers are stored in
`data/holdout/cross-house-v1.json` (local only, ignored by Git).

## Per held-out house (fridge, 16 s strict windows)

| Held-out house | Windows | Real F1 | Simulator F1 | Real MAE W | Simulator MAE W | Always-off MAE W | Real energy ratio | Simulator energy ratio |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 4,368 | **0.358** | 0.280 | 26.9 | 40.0 | **15.7** | 1.69 | 2.26 |
| 2 | 3,867 | 0.520 | **0.874** | 15.0 | **14.8** | 28.3 | 0.92 | 1.15 |
| 3 | 4,305 | 0.377 | **0.631** | 44.9 | 56.0 | **43.9** | 0.67 | 1.64 |
| 4 | 3,687 | 0.339 | **0.360** | 34.2 | 82.5 | **11.2** | 3.48 | 7.73 |
| 5 | 4,335 | 0.450 | **0.686** | **38.9** | 39.4 | 48.5 | 0.55 | 0.66 |
| **Mean F1** | | **0.409** | **0.566** | | | | | |
| **Range** | | 0.339–0.520 | 0.280–0.874 | | | | | |

"Real" is a Decision Tree trained on the other four houses. "Simulator" is the
frozen simulator v1 model, trained only on simulated homes. Always off scores
F1 0 everywhere. The energy ratio is the estimated fridge energy divided by the
true fridge energy, where 1.00 is perfect.

## Verdict (preregistered rules)

- **R1, transfer: does not transfer reliably.**
  - Real training beat Always off on both F1 and MAE in only **2 of 5** houses
    (Houses 2 and 5).
  - In Houses 1, 3 and 4 it found some fridge cycles (F1 above 0) but its
    power error was worse than predicting zero.
- **R2, simulator vs real: simulator advantage holds.**
  - The simulator model had the higher F1 in **4 of 5** houses (all but House
    1).
  - **Caveat:** this is an advantage in *detecting when the fridge is on*, not
    in *measuring how much power it uses*. The simulator's power error was the
    worst of the three models in Houses 1, 3 and 4. It overestimated House 4's
    fridge energy almost eightfold.

## What this means

- **One house misleads.** The same settings gave real-training F1 scores from
  0.339 to 0.520, depending only on which house was held out.
  - The development score of 0.781 on House 2 (trained on Houses 1, 3 and 4)
    sits far above every result here.
  - House 2's own score fell to 0.520 once House 5 was added to its training.
  - House 5's score rose from 0.297 to 0.450 once House 2 was added.
  - A single train/test split hides this sensitivity.
- **The simulator teaches timing better than scale.**
  - It reproduces the fridge's on/off rhythm well enough to beat real training
    at detection in most homes.
  - It does not match the power level in each home, so its watt and energy
    estimates can be badly wrong.
  - This suggests a next hypothesis: simulator pretraining for *when*, plus a
    small per-home calibration for *how much*. It needs its own preregistered
    test.
- **No model is ready for metering.** In 3 of 5 homes, predicting "always off"
  had lower power error than any model.

## Limits

These were stated before the run:
- House 2 chose the settings, and House 5 had been scored before. This
  measures how much results vary between homes; it is not a sealed test.
- Folds share training houses, so they are not independent trials.
- Each house contributes about 22 hours, with no seasonal coverage.
- Fridge truth is REFIT's Appliance1 fridge or fridge-freezer channel.

## Next

- **More homes:** repeat with more REFIT houses and longer slices.
- **Seal a fresh house** for the next final test.
- **Preregister the timing-plus-calibration idea** before testing it.
