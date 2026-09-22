# Current — Energy Profiler

A local learning project: simulator or recorded household data → causal appliance
inference → SQLite → live dashboard. No hardware, cloud account, GPU, or frontend
build tools required. **The bundled data is synthetic; real-household accuracy
has not been established.**

## Software roadmap: real-data experiments

See the [software roadmap guide](docs/software-roadmap.md) for real CSV replay,
frozen-model evaluation, realistic simulation, research comparisons, dashboard
analytics and the local sensor contract. It includes measured results and important
limitations. [REFIT first look](docs/refit-first-look.md) explains the source data.

## Run

### Edit online with GitHub Codespaces

Open this private repository on GitHub, choose **Code → Codespaces → Create**,
and select the smallest available machine. Setup installs Python dependencies.
In the editor's terminal, run:

```bash
python app.py
```

Open **Ports → 8000 → Open in Browser**. Keep port visibility **Private**:
GitHub sign-in protects this preview; the app itself has no login. Never change
it to Public. Only this Codespace's exact HTTPS preview address is additionally
allowed; local security checks remain enabled. Unsupported forwarding domains
stop startup instead of opening access broadly.
Start with `python app.py`: it disables Uvicorn's proxy-header interpretation so
GitHub's rewritten HTTP localhost Host/Origin pair remains consistent. The browser
connection still uses HTTPS. Do not substitute a default `uvicorn app:app` launch.

- Change `static/index.html` for page structure, `static/style.css` for design,
  `static/app.js` for browser behavior, and `app.py` for the Python server.
- Save a file, then refresh the preview. For Python edits, press Ctrl+C in the
  server terminal and run `python app.py` again. Run `python -m unittest -q`
  before saving changes to GitHub.
- Use **Source Control → Commit → Sync Changes** to back up code to the repository.
  Local and cloud copies do not automatically sync: commit/push, then pull in
  the other copy before editing there.
- Reopen your existing workspace from [Your Codespaces](https://github.com/codespaces).
  Avoid making a new workspace every time. Run the server again after a stop.
- Stop the Codespace when finished. This is an online development environment,
  **not 24/7 hosting**. Compute and storage have quotas; check GitHub's usage page
  and do not enable paid overages unless you want them.
- `data/`, recordings, trained models, logs, secrets, and personal notes are ignored
  by Git. Your computer's saved readings are not uploaded. Cloud-generated data
  stays in that Codespace, not the repository: export/download anything important
  before deleting the Codespace or its retention period expires.

Configuration follows the [Dev Container specification](https://containers.dev/implementors/json_reference/)
and [GitHub's private port-forwarding documentation](https://docs.github.com/en/codespaces/developing-in-a-codespace/forwarding-ports-in-your-codespace).

### Run on your computer

```powershell
.\.venv\Scripts\python.exe app.py
```

Open http://127.0.0.1:8000. Keep the terminal running. Use one server process.
After editing Python code, restart the server; after editing browser code, refresh.
The app binds to localhost, has no authentication, and must not be exposed publicly.
Browser writes must come from the same origin; non-local Host headers are rejected
unless using the exact private Codespaces preview described above.
This is not authentication against other local programs. Data stays local; the
existing stylesheet optionally fetches Google Fonts (system fonts work offline).

On a fresh computer with Python 3.11+:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

## Try the upgrade

1. Watch the simulator. Predictions begin after five readings. Switches still
   select manual mode; the Pause control stops collection.
2. Under **Choose your data**, select `examples/replay-demo.csv`, interval **1**,
   click **Load CSV**, then **Replay CSV / restart**. This is a hand-authored
   synthetic fixture, NOT a real household recording. Watch the blank reading
   and timestamp gap: neither becomes zero watts, and the chart breaks there.
3. Observe measured watts separately from ML estimates. Unknown labels stay unknown.
4. Review per-appliance precision, recall, F1, power MAE, energy error, and the
   two baseline scores. Open the JSON report for provenance and positive support.
5. **Start simulator** starts a new session without deleting saved readings.
   Replay ends at the last row; use its restart button to play again.

The example is deliberately too short for training. Use a substantially longer,
labeled recording to train a recorded-data model.

## Architecture and reading order

```text
simulator.py / normalized CSV (sources.py)
                ↓ timestamps, aggregate watts, optional measured labels
app.py: source selection → gap/cadence checks → last 5 aggregate readings
                ↓
features.py: watts, change, mean, variation, minimum, maximum
                ↓
ml.py: per-appliance state probabilities + estimated watts
                ↓
storage.py: raw measurement + truth + prediction + quality + model/source ID
                ↓
FastAPI snapshots → static/app.js dashboard

offline: prepare_recording.py → evaluate.py → versioned model + JSON report
```

Inference receives only aggregate power history. Labels never enter its features.
The latest timestamp is the prediction target: **no future samples** and no
midpoint-window latency. Five points require four intervals of warm-up, including
after gaps, source changes, and model replacement. Event notifications separately
require three consecutive confident predictions; that adds two sample intervals.

The model uses multi-output random forests, not a separate class for every possible
combination. Bit masks remain in exports as a backwards-compatible presentation
format, not the new training target. The old one-watt/joint classifier remains an
evaluation baseline. The second baseline always predicts all appliances off.

## Bring a real recording

Obtain a household dataset under its provider's access and license terms. This
repository does not download or redistribute UK-DALE, REFIT, REDD, or others.
Do not assume a dataset column represents a particular appliance: consult its
household/meter metadata. Choose **active power in watts**, not apparent power or
cumulative energy. Mixed units must be converted before ingestion.

Normalized CSV:

```csv
timestamp,total_watts,lamp,refrigerator,microwave
2026-01-01T00:00:00Z,160,10,150,0
2026-01-01T00:00:01Z,161,11,150,0
```

- Required: `timestamp`, `total_watts`. Optional: the three measured appliance columns.
- Blank = unknown. Only write `0` when the submeter actually reports zero.
- Timestamps must have a timezone, be unique, and increase strictly.
- One household/continuous recording per file. Separate households into files.
- Power must be finite and within 0–1,000,000 W (a numeric safety bound, not the
  model's detection range). No net-export support or automatic resampling.
- Import limit: 5 MB and 50,000 rows. Select a representative slice for this prototype.
- Set the real sample interval in the dashboard. Playback advances one row per
  wall-clock second, but calculations use original timestamps, not playback speed.

For differently named columns, `prepare_recording.py` is a streaming converter.
Example with **illustrative column names; replace them using your dataset metadata**:

```powershell
.\.venv\Scripts\python.exe prepare_recording.py source.csv recording.csv --timestamp Time --timestamp-format unix --mains Aggregate --lamp LightMeter --refrigerator FridgeMeter --microwave MicrowaveMeter --limit 10000 --origin "Dataset reference; household identifier"
```

Omit appliance mappings when unknown. Use `--scale 1000` only if **all mapped power
columns** are in kW. Use `--start` to select a later slice. ISO timestamps with an
offset are accepted by default; `--timestamp-format unix` means Unix **seconds**.
The converter validates the result, refuses overwrites, and creates a metadata
sidecar with your source reference, mapping, units conversion, and output hash.
Keep this sidecar with your experiment. The dashboard records the CSV hash/name;
it does not automatically import sidecar metadata or independently verify origin.

## Training and honest evaluation

The dashboard can train on synthetic data or the loaded labeled CSV. Training
runs off the sampling loop. A new model is activated only after successful fitting,
evaluation, and saving. Appliance thresholds are defined in `ml.py` and copied into
every report; adapt them deliberately for a real dataset and keep them fixed when
comparing experiments.

**Synthetic:** 60 training households and a fixed seed-10042 set of 20 held-out
households. Retraining changes the training seed, not the held-out test set.
Synthetic appliances have nominal powers 10, 150, and 1200 W, ±3% household variation
and ±2 W sample noise. Synthetic windows number 5,760 train / 1,920 test.

**Recorded:** split raw rows chronologically 70/30 **before** building windows.
No window crosses the split or a gap. All three labels are required for a scored
training/test window. Missing labels exclude the window rather than becoming off.
A minimum of 34 raw rows is enforced, but that is a technical minimum, not a useful
evaluation dataset. Use many complete appliance cycles and a genuinely separate
household when possible. Windows overlap within each partition; repeated trials on
the same holdout can still overfit your experiment choices. Keep a final untouched
dataset for any performance claim.

Offline evaluation does not replace the running server's active model:

```powershell
# Fixed synthetic benchmark
.\.venv\Scripts\python.exe evaluate.py --output data/experiments/synthetic

# Chronological split of a labeled recording sampled every 8 seconds
.\.venv\Scripts\python.exe evaluate.py --csv recording.csv --cadence 8 --output data/experiments/recorded

# Stronger: explicitly separate household/session holdout
.\.venv\Scripts\python.exe evaluate.py --csv training-house.csv --test-csv heldout-house.csv --cadence 8 --output data/experiments/heldout
```

Separate-file evaluation rejects identical files and exact duplicated measurements.
You remain responsible for selecting genuinely independent households and avoiding
near-duplicates. Reports include dataset hashes, split policy, feature schema,
cadence, threshold policy, seed, library version, and model version.

Metrics:

- Precision: how often a predicted on-state is right.
- Recall: how often a real on-state is detected.
- F1: balance of precision and recall. Check positive support; zero positives
  cannot demonstrate detection ability.
- MAE: mean absolute error in estimated appliance watts.
- Energy error: absolute difference of integrated predicted/measured kWh over
  adjacent scored intervals. Check `energy_coverage_seconds`; excluded gaps and
  warm-up periods are not included. Signed errors can cancel in total energy.
- Exact combination accuracy remains for comparison, but can hide weak appliances.

Held-out metrics score **raw model output before abstention**. Live session metrics
exclude warm-up/missing/cadence-mismatch windows, count abstentions as wrong, and
show prediction coverage. Session results mix model versions and replay may include
training rows; they are not a separate held-out benchmark.

## Missing data, energy, and uncertainty

Replay uses trapezoidal integration: `(previous_W + current_W) / 2 × delta_seconds
/ 3,600,000`. The first point has no preceding interval and contributes no energy.
An interval is excluded when either aggregate reading is missing or elapsed time
exceeds 1.5× the declared cadence. Covered/skipped seconds appear in the dashboard.
There is no interpolation over gaps. Inference additionally requires intervals
within ±20% of cadence; irregular samples restart the window. Models trained at a
different declared cadence abstain until you train an appropriate model.

Simulation retains its original rule: each recorded sample represents one simulated
second, including the first. Pauses do not add energy. Its timestamps follow a
logical simulation clock, so after pausing they are not wall-clock acquisition times.

Measured appliance energy is shown only for covered intervals with both labels;
partial coverage is not a full-session total. The API includes per-device coverage.
Changing the illustrative tariff reprices covered session energy only.

Predictions may abstain for an ambiguous score, out-of-training power range, or
large unexplained residual. Unexplained watts = aggregate minus estimated known
appliance watts; this can be negative due to model error. These are **heuristics**,
not reliable unknown-device detection or calibrated probabilities. Never use this
prototype for safety decisions, billing, or claims of exact appliance identification.

## Persistence and compatibility

- Readings: `data/readings.sqlite3`, with WAL for concurrent exports and collection.
- The upgrade copies old rows/IDs into `readings_v2` transactionally and preserves
  the original `readings` table. It is safe to restart; legacy rows are not duplicated.
- Models: versioned `data/models/*.joblib` and `current.json`. Training publishes
  the manifest last; startup verifies the checksum/schema/library version and loads
  once, rather than retraining or reloading at every prediction.
- **Joblib is executable serialization. Never load downloaded or uploaded model
  files.** Hashes detect corruption, not malicious local file replacement. Only
  this app's trusted local model directory is loaded.
- Incompatible/corrupt artifacts stop startup. Preserve them for diagnosis and run
  offline training into a fresh directory; do not silently replace recorded models.
- Restarting resets the live session and returns to the simulator; tariff, history,
  and trained model persist. Uploaded replay buffers are in memory, so reload the
  original CSV after restart. Source SHA-256 IDs remain in recorded readings.
- Export retains missing values as blanks and adds source, quality, covered
  interval, model version, and per-appliance predictions. Old sessions remain.
- Original learning scripts remain. Existing `power_readings.csv` and notes stay
  on the original computer and are deliberately excluded from Git.

## API

| Endpoint | Purpose |
| --- | --- |
| `GET /api/dashboard` | Consistent state/history snapshot; `after_id` + `session` for incremental polling. |
| `GET /api/state`, `GET /api/readings` | State or current-session history. |
| `POST /api/replay?cadence=1&name=recording.csv` | Raw UTF-8 CSV body (`text/csv`); validates before replacing the in-memory buffer. |
| `POST /api/source` | `{"source":"replay"}` or `{"source":"simulator"}`; starts a new session. |
| `POST /api/simulation` | Pause/resume; simulator-only auto/manual mode. |
| `POST /api/appliances/lamp` | Simulator-only `{"is_on":true}`. |
| `POST /api/tariff` | `{"rate":0.20}`; persisted finite illustrative rate. |
| `POST /api/model/train` | `{"source":"synthetic"}` or `{"source":"recorded"}`. |
| `GET /api/model/report` | Current held-out evaluation and provenance. |
| `GET /api/export.csv` | All saved sessions; nullable fields preserved. |

Interactive API docs: http://127.0.0.1:8000/docs.
Source changes and training are not safe to retry blindly after a timeout: check
`/api/state` or the model report first. They create new sessions/model versions.

Request-boundary middleware follows the
[FastAPI middleware pattern](https://fastapi.tiangolo.com/tutorial/middleware/)
and [TrustedHostMiddleware](https://fastapi.tiangolo.com/advanced/middleware/#trustedhostmiddleware).

## Verify and learn

```powershell
.\.venv\Scripts\python.exe -m unittest -v
node --check static/app.js
```

Tests use temporary databases and cover old functionality plus replay, gaps,
nullable labels, source controls, cadence mismatch, causality, data splits,
baselines, model round trips/checksums, provenance, and non-destructive migration.
Node is optional; only the JavaScript syntax check needs it.

Suggested learning exercise: change the window size in `features.py`, retrain in
a fresh experiment directory, and explain whether F1 improves versus the **same**
held-out data and single-watt baseline. Do not judge changes only by a prettier graph.

## Architecture references

Original implementation inspired by ideas, not copied source or bundled dependencies:

- [NILMTK](https://github.com/nilmtk/nilmtk): data contracts, alignment, evaluation.
- [NILMTK-contrib](https://github.com/nilmtk/nilmtk-contrib): model interfaces and explicit window alignment.
- [goruck/nilm](https://github.com/goruck/nilm): appliance-specific preprocessing/inference pipeline.
- [Emoncms](https://github.com/emoncms/emoncms): input/history separation and missing-data semantics.
- [NILMbench](https://github.com/nilmtk/nilmbench): fixed splits and experiment provenance.

Remaining research work: obtain/label real recordings, map their actual appliances,
validate thresholds and uncertainty on unseen households, and compare stronger
models. A future sensor adapter can feed the same reading contract; no firmware or
mains-wiring instructions are included because this project has no hardware yet.
