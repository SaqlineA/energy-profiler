# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Primary: the builder.** A developer new to ML and hardware who uses Current
  as a personal household-energy research lab. They run the simulator, replay
  real recordings, train and compare models, and read the evidence to decide
  what to try next. They want to understand every result, not just see a score.
- **Secondary: portfolio viewers**, such as recruiters, employers and peers the
  builder shows the project to. Many do not know ML. They should grasp within a
  minute what the home is doing, what the model got right and wrong, and whether
  data is real or simulated. The stated test: "a non-ML recruiter should
  immediately understand it."

## Product Purpose

Current ("Current — Energy Profiler") has two equal jobs:

1. **Live energy insight.** It shows household power, energy, illustrative cost
   and appliance activity at a glance, from a simulator, a replayed recording or
   a local sensor.
2. **An honest appliance-detection lab.** It shows what non-intrusive load
   monitoring (NILM) gets right and wrong from aggregate power. It compares
   simulated and real (REFIT) data using preregistered experiments, with
   failures shown as plainly as successes.

Success means the builder learns something true from every experiment, and a
viewer leaves understanding both the live picture and the limits of the model.
It is a learning and research application, not a validated meter, billing
system or safety device.

## Positioning

Most energy dashboards imply their appliance breakdowns are right. Current's
defining mechanism is visible evidence:

- every result states what data it was tested on and trained on (real vs
  synthetic);
- experiments are written down before they run;
- the one held-out real house (REFIT House 5) was scored exactly once;
- plain-language explanations sit next to F1, MAE and energy error.

Its headline finding is uncomfortable and kept front and centre: on the unseen
house, the simulator-trained model beat the model trained on real houses.

## Operating Context

- Runs locally (`python app.py` → `http://127.0.0.1:8000`) or in a private GitHub
  Codespace. It is used by one person at a time, alongside the repository's
  `docs/` write-ups and the command-line research scripts
  (`fridge_development.py`, `final_test.py`, `washer_experiment.py`,
  `fridge_profile.py`, `washer_profile.py`).
- **Data sources** share one processing pipeline:
  - a seeded simulator (v1, and the realistic v2 fridge, microwave, washer and
    background);
  - CSV replay of recorded data (bounded REFIT slices);
  - a validated local-sensor JSON endpoint, prepared for a future ESP32.
- **Planned: a public read-only demo.** Visitors could look at the dashboard and
  saved experiments but could not change the data source, upload files, retrain
  or post sensor readings. The app has no login today, and hosting (Render) is
  currently suspended. Before any public deployment, write endpoints must be
  disabled or protected, and private household recordings must not be exposed.

## Capabilities and Constraints

- **Live dashboard:**
  - aggregate power chart, energy and illustrative cost;
  - appliance cards with manual toggles;
  - a washing-machine card (simulated, not ML-detected);
  - detected change events, saved sessions and CSV export.
- **Experiments workbench:**
  - saved reports grouped as final test / development / other;
  - TESTED ON / TRAINED ON real-vs-synthetic badges and plain-language
    explanations;
  - an ON/OFF strip, actual-vs-predicted power, and a prediction-error chart.
- **Models:**
  - A live three-appliance random-forest model trained on synthetic data
    (lamp, fridge, microwave; manifest version `3132ae99ccd11d4c`).
  - Separate research models: fridge-only and washer-only; Decision Tree,
    Random Forest and always-off baselines.
  - Research models are never promoted automatically.
- **Stack constraint:** Python FastAPI backend with SQLite, and a plain
  HTML/CSS/JavaScript frontend with no framework or build step. Prefer simple,
  tested changes over new frameworks or rewrites. Old simulator modes and
  experiment protocols stay reproducible (versioned, opt-in changes).
- **Data rules:**
  - Timestamps and gaps are preserved, never silently interpolated.
  - Blank means unknown, not zero.
  - Appliance ground truth is used only for evaluation, never as a model input.
  - Recordings, models and reports live in ignored `data/` and are not in Git.
- **Out of scope for now:** physical sensing, ESP32 firmware, calibration and
  mains safety (deferred to the builder). Paid services are not enabled without
  asking.
- **Undecided:** the public demo's hosting, whether it gets authentication, and
  which saved experiments it exposes.

## Brand Commitments

- **Name:** "Current", full name "Current — Energy Profiler". The wordmark is
  "current." with a ϟ mark.
- **Visual constraint the builder asked for:** an Apple-inspired, fluid, clean
  look. It is currently implemented in `static/fluid.css` plus `static/apple.css`
  (see `docs/fluid-design.md`). A green accent is the existing identity.
- **Voice:** plain, direct and honest about uncertainty. It never overstates
  accuracy. Uncertainty and unexplained power are called heuristics, not
  detections.

## Evidence on Hand

- **Experiment write-ups** in `docs/`:
  - `fridge-development.md` (v1–v4);
  - `final-test.md` (House 5, scored once);
  - `washer-experiment.md`;
  - `simulator-fridge-v2.md`, `simulator-microwave-v2.md`,
    `simulator-background-v2.md`;
  - `washing-machine-profile.md`, `fridge-behaviour.md`,
    `experiment-visualization.md`.
- **Real data:** bounded REFIT slices (Houses 1–5; House 5 retired), cited from
  Zenodo 5063428.
- **Imagery:** Higgsfield-generated illustrations in `static/img/` (hero house,
  lamp, fridge, microwave, washer). These are illustrations, not photos of real
  or simulated appliances.
- **Absent — do not fabricate:**
  - users, testimonials, customers or deployments;
  - real-household accuracy beyond the documented REFIT results;
  - any hardware or sensor validation;
  - calibrated probabilities;
  - pricing or billing accuracy.

## Product Principles

1. **Evidence before polish.** Never let presentation imply more certainty than
   the data supports. Failures, limitations and "scored once" facts stay visible.
2. **Always say where the data came from.** Real vs synthetic, tested on vs
   trained on, is labelled wherever a result appears.
3. **Understandable in a minute.** Every metric has a plain-language reading a
   non-ML viewer can follow. Visuals (the ON/OFF strip, the error chart) beat
   bare numbers.
4. **Live picture and research lab carry equal weight.** Neither is hidden
   behind the other.
5. **Simple and reproducible.** Local-first, dependency-light, versioned
   protocols; one change at a time.

## Accessibility & Inclusion

Established practice to keep:
- keyboard focus and a skip link;
- reduced-motion, reduced-transparency and high-contrast fallbacks;
- text summaries and aria labels on charts;
- no page-level horizontal scrolling from 320 px up, with dense charts
  scrolling inside their own region;
- light and dark themes.

No formal conformance standard has been adopted.
