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
