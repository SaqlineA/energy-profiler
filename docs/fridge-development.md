# Fridge-only development protocol v1

Fixed before running this comparison: train only on the frozen House 1 slice,
evaluate only on House 2. Verify the split manifest and recording hashes first.
House 5 may be hashed for integrity but must never enter parsing for training,
features, prediction, candidate selection or plotting in this runner.

Use refrigerator threshold 20 W, five trailing readings, summary features,
eight-second cadence, seed 42 and the existing strict timing rules. Compare the
unchanged always-off, depth-8 Decision Tree and 40-tree/depth-12 Random Forest
settings. No resampling, interpolation, hyperparameter sweep or label filling.
All candidates must score the same timestamps. Record on/off support, F1, MAE,
energy error and observed coverage; irregular intervals exclude windows.

This is development evidence, not a final test. Do not automatically select or
promote a candidate. Missing lamp/microwave labels stay unknown; the output is
one refrigerator category, not full-home disaggregation. The residual-based
uncertainty heuristic was designed for the three-device model and is conservative
but not calibrated for this one-device experiment; raw scores precede abstention.
Short slices, upstream cleaning and different refrigerator/freezer types limit
generalization. No live model files are written.

## Run

```powershell
python fridge_development.py
```

The default manifest is `data/refit/split-v1.json`. Saved reports appear under
**Experiments → Refresh history → Fridge dev v1 / ... / House 2** on the machine
running the command. Recordings and reports are not uploaded by Git.
Scikit-learn's [classifier](https://scikit-learn.org/stable/modules/generated/sklearn.multioutput.MultiOutputClassifier.html)
and [regressor](https://scikit-learn.org/stable/modules/generated/sklearn.multioutput.MultiOutputRegressor.html)
wrappers preserve the evaluator's per-device output shape for one target.

## Result: insufficient training data, no candidate selected

Only **8 of 10,000 training readings** ended compatible labeled windows; all
eight were fridge-off. House 1's most common intervals are 1, 2, 13 and 14 seconds,
so the declared strict eight-second policy rejects almost all five-reading windows.
This is not fixed by changing the playback speed or pretending timestamps differ.

All three candidates scored the same 3,829 development windows (38.29% of the
10,000 input readings), with 1,225 on and 2,604 off labels. Window spans are
28–33 seconds under the existing ±20% per-interval tolerance. Matched energy
coverage is 20,744 seconds, not the full recording duration.

| Candidate | F1 | Accuracy | MAE W | Estimated / measured kWh |
|---|---:|---:|---:|---|
| Always off | 0.000 | 68.01% | 27.95 | 0 / 0.16076 |
| Decision Tree | 0.000 | 68.01% | 27.95 | 0 / 0.16076 |
| Random Forest | 0.000 | 68.01% | 27.95 | 0 / 0.16076 |

These are diagnostic failures, not successful models: all predict off, miss all
1,225 on cases, and have zero predictions passing the current uncertainty heuristic.
Reports expose training on/off support, set `training_eligible: false` when either
class is absent, and lead with an insufficient-training warning. Both classes are
a necessary condition, not a sufficient sample-size or deployment-quality guarantee.
Initial pilot reports without the new warning are superseded by the reports that
include `training_eligible` and `train_class_support` metadata.

House 5 remains unscored. No thresholds or hyperparameters were tuned on it; the
live model was not replaced. Next, revise the data-acquisition protocol to obtain
a training recording with enough naturally compatible on/off windows (or explicitly
design and validate a separate resampling policy). Preserve the v1 split and its
failure evidence; do not silently overwrite it or relax timing to improve scores.

# Fridge-only development protocol v2: label-blind 16 s thinning

v1 stays as recorded above; its reports and the split-v1 recordings are unchanged.
v2 reuses the same frozen files (hashes verified) and changes only sampling:
`sources.thin_to_cadence` keeps the first real reading at least 12.8 s (0.8 × 16)
after the previous kept one, skipping missing aggregates. It decides from
timestamps only, never changes or creates values, and is then followed by the
same strict checks (±20% intervals, reset after gaps over 24 s). Because it is
label-blind, House 5 can later be thinned the same way without being inspected.

Why 16 s: House 1 arrives in bursts (intervals of 1–2 s then 12–14 s), so almost
no consecutive readings are 8 s apart; pairs of intervals add up to about 15 s.
Thinned window counts were compared for 8–20 s on Houses 1 and 2 only,
before any model was fitted. 15 and 16 s retained similar coverage, and 16 s was
chosen as a round multiple of v1's 8 s. The House 1 on/off label counts were
visible during that check. No model scores were used to pick the cadence.
Thinning is instantaneous subsampling: short events between kept readings can be
missed, and energy is integrated from fewer points.

```powershell
python fridge_development.py --protocol v2
```

## v2 result (2026-09-26): training support fixed, candidates fail on House 2

Training now has 4,368 windows (886 on / 3,482 off; `training_eligible: true`).
All candidates scored the same 3,867 House 2 windows (1,256 on / 2,611 off),
spanning 52–70 s, with 57,744 s of matched energy coverage.

| Candidate | F1 | Accuracy | MAE W | Estimated / measured kWh |
|---|---:|---:|---:|---|
| Always off | 0.000 | 67.52% | 28.34 | 0 / 0.4532 |
| Decision Tree | 0.400 | 30.39% | 52.60 | 0.9487 / 0.4532 |
| Random Forest | 0.406 | 28.55% | 52.61 | 0.9601 / 0.4532 |

The learned models predict "on" most of the time in House 2 (Random Forest:
2,452 false positives, 159 true negatives). They find about 75% of the on
windows, but their accuracy and MAE are worse than always-off and they
overestimate energy by about 2.1×. No window passes the uncertainty heuristic.
So the data blocker is solved, but a House 1 model does not transfer to House 2
with raw-watt summary features. A likely cause is the difference in background
load between houses. This is a hypothesis, not a finding.
No candidate is selected or promoted; House 5 remains unscored.

Next (still development-only): declare one fixed change in advance and compare
it on House 2 against these v2 numbers. For example, add baseline-relative
features that do not depend on each house's absolute load. Record every
attempt, because repeated House 2 comparisons make it progressively less
independent.

# Fridge-only development protocol v3: background-relative features

Written and committed before implementation or any v3 result.

**Hypothesis.** The model relies too heavily on absolute household wattage, so
differences in background consumption between houses hurt generalization.

**Single change.** Replace the `summary` features with `relative` features. Everything
else stays as in v2: House 1 training, House 2 development, the same 16 s thinning,
strict timing, five-reading windows, the same three candidates, seed 42, a 20 W
threshold and the same metrics. The House 2 windows scored are identical to v2's,
because the background never adds a scoring requirement.

**Background.** For each reading, take the minimum real aggregate watts among
thinned readings in the trailing 30 minutes (from t − 1800 s, excluding it, up to
and including t). It uses aggregate power and past readings only, never
refrigerator labels or future readings. Gaps are not filled, and near the start
of a recording less history is available.
30 minutes is a fixed assumption, chosen so the window usually covers some
fridge-off time. It is not tuned, and a fridge that runs for longer than 30
minutes would raise the background.

**Features** (six, the same count as `summary`, with no absolute watts):
current − background, current − previous, window mean − background,
window standard deviation, window max − min, and the largest absolute step
within the window.

**Decision rule.** Compare the v3 Random Forest with the committed v2 Random Forest
(F1 0.406, accuracy 28.6%, MAE 52.6 W, 0.960 / 0.453 kWh). Report whether it
helped, hurt or made essentially no difference, and run it once. If it fails,
the next idea gets a new declared protocol, not a tweak to this one. House 5
stays unscored.
