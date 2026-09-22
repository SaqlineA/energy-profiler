# Software roadmap implementation

Approved by the user: implement the software roadmap locally; physical hardware
assembly, calibration and household validation remain user-owned. No paid services.

## Modules and order

1. `real-data`: convert 200 REFIT rows without filling or changing timestamps.
2. `evaluation`: preserve the saved baseline; score known labels only. Report
   strict timing coverage separately from explicit sample-window diagnostics.
3. `simulation`: seeded realistic sessions, cycles, startup, noise, background,
   overlap and optional multi-stage washing machine.
4. `experiments`: compare features/windows and RF, decision-tree, always-off
   baselines on held-out sessions and identical real data. Do not promote models
   automatically or claim improvements before measuring.
5. `analytics`: actual/predicted charts, saved experiments and session summaries.
6. `sensor-contract`: validated local ingestion, with simulator-independent time.

## Contracts and safeguards

Normalized readings retain UTC `timestamp`, `total_watts`, and nullable measured
appliance watts. Missing truth is never off. Unknown loads are not identified by
residual power. No interval spanning an excessive gap contributes energy.
Original three-device model artifacts remain loadable and are never overwritten
by research experiments. A fourth device is initially experimental, not secretly
added to the baseline model. Existing localhost/Origin restrictions remain.

Experiments use source hashes, model version, seed, features, window length,
timing policy, counts and limitations. Metrics use only measured labels, report
positive and negative support, and do not silently count abstentions as off.
Research artifacts/recordings stay in ignored `data/`. Browser output uses text
nodes for supplied names. Request sizes, choices and numerical values are bounded.

## Verification and design

Use unittest (`.\.venv\Scripts\python.exe -m unittest -q`), separate pandas
tests (`... -m unittest discover -s research -q`), and `node --check` for JS.
Add small focused regression tests before changing behavior. Use isolated test
data directories so verification does not overwrite the user's recordings/models.
Retain the current dashboard's colors and layout; add labeled experiment controls,
empty/error states, accessible charts and scrollable tables rather than redesign.
Verify browser behavior and narrow mobile layout before calling UI work complete.

## Risks

REFIT cleaning already filled some gaps. Source `Issues` encoding needs verification
before filtering. Irregular timestamps do not establish sensor sampling frequency.
Small slices and single-class labels cannot establish generalization. Native
sample-window diagnostics deliberately change the time represented by a window:
they are a domain-shift stress test, not a deployable cadence conversion.

Hardware networking, authentication outside localhost, ADC selection, actual
voltage/current measurement and calibration are not part of this software run.
