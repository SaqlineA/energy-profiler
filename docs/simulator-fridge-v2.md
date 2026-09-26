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

## Result (2026-09-26)

```powershell
python fridge_profile.py
```

Both simulator versions were profiled with the same four 12-hour sessions
(seed 42, one-second samples). The real houses are at their native timing.
The shorter v1 profile (ten 30-minute sessions) is still reported for continuity.

| | Sim v1 | **Sim v2** | House 1 | House 2 | House 3 | House 4 | Pass |
|---|---:|---:|---:|---:|---:|---:|:---:|
| Running W, p50 | 92 | **85** | 76 | 85 | 99 | 51 | ✅ 51–99 |
| On cycle, min p50 | 4.0 | **27.6** | 28.2 | 25.6 | 40.1 | 0.4* | ✅ 24–40 |
| Off period, min p50 | 3.5 | **89.4** | 115 | 63 | 73 | 10* | ✅ 60–120 |
| Startup peak ÷ median, p50 | 2.3 | **1.3** | 1.4 | 1.2 | 1.2 | 1.0 | ✅ ≤1.5 |
| Running variation, CV p50 | 0.1 | **0.0** | 0.1 | 0.0 | 0.0 | 0.0 | ✅ ≤0.1 |
| Duty cycle | 0.51 | **0.22** | 0.20 | 0.34 | 0.40 | 0.22 | ✅ 0.2–0.4 |
| Fridge step at switch-on, p50 | 203 W | **103 W** | 109 | 96 | 119 | 24* | — |
| Household total step at switch-on, p50 | 204 W | **105 W** | 32 | 86 | 0 | 0 | not addressed |

\*House 4's 51 W fridge dips across the 20 W threshold, which splits its cycles.

**All six preregistered realism checks pass**, and v2 is at least as close as
v1 on every one. The biggest gains are in timing: cycles are about 7× longer
and off periods about 25× longer, matching real compressors. The startup spike
is realistic and the running power is tighter.

`realistic_sessions(..., fridge='v1')`, the default, produces byte-identical
sessions to the previous code. This was verified against `HEAD` for plain and
washer sessions, so every earlier experiment still reproduces.
`test_realistic.py` checks v2's cycle bounds and mild startup.

**Not changed, and not claimed:**
- ML accuracy was not measured. Whether v2 synthetic data helps or hurts needs
  a new untouched REFIT house, because House 5 is spent.
- The switch-on step in the household total is still clean in the simulator. In
  real Houses 1, 3 and 4 it is small or absent, and that is unexplained.
- There is no slow power decline within a cycle and no defrost cycles. Every
  home's fridge is 80–90 W, but real fridges range from about 50 to 100 W.
- The live model (`3132ae99ccd11d4c`) and its generator are unchanged.
- Short sessions (for example 30 minutes) now often contain no fridge
  transition at all. That is realistic, but training runs that use v2 need
  sessions lasting hours.
