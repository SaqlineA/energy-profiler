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
