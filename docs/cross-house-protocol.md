# Cross-house test: protocol (preregistered)

Written and committed **before** the experiment runs. It runs once. Whatever
it shows is recorded in `docs/cross-house.md`, including failures.

## Why

The House 5 test gave two surprises from a single house:
- **Real training dropped:** the real-trained Decision Tree fell from F1 0.781
  on House 2 to 0.297.
- **The simulator did better:** a simulator-trained tree reached 0.686.

A single house can't tell a general pattern from a quirk of that house. This
test rotates the held-out house through every REFIT house already
downloaded.

## Questions

1. **Transfer:** does training on real homes transfer to an unseen home in
   general, or only to some homes?
2. **Simulator vs real:** was "simulator beats real" on House 5 a general
   pattern or a one-house exception?

## Data (unchanged files, checked by SHA-256)

REFIT Houses 1, 2, 3, 4 and 5. Each is the existing 10,000-reading slice
(about 22 hours) with fridge truth from Appliance1:
- Houses 1 and 2 are pinned in `data/refit/split-v1.json`.
- Houses 3 and 4 are pinned in `fridge_development.EXTRA_TRAINING`.
- House 5 is pinned as the spent final test.

No new data is downloaded for this test.

## Method (frozen; no tuning)

**Settings:** the same as the preregistered v4r final-test model:
- 16-second label-blind thinning;
- background-relative features;
- strict timing;
- a fridge-only target.

**Each fold:** hold out one house *k*. Train the Decision Tree on the other
four houses (one session per house). Score three models on house *k*, all on
identical windows:
- **Real:** the Decision Tree trained on the four real houses.
- **Simulator:** the frozen House 5 simulator model, a Decision Tree trained
  on `realistic_sessions(42, 10, 1800)` (simulator v1, unchanged).
- **Always off:** the no-skill baseline.

**Recorded per fold:**
- F1, precision, recall and power MAE (W);
- the estimated / true fridge energy ratio;
- the window count.

## Decision rules (fixed now)

- **R1, transfer:**
  - **Holds:** real training beats Always off on *both* F1 and MAE in at least
    4 of the 5 held-out houses.
  - **Does not transfer reliably:** it does so in 3 or fewer.
- **R2, simulator vs real:**
  - **Simulator advantage holds:** the simulator's F1 is higher than real
    training's in at least 4 of 5 houses.
  - **House 5 was an exception:** the simulator is higher in 0 or 1 houses.
  - **Mixed, no general claim:** the simulator is higher in 2 or 3 houses.
- **Summary:** the mean, minimum and maximum F1 per model across the five
  houses. **The spread is the headline result.**

## Known limits, stated in advance

- **Not a sealed test:**
  - House 2 was used to choose these settings.
  - House 5 has been scored before.
  - So this measures how much results vary between homes; it is not a fresh
    final test.
- **Folds are not independent:** they share training houses, so 5 folds are
  not 5 independent trials.
- **Small slices:** about 22 hours per house; daily and seasonal patterns are
  not covered.
- **Approximate truth channel:** Appliance1 is a fridge or fridge-freezer
  channel, mapped to "refrigerator" as in earlier work.
- **Weak simulator test for House 5:** House 5's fridge statistics never
  shaped the simulator v1, but the House 5 fold of R2 repeats the earlier
  result, so it is not new evidence on its own.

## Correction (8 October 2026, after the run)

The data section above says fridge truth comes from Appliance1 in every house.
That is wrong for House 3. As documented in `docs/fridge-development.md`, House
3's pinned file uses **Appliance2**, its fridge-freezer. The runner always used
the pinned, hash-checked files, so the results are unaffected. Only this
description was wrong. The text above is left unchanged as the preregistered
record.
