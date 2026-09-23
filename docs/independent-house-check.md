# Independent-house REFIT checkpoint

The frozen model `fea34356acf733a8` was evaluated on 10,000 complete readings
from REFIT House 2, without retraining or promotion. This advances the next
research task after the [House 1 check](extended-refit-check.md).

## Provenance and timing

Source: [REFIT on Zenodo](https://zenodo.org/records/5063428), `CLEAN_House2.csv`.
Downloaded a 1,500,000-byte prefix; the published whole-file checksum cannot
validate this partial download. Channel 1 was cross-checked against the authors'
[seq2point REFIT mapping](https://github.com/MingjunZhong/seq2point-nilm/blob/master/dataset_management/refit/create_dataset.py).
This **fridge/freezer** channel is mapped to our refrigerator category for a
stress test, not treated as an identical simulated appliance. Lamp/microwave
truth remain unknown. Upstream cleaned data may already include imputation.

Normalized SHA-256: `8ee9745d08e25ca4626924669bcb41c013ba59f542223fb205b6953838e5fd34`.
Range: 2013-09-17 22:08:11 UTC to 2013-09-18 15:31:32 UTC. Intervals range
from 1 to 1,811 seconds; 14 exceed 16 seconds. Those gaps reset history and
are excluded from integration. No readings were invented to fill gaps.
Data and detailed reports stay local and ignored by Git.

## Frozen sample-window diagnostic

| Measure | Refrigerator category |
|---|---:|
| Scored / input rows | 9,941 / 10,000 |
| On / off truth | 3,340 / 6,601 |
| Accuracy | 86.45% |
| Precision / recall | 72.77% / 95.36% |
| F1 | 0.825 |
| Power MAE / RMSE | 40.38 W / 64.26 W |
| Zero-watt baseline MAE, identical scored rows | 29.26 W |
| Certain predictions | 3,027 / 9,941 |
| Matched energy coverage | 59,013 seconds |
| Measured / estimated energy | 0.46859 / 1.06390 kWh |
| Absolute energy error | 0.59531 kWh |

Confusion counts: TP 3,185, FP 1,192, FN 155, TN 5,409. Metrics score raw
outputs before abstention. Zero-watt baseline F1 is zero: low power error alone
does not mean useful detection. Estimated energy is about 127% too high.

**Strict timing evaluation produces zero compatible windows**, not zero error.
Diagnostic five-reading windows span 4–41 seconds versus four seconds in
training. Better F1 than House 1 reflects a different recording, not an improved
model. This is evidence of domain sensitivity, not proof of generalization,
complete daily coverage or live metering accuracy.

## Reproduce

After obtaining the prefix from the source above:

```powershell
python research/save_refit_sample.py data/refit/house2-prefix.part data/refit/house2-first-10000.csv
python prepare_recording.py data/refit/house2-first-10000.csv data/refit/house2-replay-10000.csv --timestamp Unix --timestamp-format unix --mains Aggregate --refrigerator Appliance1 --limit 10000 --origin "REFIT House 2 fridge/freezer channel 1; Zenodo 5063428"
python experiments.py data/refit/house2-replay-10000.csv --cadence 8 --policy strict
python experiments.py data/refit/house2-replay-10000.csv --cadence 8 --policy sample_window
```

Next: freeze a cadence-aware evaluation protocol before tuning. Reserve House 2
as a holdout; compare simple baselines and Random Forest on disjoint training
sessions at target cadence, reporting activity and energy errors together.
Do not promote a model based on this already-inspected prefix alone.
Physical sensing and hardware validation remain deferred.
