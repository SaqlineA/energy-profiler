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

## v3 result (2026-09-26): mixed; the failure mode changed but detection was not fixed

Run once. The same 4,368 training windows (886 on / 3,482 off) and the same 3,867
House 2 windows (1,256 on / 2,611 off) with 57,744 s of energy coverage as v2.

| Random Forest | F1 | Accuracy | MAE W | Estimated / measured kWh | TP / FP / FN / TN |
|---|---:|---:|---:|---|---|
| v2 (absolute summary) | 0.406 | 28.55% | 52.61 | 0.960 / 0.453 | 945 / 2,452 / 311 / 159 |
| v3 (relative) | 0.181 | 70.70% | 21.97 | 0.143 / 0.453 | 125 / 2 / 1,131 / 2,609 |
| Always off (reference) | 0.000 | 67.52% | 28.34 | 0 / 0.453 | 0 / 0 / 1,256 / 2,611 |

The v3 Decision Tree scored F1 0.282, accuracy 71.53%, MAE 19.94 W and
0.174 / 0.453 kWh. No candidate is selected on the basis of this.

**What changed.** False positives almost disappeared, falling from 2,452 to 2.
This fits the hypothesis: v2's flood of "on" predictions was driven by House 2's
absolute load level. For the first time, a learned model beats always-off on
accuracy and MAE, though only narrowly (70.7% vs 67.5%, and 22.0 vs 28.3 W).

**What did not.** Recall fell from 75% to 10%. The model now misses about nine in
ten fridge-on windows and underestimates energy by about 68%. The absolute energy
error is smaller (0.31 kWh vs 0.51 kWh), but only because it went from roughly
double to roughly a third of the true value. F1 fell from 0.406 to 0.181.
No window passes the uncertainty heuristic.

**Verdict: mixed.** It is not a usable detector and should not be called an
improvement. The evidence supports part of the hypothesis: absolute wattage
caused the false positives. Removing it does not reveal a fridge signal that
transfers between houses. Possible reasons, all untested: the fridges differ in
power and cycle pattern, a 30-minute minimum is sometimes a poor background, or
64-second windows at 16 s rarely capture a clear switch-on step. v3 is not
adjusted further. House 5 remains unscored.

# Fridge-only development protocol v4: multi-house training

Written and committed before Houses 3 and 4 were downloaded or inspected.

**Question.** Does training on several households improve cross-house
generalization to House 2?

**Data.**
- **Training:** the frozen House 1 slice from split-v1, plus the first 10,000
  cleaned readings of REFIT House 3 and House 4, downloaded as byte-range
  prefixes in the same way as Houses 1, 2 and 5.
- **Development:** House 2 only.
- **House 5:** stays reserved. Its hash is checked, but it is never parsed or scored.
- **Fridge channels,** from NILMTK REFIT metadata (NILMTK meter N = REFIT
  Appliance(N−1)): House 3 uses Appliance2 (fridge-freezer) and House 4 uses
  Appliance1 (fridge).
- **Known confound:** House 3 also has a separate freezer (Appliance3). House 4
  also has a freezer (Appliance2) and a fridge-freezer (Appliance3). Their cycles
  appear in the household total without a label, so they may look like
  "unexplained" fridge-like load.
- **Houses stay separate.** Each house is its own training session, so a feature
  window never crosses from one house into another.

**Fixed settings.** v2 thinning (16 s), strict timing, five-reading windows, the
always-off / Decision Tree / Random Forest candidates unchanged, seed 42, a 20 W
threshold, and the same metrics. Two runs are declared in advance, with no others:
- v4 (summary features): compared with v2.
- v4r (relative features): compared with v3.

Together these show whether adding houses helps with either feature set.

**Inclusion check before training.** This is the same timing and fridge-profile
inspection used earlier. A new house is included only if its thinned 16 s data
yields at least 100 fridge-on and 100 fridge-off training windows. A house that
fails is documented and excluded; it is not swapped for another house under
this protocol.

**Reporting.** F1, accuracy, MAE, predicted vs measured energy, the confusion
matrix and training support. Whatever the result, House 5 is not scored in
Step 10, and Step 10 ends with this experiment.

## v4 data preparation and inclusion check (2026-09-26)

```powershell
curl.exe -4 -L --fail --max-time 60 --range 0-1499999 --max-filesize 1500000 "https://zenodo.org/api/records/5063428/files/CLEAN_House3.csv/content" --output data/refit/house3-prefix.part
python research/save_refit_sample.py data/refit/house3-prefix.part data/refit/house3-first-10000.csv
python prepare_recording.py data/refit/house3-first-10000.csv data/refit/house3-replay-10000.csv --timestamp Unix --timestamp-format unix --mains Aggregate --refrigerator Appliance2 --limit 10000 --origin "REFIT House 3 fridge-freezer channel 2 (NILMTK meter 3); Zenodo 5063428; training partition v4"
# House 4: same commands with House4 and --refrigerator Appliance1 (fridge, NILMTK meter 2).
python fridge_development.py --protocol v4
python fridge_development.py --protocol v4r
```

The normalized SHA-256 hashes are pinned in `fridge_development.EXTRA_TRAINING`.
House 3 is `7a6d59ab…`, and House 4 is `e371a1c4…`. The runner also rejects
any exact measurement shared between the training files and House 2.

| House | Common intervals (s) | 16 s windows (on / off) | Fridge on W (p50) | On / off cycle (min, p50) | Household total rise at fridge switch-on (p50) |
|---|---|---|---:|---|---:|
| 1 | 1, 2, 13, 14 | 886 / 3,482 | 76 | 28 / 115 | 32 W |
| 3 | 7, 6, 5 | 1,765 / 2,540 | 99 | 40 / 73 | 0 W |
| 4 | 2, 1, 3, 12 | 799 / 2,888 | 51 | 0.4 / 10* | 0 W |
| 2 (development) | 7, 8 | 1,256 / 2,611 | 85 | 26 / 63 | 86 W |

\*House 4's small fridge often dips across the 20 W threshold, which splits its
cycles. Its p90 on cycle is 24 min. Both new houses pass the inclusion rule,
so no house was excluded. Houses 1, 3 and 4 all show a small household-total
rise when their fridge switches on. House 2 is the only house where the total
clearly tracks the fridge channel. The cause is still unexplained.

## v4 result: more houses help the relative features, not the absolute ones

The two declared runs were each run once. Both use the same 3,867 House 2
windows (1,256 on / 2,611 off) and 57,744 s of energy coverage. Training has
12,360 windows across three houses (3,450 on / 8,910 off).

| Run | Features | Training houses | Model | F1 | Accuracy | MAE W | Est. / measured kWh |
|---|---|---|---|---:|---:|---:|---|
| v2 | summary | 1 | RF | 0.406 | 28.55% | 52.61 | 0.960 / 0.453 |
| v4 | summary | 1, 3, 4 | RF | 0.132 | 66.02% | 28.14 | 0.108 / 0.453 |
| v4 | summary | 1, 3, 4 | DT | 0.095 | 64.37% | 28.60 | 0.101 / 0.453 |
| v3 | relative | 1 | RF | 0.181 | 70.70% | 21.97 | 0.143 / 0.453 |
| v4r | relative | 1, 3, 4 | RF | 0.439 | 75.41% | 19.70 | 0.303 / 0.453 |
| v3 | relative | 1 | DT | 0.282 | 71.53% | 19.94 | 0.174 / 0.453 |
| v4r | relative | 1, 3, 4 | DT | **0.781** | **87.12%** | **14.76** | **0.386 / 0.453** |
| — | — | — | Always off | 0.000 | 67.52% | 28.34 | 0 / 0.453 |

**Summary features (v4 vs v2):** adding houses removed most false positives but
left an almost always-off model. F1 is 0.13, with no better accuracy or MAE
than always-off. Absolute-watt features still do not generalize.

**Relative features (v4r vs v3):** adding houses improved every metric for both
models. The Random Forest now finds 30% of on windows (up from 10%) with 67
false positives. The Decision Tree finds 71% of on windows with 128 false
positives. It is the first candidate clearly better than always-off on every
metric, and it underestimates energy by about 15%.

**Answer: yes, with background-relative features.** Training on several
households improved generalization to House 2. With absolute watts, it did not.

**Caveats:**
- This is one development house and one seed.
- The Decision Tree beating the Random Forest by this much (0.78 vs 0.44 F1) is
  unexplained, and it could be seed or house luck. The tree has a shallower
  depth and a larger minimum leaf, which may simply generalize better.
- No window passes the uncertainty heuristic (certain_samples = 0).
- House 2 has now been used for five comparisons, so it is development
  evidence, not a final test.
- House 4's extra freezer and fridge-freezer, and House 3's separate freezer,
  are unlabeled load.

No candidate was promoted, the live model is unchanged, and House 5 remains
unscored. This concludes Step 10. Step 11 should declare its choice from this
evidence (for example, v4r Decision Tree vs v4r Random Forest), compare it with
the synthetic-trained system, and only then score House 5 once.
