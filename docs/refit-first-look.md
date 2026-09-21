# First look at real household electricity

Completed: the roadmap's **today** assignment, not all of Phase 1.
No dashboard, database, simulator or model changes. No retraining or inference.

## Run it yourself

From the project folder in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-research.txt
.\.venv\Scripts\python.exe inspect_refit.py data/refit/house1-first-10000.csv
```

In Codespaces, use `python` instead of `.\.venv\Scripts\python.exe`.
The sample lives on this computer and is Git-ignored; it is not uploaded to GitHub.
The research dependency is optional and does not change server requirements.

Read `inspect_refit.py` from top to bottom:

- `pd.read_csv(path)` opens the CSV as a table called a DataFrame.
- `df.head()` selects its first five rows.
- `df.columns` holds the column names.
- `df.shape[0]` counts rows in this file, not the original full recording.
- `df.isna().sum()` counts missing entries in each column. Zero watts is a value.
- `df["Unix"].diff()` subtracts consecutive timestamps to measure spacing.

The script reads the whole local file into memory. Start with this small sample.
It neither fills gaps nor changes the file. Malformed numeric timestamps fail
visibly instead of being silently repaired.

## What we actually observed

Sample: the **first 10,000 data rows** of `CLEAN_House1.csv`, unchanged,
plus the original header. This is a chronological prefix, not a random sample
or representative benchmark.

| Check | Result in this sample |
| --- | --- |
| Columns | 13 |
| First recorded Time | 2013-10-09 13:06:17 |
| Last recorded Time | 2013-10-10 09:39:04 |
| Missing entries recognized by pandas | 0 in every column |
| Median consecutive Unix difference | 3 seconds |
| Smallest / largest difference | 1 / 4,363 seconds |
| Non-increasing timestamp steps | 0 |

The dataset's nominal sampling description is approximately eight seconds, but
**this exported prefix is not a regular eight-second sequence**. Its largest
gap is about 73 minutes. We have not established the reason for the irregular
spacing. Do not replace timestamps with row numbers or claim three seconds is
the sensor's sampling rate.

The cleaned release fills short gaps with preceding values and longer gaps with
zero. Therefore, no NaNs does **not** establish uninterrupted measurement, and
zero is not always proof that an appliance was off.
[University of Strathclyde dataset and cleaning notes](https://pureportal.strath.ac.uk/en/datasets/refit-electrical-load-measurements-cleaned/).

## Reading the columns

`Time` is readable time text; `Unix` is its numeric timestamp in seconds.
`Aggregate` is whole-house power in watts. The nine `Appliance` columns are
separately monitored loads, also in watts.

House 1's published mapping:

| Column | Monitored load |
| --- | --- |
| Appliance1 | Fridge |
| Appliance2 | Chest freezer |
| Appliance3 | Upright freezer |
| Appliance4 | Tumble dryer |
| Appliance5 | Washing machine |
| Appliance6 | Dishwasher |
| Appliance7 | Computer site |
| Appliance8 | Television site |
| Appliance9 | Electric heater |

Mapping reference: the data-packaging authors' [REFIT walkthrough](https://frictionlessdata.io/blog/2017/12/19/dm4t/),
which transcribes the dataset's data dictionary and shows matching initial rows.
The original university README download returned a browser verification page
during this inspection. Recheck its house-specific notes before later evaluation,
especially when selecting another period. Appliance numbers differ across houses.
Computer/TV sites need not represent single devices.

`Issues` is an additional source field. Preserve it. Its encoding has **not**
been verified here; do not use it as watts, an appliance label, or a quality
filter until the matching release documentation is checked.

In the first row, aggregate power is 523 W, while the nine appliance readings
sum to 144 W. The 379 W difference is unaccounted for by those channels; it is
not another known appliance label. Unmonitored loads and measurement timing
can contribute to differences. Do not force the appliance sum to equal aggregate.

There is no separate lamp or microwave column in this House 1 mapping. A later
comparison with our three-appliance model should initially consider the fridge,
not score absent lamp/microwave truth as off.

## Source and reproducibility

Downloaded 2026-09-21 from [Zenodo record 5063428](https://zenodo.org/records/5063428),
linked by the university. Creators: David Murray and Lina Stankovic.
License: CC BY 4.0, confirmed in the record metadata.
Please cite the [REFIT dataset paper](https://doi.org/10.1038/sdata.2016.122) when
using the data in project reports. This local derivative selects a prefix only;
it does not alter the selected source lines.

The original file is 400,840,083 bytes. We downloaded bytes 0 through 999,999,
then retained the header and first 10,000 complete rows, avoiding a cut-off row.
We did not download the full recording or verify its full-file checksum.

Local sample SHA-256:
`ab94289712b85d50bbf1d3c46dc6042742fabd48f022c7bfd88773611e5e197d`

To reproduce on Windows in a fresh project copy (requires curl):

```powershell
New-Item -ItemType Directory -Force data/refit
curl.exe -4 -L --fail --max-time 40 --range 0-999999 --max-filesize 1000000 "https://zenodo.org/api/records/5063428/files/CLEAN_House1.csv/content" --output data/refit/house1-prefix.part
# Continue only if curl succeeds.
.\.venv\Scripts\python.exe research/save_refit_sample.py data/refit/house1-prefix.part data/refit/house1-first-10000.csv
```

Do not run the download over an existing `.part` file you want to preserve.
The sample-saving helper refuses to overwrite an existing destination CSV.
On Linux/Codespaces, use `mkdir -p data/refit`, `curl`, and `python` instead.

## Checks and your next exercise

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s research -q
.\.venv\Scripts\python.exe -m unittest -q
```

Research tests are separate so running the website's original tests does not
require pandas. Tests check output, missing-versus-zero behavior, unchanged input,
single-row handling, complete sample rows, and overwrite protection.

Try adding `print(df["Appliance1"].describe())` yourself. Can you explain its
minimum, mean and maximum? Then explain why zero missing values and a long
timestamp gap can both be true.

Next milestone: agree how to handle irregular timestamps, verify source quality
flags, and convert a suitable sample for replay. Only then evaluate the existing
model without retraining. Its one-second training cadence currently differs
from these recordings, so a naive upload is not a valid baseline experiment.
