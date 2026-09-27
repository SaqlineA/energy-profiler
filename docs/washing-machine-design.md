# Simulated washing machine v2: design (Step 15B)

Written and committed before implementation. It is based on the real profile in
[washing-machine-profile.md](washing-machine-profile.md). The goal is a
reasonable educational multi-stage appliance, not a copy of any one real washer.

## Compatibility

- `RealisticHome(washer=False)` (the default) and `washer=True` (the existing
  compressed v1 washer) stay byte-identical, so every earlier seed, test and
  report still reproduces.
- The new model is opt-in: `washer='v2'`, also accepted by
  `realistic_sessions(..., washer='v2')`.
- v2 draws from **its own seeded random generator**, derived from the home's
  seed. Adding it never changes the lamp, fridge, microwave, background or noise
  values. The household total with the washer is exactly the total without it
  plus the washer's watts, apart from rounding.
- The research simulator's washer device (`WASHER`, 10 W threshold) and the live
  three-appliance model are unchanged. No ML detection is added in Step 15.

## State machine

The only allowed order is:
`off → fill → heat → wash → pause → drain → spin → off`.

Each state's duration and settings are drawn once, when the state starts. One
sample is one simulated second.

| State | Duration | Power | Variation | Based on |
|---|---|---|---|---|
| **off** | Until the next scheduled start | 0 W | none | REFIT idle is 0 W |
| **fill** | 2–5 min | Inlet valve 8–12 W, plus a slow tumble every 20–40 s lasting 5–10 s at 40–90 W | ±5% noise | The low flicker before heating |
| **heat** | 8–18 min | One heater level per home, 2,000–2,500 W | ±2% noise | 1.9–2.6 kW blocks lasting 5–18 min in 37/38 cycles |
| **wash** | 15–60 min | Drum reversals: on 8–15 s at 100–250 W, off 3–8 s at about 5 W | ±5% noise | The dense 20–250 W flicker |
| **pause** | 1–5 min | 2 W (electronics) | none | Near-zero pauses |
| **drain** | 1–3 min | Pump at 30–60 W (drawn per cycle) | ±5% noise | Low steady segments |
| **spin** | 3–10 min | Rises from 150 W to a peak of 300–550 W over the first half, then holds | ±5% noise | The 250–550 W final spin |

**Schedule:**
- The first cycle starts 2–10 minutes into a session, so it can be seen in the
  dashboard. This is a demo convenience, not a realistic habit.
- After each cycle ends, the next one starts 36–120 hours later, which averages
  about 0.3 cycles per day (REFIT: 0.19–0.57).
- A full cycle lasts about 30–100 minutes (REFIT p50: 32–140) and uses about
  0.3–0.8 kWh (REFIT p50: 0.3–0.9).

**Saved state:**
- `RealisticHome.wash_stage` holds the current state name.
- Each v2 simulator reading carries `washing_machine_stage`, which is stored in a
  new nullable SQLite column (an additive migration, like `washing_machine`).
- CSV export gains that column.
- Replay and sensor readings leave it empty.

**Dashboard:**
- A new simulation profile, *Realistic v2: real-data fridge + washing machine*,
  uses fridge v2 and washer v2 together. It is a demo profile, not an experiment.
- Its washer card shows running or off, the phase, the measured watts and the
  minutes into the cycle.
- The existing *expanded* profile keeps the v1 washer.

## Acceptance checks (decided now)

Simulate 14 days for each of two homes (seeds 42 and 1039), and profile the
washer channel with `washer_profile.profile` using the same thresholds as for
real data. v2 passes if all of these hold:

- Cycle length p50 is 30–140 min.
- Peak p50 is 1,900–2,700 W.
- Every cycle includes heating, with a heat-band p50 of 5–18 min.
- Energy per cycle p50 is 0.3–0.9 kWh.
- Idle power p50 is 0 W.
- There are 0.15–0.65 cycles per day.
- Non-heating active watts: p50 is 60–140 W and p99 is at most 600 W.

**Tests:**
- The states run in the allowed order, with no impossible jumps such as
  `off → spin`.
- Every state's watts stay inside its range.
- v1 and no-washer sessions are byte-identical to before.
- The household total includes the washer.
- The stage is saved in storage.
- A cycle finishes and the washer returns to off.

## Known simplifications

- There is one wash and one final spin. Real machines repeat rinse, drain and
  short spins several times.
- Every cycle heats; some real cycles are cold washes.
- Drum reversals are regular. Real motor current also has
  startup surges and load-dependent variation.
- There is no washer-dryer, no standby display load, and no link between the
  washer schedule and time of day.
