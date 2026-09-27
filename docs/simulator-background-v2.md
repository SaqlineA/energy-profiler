# Research simulator background v2 (unmetered load)

Written before the code change. Everything in a simulated home that is not a
modelled appliance (lamp, fridge, microwave, washer) is *background*: always-on
baseload plus unmetered devices such as lights, TV, computers and kettles. The
fixed 80 W "unknown" load that v1 switches on for 40 s every 4 minutes has no
real counterpart.

## Real behaviour (REFIT Houses 1–4; House 5 retired)

The data is the 20 MB slices in `data/refit/washer/`. *Unmetered* means the
household total minus all nine plug-metered channels. *Baseload* is the lowest
household total in each hour. *Rises* are increases in unmetered power between
consecutive readings no more than 30 s apart.

| | House 1 | House 2 | House 3 | House 4 |
|---|---:|---:|---:|---:|
| Baseload p50 | 180 | 68 | 106 | 109 |
| Unmetered p10 / p50 / p90 / p99 (W) | 107 / 179 / 553 / 2,304 | 57 / 68 / 275 / 3,087 | −75 / 52 / 539 / 2,131 | 54 / 136 / 419 / 3,187 |
| Rises of 200–1,000 W per day | 94 | 45 | 57 | 64 |
| Rises above 1 kW per day | 34 | 35 | 22 | 25 |

House 3's unmetered value is negative 30% of the time. The whole-house clamp
and the plugs disagree there, as seen before for the fridge. Rise counts are
approximate: a cycling heater counts several times.

## v2 design

- **Opt-in:** `RealisticHome(background='v2')` and
  `realistic_sessions(..., background='v2')`. v1 stays byte-identical.
- **Own random generator.** v2 still makes v1's background random draws and
  ignores them, so the lamp, fridge, microwave and washer produce **identical**
  values under both background versions. Only the unmetered load changes.
- **Baseload:** one level per home, 60–180 W, which drifts slowly within
  ±20% of that level.
- **Medium unmetered loads** (lights, TV, computers): each home has a rate of
  50–100 starts per day. Each load adds 100–600 W for a log-uniform 1–30 min.
  They can overlap.
- **Large unmetered loads** (kettle, oven, toaster, iron): each home has a rate
  of 15–30 starts per day. Each adds 1,000–3,000 W for a log-uniform 1–10 min.
  These can look like washer heating on purpose, because real homes have
  kettles.
- The periodic 80 W load and v1's 20–120 W random walk are not used in v2.
  The ±2 W sensor noise stays.
- **The `household` dashboard profile** switches to background v2.

## Acceptance (decided now)

Simulate 14 days for each of two homes (seeds 42 and 1039). Compute *unmetered*
as the total minus lamp, fridge, microwave and washer, and use the same metrics
as for the real houses. v2 passes if:

- Baseload p50 is 60–180 W.
- Unmetered p50 is 50–180 W.
- Unmetered p90 is 275–555 W.
- Unmetered p99 is 2,100–3,200 W.
- Rises of 200–1,000 W number 45–95 per day.
- Rises above 1 kW number 20–35 per day.
- v1 fingerprints are unchanged.
- The labelled appliances are identical under background v1 and v2.

**Known simplifications:**
- Loads start at the same rate at every hour of the day; real homes are quieter
  at night.
- Loads are flat steps: no thermostat cycling, no dimmers, no motors.
- There is no seasonal heating.

## Result (2026-09-26)

Two homes (seeds 42 and 1039) were each simulated for 14 days, with fridge,
microwave and washer v2 running.

**First run (as designed): 7 of 12 checks passed.** Unmetered p90 was 864 and
675 W, p50 was 183 W (seed 42), 200–1,000 W rises were 43 per day (seed 1039)
and >1 kW rises were 18 per day (seed 42). The cause was that medium loads were
sized from their *median* duration. Long runs pull the average up to about
8.5 min, so a medium load was running about 44% of the time.

**One documented revision:**
- Medium loads: 1–30 min → 1–10 min, and 50–100 → 60–120 starts per day.
- Large loads: 1–10 min → 1–5 min, and 15–30 → 20–35 starts per day.

It was not tuned further after that.

| Check | Target | Seed 42 | Seed 1039 |
|---|---|---:|---:|
| Baseload p50 | 60–180 W | 147 ✅ | 103 ✅ |
| Unmetered p50 | 50–180 W | 173 ✅ | 123 ✅ |
| Unmetered p90 | 275–555 W | **677 ❌** | 548 ✅ |
| Unmetered p99 | 2,100–3,200 W | 2,719 ✅ | 2,779 ✅ |
| Rises 200–1,000 W per day | 45–95 | 88 ✅ | 51 ✅ |
| Rises above 1 kW per day | 20–35 | 22 ✅ | 27 ✅ |

**Verdict: partial pass, 11 of 12 checks.** Seed 42's simulated home is busier
at its 90th percentile than any of the four real homes (677 vs at most 553 W).
This is left as measured. For comparison, v1 had an unmetered p90 of about
190 W and p99 of about 265 W, with **no** rises above 200 W.

**Checks:**
- v1 fingerprints are unchanged.
- The labelled appliances (lamp, fridge, microwave, washer) are identical under
  background v1 and v2 over a simulated day.
- Unmetered load never falls below the baseload floor, and kettle-sized loads
  appear within a day (`test_realistic.py`).
- The `household` dashboard profile now uses fridge, microwave, washer and
  background v2 (`test_project.py`).

**Why this matters for the washer experiment.** Kettle-, oven- and
iron-sized loads (1–3 kW for 1–5 min) now occur 20–35 times a day. They share
the washer's 2 kW heating level but are shorter than its 10–15 min heating
block, so a detector has to use duration and shape, not power alone. This is
closer to the real problem. It also means the earlier "washer is visible in a
quiet window" plots are an optimistic case.
