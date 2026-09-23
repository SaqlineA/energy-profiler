# Extended REFIT check and dashboard refresh

## Experiment boundary

The next software checkpoint evaluates the unchanged model `fea34356acf733a8`
on five non-overlapping sections of the existing REFIT House 1 prefix, excluding
the initial 200 rows used for exploration. Each section contains 1,960 readings;
9,800 additional readings were processed. No training or tuning took place.
Native sample-window diagnostics reset at gaps above 16 seconds and at every
section boundary. This remains a timing-mismatched, same-house stress test:
**cross-house validation is still outstanding**.

## Results

| Original data rows (1-based) | Scored | Fridge on / off | F1 | MAE W | Zero-watt MAE W |
|---|---:|---:|---:|---:|---:|
| 201–2160 | 1952 | 282 / 1670 | 0.263 | 119.41 | 11.52 |
| 2161–4120 | 1921 | 510 / 1411 | 0.323 | 134.20 | 20.29 |
| 4121–6080 | 1952 | 281 / 1671 | 0.252 | 144.16 | 10.91 |
| 6081–8040 | 1944 | 442 / 1502 | 0.370 | 137.97 | 17.34 |
| 8041–10000 | 1944 | 354 / 1590 | 0.234 | 126.85 | 14.39 |

Zero-watt MAE is calculated on exactly the same scored rows. It wins on power
error because most observations are off and the original model frequently
attributes other loads to the fridge. It detects no fridge activity, so its F1
is zero. Neither strategy is ready for appliance metering. Lamp and microwave
truth remain unknown and are not scored. A short initial slice substantially
understated the real-data difficulty.

Saved reports appear as **Extended REFIT House 1 / rows …** under Experiments.
Each contains the normalized section hash, offset and timing limitations. The
reports are local ignored data; this document preserves the findings in Git.

## Reproduce with existing tools

No new framework or runner is necessary. For the first section:

```powershell
python prepare_recording.py data/refit/house1-first-10000.csv data/refit/extended-201.csv --timestamp Unix --timestamp-format unix --mains Aggregate --refrigerator Appliance1 --start 200 --limit 1960 --origin "REFIT House 1; Zenodo 5063428; CC BY 4.0"
python experiments.py data/refit/extended-201.csv --cadence 8 --policy sample_window
```

Repeat with zero-based starts 2160, 4120, 6080 and 8040, using distinct output
filenames. Keep the same model artifact. In each report, the zero-watt MAE is the
mean measured fridge watts among points that have a fridge prediction. Do not
count warmup or gap-reset rows. Source provenance and cleaning caveats are in
[the software guide](software-roadmap.md).

## Design contract and verification

Keep Current's green/cream identity and its existing vanilla HTML/CSS stack.
The screen's primary job is monitoring; importing data and running an experiment
are secondary tasks. Use native expandable settings, direct section navigation,
clearer type and table spacing, visible chart line keys, and keyboard focus.
Keep uncertainty explanations visible with the selected report. No new UI
dependencies, animation package, fabricated results or automatic model promotion.

The new **Data source & import** panel expands to expose existing controls.
The experiment workbench separates report inspection from **Run a new frozen-model
evaluation**. Jump links reach experiments and sessions on small screens too.
Tests cover the existing processing behavior; runtime checks cover report display,
keyboard-operated disclosure and layout at 320, 768, 1024 and 1440 pixels.

Next research task: choose a documented second-house refrigerator channel, obtain
an independent recording and establish its timing/quality before training changes.
This check does not substitute for that validation or for physical hardware.
