# Refrigerator behaviour: simulators vs REFIT Houses 1 and 2

Question: *does the simulator produce refrigerator behaviour that resembles real
refrigerators?* This is description only. No model was trained or tuned, and the
fridge labels are used only to describe behaviour. `fridge_profile.py` refuses
any file under `data/holdout/`, so House 5 was not read.

```powershell
python fridge_profile.py
```

A fridge counts as on at 20 W or more, the same threshold as the experiments.
Cycle lengths count only runs whose start and end were both observed. A run next
to a gap longer than 60 s, or at the edge of a recording, is excluded, never
bridged. Real data is profiled at its native timing, not thinned to 16 s.

| | Live-model generator | Research simulator | REFIT House 1 | REFIT House 2 |
|---|---|---|---|---|
| Sampling | 1 s | 1 s | median 3 s, bursty | median 7 s |
| Fraction of time on (duty cycle) | 49% | 52% | 20% | 34% |
| On watts, p10 / p50 / p90 | 147 / 150 / 154 | 75 / 100 / 153 | 69 / 76 / 83 | 82 / 85 / 88 |
| Off watts (p50) | 0 | 0 | 0 | 1 |
| On cycle, minutes (p50) | 0.2 | 4.0 | 28 (7 cycles) | 26 (11 cycles) |
| Off period, minutes (p50) | 0.2 | 3.1 | 115 | 63 |
| Switch-on peak ÷ running median (p50) | 1.0 (none) | 2.4 | 1.4 | 1.2 |
| Variation while running (CV) | 0.0 | 0.1 | 0.1 | 0.0 |
| Fridge-channel step at switch-on (p50) | 150 W | 246 W | 109 W | 96 W |
| **Household total step at switch-on (p50)** | 149 W* | 244 W | **32 W** | **86 W** |
| Household total, p10 / p50 / p90 | 0 / 1,174 / 1,360 | 53 / 202 / 1,323 | 181 / 258 / 819 | 60 / 66 / 257 |

\*The generator switches every appliance at once every 10 s, so its household
total steps range from −1,064 to +1,362 W. The median simply falls on the fridge.

## Findings

1. **Neither simulator resembles a real fridge's timing.** Real compressor cycles
   run about 25–28 minutes, followed by 1–2 hours off. The research simulator
   cycles every 2–6 minutes, and the generator behind the live model (`3132ae99`)
   every 10 seconds. At a 16 s sampling rate, a five-reading window
   (64 s) almost always sits in a steady run in real data, while the simulated
   data is full of transitions.
2. **The simulated fridges are too large and too spiky.** Real fridges draw about
   76–85 W with a mild switch-on peak (about 1.2–1.4×). The research simulator
   draws 75–153 W with a 2.4× switch-on spike, and the live generator draws a flat
   150 W. The simulators' "off" value of 0 W is realistic.
3. **House 1 and House 2 fridges are similar** (76 vs 85 W, 26–28 min cycles).
   Their surroundings differ: median household totals are 258 vs 66 W. That
   matches the v2 false alarms.
4. **House 1's household total barely shows its fridge switching on.** In House
   2, the total rises by about the fridge's own step (86 vs 96 W). In House 1,
   the median rise is only 32 W against a 109 W step on the fridge channel,
   and it stays small even a few readings later (8 switch-ons inspected).
   In several examples, the total rose by 20–60 W while the fridge plug read
   85–110 W. The cause is not known. Possibilities include the whole-house
   clamp and the plug monitor measuring differently, or timing or alignment
   differences between them. This is a small sample and is not a verified
   explanation. If it is real, a House 1 model learns that a small household
   rise means "fridge on", which would not transfer to House 2.

## What this means for the final Step 10 experiment

- The simulator is unrealistic for fridges, in timing most of all. Synthetic
  scores such as the 0.880 fridge F1 in the cadence experiment and the live
  model's 1.000 fridge F1 do not describe real fridges.
- The houses differ in background load (House 1 higher) and in how clearly the
  fridge appears in the household total. The fridges themselves are similar.
- The findings point to two separate next steps. Training on more than one
  house would dilute House 1's weak switch-on signature, but that needs more
  REFIT data downloaded. Making the simulator's fridge realistic (25–30 min on,
  1–2 h off, about 80 W, mild peak) should be done separately.
  Neither has been done yet, and House 5 remains unscored.
