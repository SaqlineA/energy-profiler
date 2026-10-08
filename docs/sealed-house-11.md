# Sealed test house: REFIT House 11

This replaces House 5, which was scored once (`docs/final-test.md`) and is
spent. House 11 was sealed on 8 October 2026, the moment it was downloaded,
before any of its readings were looked at.

## What was downloaded

- **Source:** [REFIT on Zenodo](https://zenodo.org/records/5063428),
  `CLEAN_House11.csv` (CC BY 4.0).
- **Download:** a byte-range prefix of 1,500,000 bytes, the same way as Houses
  1–5. It was cut to the first 10,000 complete readings by
  `research/save_refit_sample.py`, which checks only the header and the row
  count.
- **SHA-256 of the 10,000-reading file** (`data/sealed/house11-first-10000.csv`,
  local and ignored by Git): `f104e783b7632c0c3cb5b325ed117164700aa3c43beecfa1d3eec9ec9d31618d`.
- **SHA-256 of the raw prefix:** `5081c8599d8935c0b1f42505a070f5b7df6a71288097238a87538b0d4afc5827`.

## Fridge channel (decided before opening)

Taken from NILMTK's REFIT metadata (`building11.yaml`, meter N = REFIT
Appliance(N−1)):
- **Fridge:** meter 2, which is **Appliance1**, labelled "Fridge" (spelled
  "Firdge" in the metadata).
- **Confound:**
  - House 11 also has a **fridge-freezer**: meter 3, which is Appliance2.
  - Its cycles appear in the household total but are not labelled as the
    fridge. This is the same kind of confound as House 4's extra freezers.
  - It is stated now so that it can't be used as an excuse later.

## Rules

1. **Nothing reads House 11's values** (power, timing or appliance channels)
   until a final-test protocol has been committed and every model it names is
   frozen.
2. **That protocol must name before House 11 is opened:**
   - the exact models;
   - their version hashes;
   - the decision rule.
3. **House 11 is scored once.** Every result is recorded, including failure.
4. **Normalising the file to the project's CSV format happens inside that final
   run,** not before. The normalising step is `prepare_recording.py`, with
   `--refrigerator Appliance1`.
5. **No tuning against it,** and no peeking at summary statistics. A check that
   only counts rows or hashes the file is allowed.

## Known limits, stated now

- **One home:** a sealed result is still one home.
- **Short slice:** about a day of data (10,000 readings at 8 s), the same
  length as Houses 1–5.
- **Untested cleaning:** the cleaned REFIT data may include upstream
  imputation, and gaps are not checked until the final run.
