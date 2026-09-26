# Research simulator fridge v2 (Step 13)

Written before the simulator was changed. This is a realism fix, not an ML
change. It is done because the v1 fridge is unrealistic
([fridge-behaviour.md](fridge-behaviour.md)), not because it is known to improve
accuracy. v1 stays the default (`fridge='v1'`), so every earlier seed, test and
report still reproduces. v2 is opt-in (`fridge='v2'`). The live model is not
retrained or replaced.

## Target behaviour (from REFIT Houses 1–4 only; House 5 is not used)

| Behaviour | Houses 1–4 observed | v2 target |
|---|---|---|
| Running power, p50 | 76, 85, 99, 51 W | about 80–90 W per home |
| On cycle, p50 | 28, 26, 40 min (House 4 cycles split by threshold dips) | 25–30 min |
| Off period, p50 | 115, 63, 73 min | 60–120 min |
| Switch-on peak ÷ running median, p50 | 1.4, 1.2, 1.2, 1.0 | mild, about 1.1–1.4× for the first few seconds |
| Variation while running (CV, p50) | 0.0–0.1 | same small noise as v1 (3.5%) |
| Duty cycle | 0.20–0.40 | follows from the cycles (about 0.2–0.3) |

## Acceptance (realism only, decided now)

When profiled with `fridge_profile.py`, v2 passes if **every** item below lands
within the range seen in Houses 1–4 (widened slightly where noted) and is at
least as close to it as v1:

- Running-power p50: 51–99 W.
- On-cycle p50: 24–40 min.
- Off-period p50: 60–120 min.
- Startup peak p50: at most 1.5×.
- Running variation (CV) p50: at most 0.1.
- Duty cycle: 0.2–0.4.

Known remaining gaps, which are out of scope here:
- The simulator's household total still changes by the whole fridge step at
  switch-on. Houses 1, 3 and 4 do not show that.
- Real fridges show slow power decline across a cycle and occasional
  defrost behaviour.
- Other appliances and the background load are unchanged.
