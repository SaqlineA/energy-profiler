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
