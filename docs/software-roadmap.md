# Software roadmap: implemented learning lab

Phases 1–5 are implemented locally. Physical sensing, electrical calibration,
and real-home validation remain future work. This is not a reliable appliance
meter or a billing system. The existing live model has not been replaced.

## How readings reach the website

CSV replay, the simulator, and local sensor JSON all enter `EnergyProfiler.process`
in `app.py`. It validates timing, builds a trailing aggregate-only feature window,
asks the model for estimates, and saves a reading in SQLite. The dashboard polls
the API. Appliance measurements are ground truth for comparison, not model inputs.
CSV export preserves readings for later study; absent appliance labels stay blank,
not zero. The optional `washing_machine` column is separate from the live model's
three outputs.

## Try the real recording

From the project directory, with its virtual environment activated:

```powershell
python prepare_recording.py data/refit/house1-first-10000.csv data/refit/house1-replay-200.csv --timestamp Unix --timestamp-format unix --mains Aggregate --refrigerator Appliance1 --limit 200 --origin "REFIT House 1; Zenodo 5063428; CC BY 4.0"
python app.py
```

The source sample is local and ignored by Git. See [REFIT first look](refit-first-look.md)
for acquisition and inspection. Source: [REFIT cleaned dataset](https://zenodo.org/records/5063428).
House 1 Appliance1 is the refrigerator. This sample provides no lamp or microwave
ground truth. Source cleaning may already have imputed missing values; the `Issues`
field is not interpreted or silently filtered.

Open the dashboard, choose the converted CSV, set sample interval to **8**, click
**Load CSV**, then **Replay CSV / restart**. Playback advances one recorded row per
wall-clock second; calculations still use original timestamps. Eight seconds is
an explicit nominal replay assumption, not a claim that every interval is eight
seconds. The larger 10,000-row prefix has a median interval of three seconds.

For the first 200 rows, the independent integration check found:

- 817 covered seconds; 413 seconds skipped under the 12-second maximum-gap rule.
- Aggregate energy: **0.3060201389 kWh**.
- At the illustrative $0.16/kWh rate: **$0.04896322**.

Energy uses trapezoids between adjacent valid readings: average watts × elapsed
seconds / 3,600,000. Long gaps and missing endpoints contribute neither energy
nor coverage. Changing the nominal cadence changes coverage; do not choose it
just to obtain a desired total. The first reading has no preceding energy interval.

## Frozen model evaluation

The live model expects one-second data. **Strict** evaluation correctly produces
no predictions on this eight-second configuration. **Native-window diagnostic**
uses the same number of consecutive samples, with resets for gaps over 16 seconds.
Those samples span a different duration than training, so it is only a stress test.

Use **Evaluate loaded CSV — no retraining**, or:

```powershell
python experiments.py data/refit/house1-replay-200.csv --cadence 8 --policy strict
python experiments.py data/refit/house1-replay-200.csv --cadence 8 --policy sample_window
python run_comparisons.py data/refit/house1-replay-200.csv
```

Reports are saved under ignored `data/experiments`, with model metadata, source
hashes, timing policy, label counts, confusion matrices, accuracy, precision,
recall, F1, MAE, RMSE and covered-interval energy errors. Refresh dashboard history
to view them. The chart shows up to 2,000 points; metrics cover the full report.
API experiments are limited to 10,000 rows. Missing metrics mean unavailable, not
perfect accuracy. Metrics score **raw predictions before abstention**; the Certain
column shows how many were not flagged uncertain, not a calibrated probability.

The original frozen model (`fea34356acf733a8`) scored 196 diagnostic fridge windows:
accuracy 54.08%, F1 0.683, MAE 99.87 W; only 67 were marked certain.

The comparison runner applies a common 30-reading warmup, leaving the same **171**
real-data windows for each model. Results from this local run:

| Model | Fridge F1 | Fridge MAE (W) |
|---|---:|---:|
| Original frozen model | 0.615 | 102.49 |
| Classic synthetic RF, five samples | 0.603 | 102.59 |
| Realistic synthetic RF, five samples | 0.624 | 40.84 |
| Realistic RF, watts only | 0.605 | 35.74 |
| Realistic RF, history features | 0.632 | 41.27 |
| Decision tree | 0.627 | 39.26 |
| Always off / zero watts | 0.000 | 40.19 |

The realistic five-sample model is **slightly worse than zero watts on MAE** here.
Lower power error alone does not prove useful appliance detection. Longer windows
also did not consistently improve real-data F1. These are exploratory comparisons
on one short recording, not an untouched final test set; do not claim generalization.
The original 79.2% dashboard score describes synthetic held-out combinations only.

## Simulator and research models

Choose Original, Realistic, or Realistic + experimental washer in Simulation lab.
Realistic mode has seeded changing wattage, startup spikes, cycling, overlapping
devices, unknown background load and sensor noise. The washer has compressed
fill/heat/wash/drain/spin stages; these demonstrate multiple states, not a calibrated
real washing cycle. Repeated profile resets reproduce the same seed for debugging.

`run_comparisons.py` compares RF windows of 5/10/20/30 samples, summary/history/watts
features, a decision tree and an always-off baseline. Training and evaluation use
separate generated sessions and seeds; windows never bridge sessions. A separate
four-device model evaluates washer sessions. Research models are not promoted to
the live model and no command above writes `data/models`.

## Dashboard analytics

Actual vs. predicted overlays measured watts and dashed raw estimates, with gaps
and unavailable truth left visible. Select saved reports or the live session.
Original appliance cards retain measured energy breakdowns; unexplained watts
remain a heuristic residual, not an identified mystery appliance. Detected changes
still require three confirming predictions. Saved-session comparisons include
coverage, skipped/missing counts, energy and cost at the **current** tariff, not
historical billing. Different session durations are not directly comparable.

## Future sensor contract (no hardware required)

Select **Wait for local sensor**, or POST `/api/source` with
`{"source":"sensor","cadence":1}`. Then POST `/api/sensor/readings`:

```json
{"timestamp":"2026-09-22T12:00:00Z","total_watts":123.4}
```

Timestamps require a timezone and must increase strictly. Watts may be null for
missing readings, otherwise finite and between 0 and 1,000,000. Extra fields are
rejected; independently measured labels must not be invented by a sensor adapter.
Bodies over 8 KB return 413; invalid data 422; duplicate/out-of-order timestamps
or paused/wrong source mode return 409. Sensor mode never creates simulator samples.
The request schema is available in `/docs`. CSV and JSON share normalized timestamps,
watts and missing-value semantics; CSV may additionally carry evaluation labels.

Keep the server loopback-only. An ESP32 cannot directly reach this loopback address:
a future local relay or authenticated gateway is still needed. No authentication,
network exposure, mains wiring, sensing calibration or physical accuracy is claimed.

## Verification and next learning step

Run `python -m unittest -q`, `python -m unittest discover -s research -q`,
`python -m pip check`, and `node --check static/experiments.js`.
The real 200-row replay was independently checked against timestamp-based
integration; the dashboard was checked in a real browser.

Next, explain why the zero-watt baseline has a low MAE despite detecting no fridge
activity. Then collect a longer recording with both on and off periods from a
different house before tuning further. This is the most useful next ML milestone.

Checkpoint update: the [independent House 2 diagnostic](independent-house-check.md)
is complete, with timing incompatibility and energy overestimation documented.
The [cadence-aware protocol and first comparison](cadence-protocol.md) are now
implemented: matching eight-second training/evaluation, three fixed candidates,
and no automatic live-model promotion. Real-data partitioning is next.
