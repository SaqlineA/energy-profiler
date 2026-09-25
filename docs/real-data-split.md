# Real-data split protocol v1

Declared before retrieving or scoring the final-test slice:

| Role | REFIT house | Original data rows | Use |
|---|---:|---|---|
| Training | 1 | First 10,000 | Fit experimental fridge models |
| Development | 2 | First 10,000 | Compare candidates and choose settings |
| Final test | 5 | First 10,000 | Score once after choices are frozen |

House 1 and House 2 have already been inspected. Neither is an untouched final
test. House 5 is chosen in advance, not selected for a favorable score. Its
measurements may be parsed to validate integrity, but no plots, label summaries
or predictions are inspected during this milestone. This is a process boundary,
not filesystem access control; do not upload the final slice into the dashboard
while tuning.

Use `Aggregate` watts and `Unix` timestamps. Appliance1 is the mapped refrigerator
category; it can represent a fridge/freezer rather than an identical refrigerator
across houses. House 2/5 channel 1 is cross-checked against the research authors'
[REFIT mapping](https://github.com/MingjunZhong/seq2point-nilm/blob/master/dataset_management/refit/create_dataset.py).
House 1 follows the mapping documented in our earlier REFIT investigation.
The [source download record](https://zenodo.org/records/5063428) describes cleaned
aggregate and appliance watts. Upstream imputation remains a limitation.

Keep all original timestamps, missing values and gaps. Do not interpolate to
manufacture regular eight-second windows. Later training and evaluation must
use the same strict cadence rules, report retained-window/energy coverage, and
reset history at each recording boundary. Only fridge labels are available in
these normalized slices; do not train the existing three-output model by filling
missing lamp/microwave labels with zeros.

The first 10,000 readings are a bounded learning exercise, not a representative
season or population. Once final results have been seen, they cannot be used to
tune and still be called an untouched test. Freeze a new protocol and reserve
new independent data for the next iteration. Hardware validation remains separate.

## Frozen local recordings (2026-09-25)

All three normalized files contain 10,000 readings. House 5 is stored under
`data/holdout/`, outside dashboard experiment storage; it has not been scored.
Only a 1,500,000-byte source prefix was downloaded. The published checksum of
the full source file cannot validate that partial download. Our manifest hashes
identify the normalized slices, not a cryptographically authenticated dataset.

The manifest `data/refit/split-v1.json` has SHA-256:
`a2cdf10314926961f71a79e8f5fe6197b414c36b356b064fc7f0f5d7abc01b01`.
This digest records the initial local manifest; regenerating it with different
paths or platforms may change its bytes. All recordings and the manifest stay
local and ignored by Git. The protocol and checker are version-controlled.

```powershell
python real_data_split.py --training data/refit/house1-replay-10000.csv --development data/refit/house2-replay-10000.csv --final-test data/holdout/house5-replay-10000.csv
python real_data_split.py --verify data/refit/split-v1.json
```

Creation refuses to overwrite an existing manifest. It uses the existing CSV
validator and rejects identical files or exact normalized measurements shared
across partitions, including duplicates hidden by number formatting. Verification
checks declared house assignments and file hashes without scoring. It does not
prove household identity, detect every near-duplicate, or prevent someone from
manually changing both data and the manifest. Different houses may share wall-clock
times; time-range overlap alone is not evidence of training leakage.

Next milestone: implement an isolated fridge-only training path using House 1,
compare fixed baseline/tree/forest candidates on House 2, and report strict-timing
coverage. Freeze the candidate choice and thresholds before unlocking House 5.
Do not replace the live three-appliance model with a one-appliance experiment.
