# Cadence-matched experiment protocol v1

This protocol is fixed before running the comparison. The question is whether
the existing experimental models can learn from and be evaluated on the same
physical time span. This is a synthetic benchmark, not a real-house accuracy claim.

- Generate 10 independent training sessions using seed 42, and three evaluation
  sessions using seed 70042. Each session is 1,800 seconds. The simulator adds
  997 per session to the seed; training and evaluation seeds do not overlap.
- Keep every eighth original one-second sample, including its timestamp and
  appliance labels. These are instantaneous subsamples, not eight-second means;
  short events can be missed. Never relabel one-second data as eight-second data.
- Train three candidates: always-off, depth-limited Decision Tree, and the
  existing 40-tree Random Forest. Keep five readings and summary features fixed.
  Each complete window represents 32 seconds. No hyperparameter search.
- Use strict eight-second evaluation, resetting history at session boundaries,
  missing aggregate readings, gaps and irregular intervals using existing rules.
  All candidates must score identical timestamps and equal energy coverage.
- Record F1, positive/negative support, MAE, energy error and coverage together.
  Metrics score raw estimates before abstention, as in the existing evaluator.
- Save reports in ignored experiment storage, compatible with dashboard history.
  Never write or promote a live model. Record protocol, seeds, source hashes and
  library version so the comparison is reproducible.

House 2 is **not an untouched final test**: its prefix has already been inspected.
Do not use its results to tune this comparison. A later real-data trial must
declare its training/development houses and a genuinely untouched final recording.
No interpolation or gap-filling of REFIT is authorized by this protocol.

## Run and inspect

```powershell
python cadence_comparison.py
```

Open dashboard **Experiments → Refresh history**, then choose a report named
`Cadence v1 / ... / synthetic 8s`. This uses the existing charts and metrics;
no new server route or frontend dependency is needed. Reports are local to the
machine running the command; Git does not transfer them into a Codespace.

## First fixed run (2026-09-25)

Each model trained on 2,210 windows and scored the same 663 held-out windows
from three sessions. Energy comparison covers 5,280 seconds, excluding warmup
and session boundaries. All feature windows span exactly 32 seconds.

| Model | Fridge F1 | Fridge MAE W | Fridge absolute energy error kWh | Lamp F1 | Microwave F1 |
|---|---:|---:|---:|---:|---:|
| Always off | 0.000 | 84.74 | 0.12383 | 0.000 | 0.000 |
| Decision Tree | 0.863 | 45.57 | 0.02874 | 0.484 | 1.000 |
| Random Forest | 0.880 | 43.68 | 0.02614 | 0.539 | 1.000 |

Fridge on/off support is 319/344. Random Forest estimates 0.09769 kWh against
0.12383 kWh measured by the simulator, about 21% low, and only 183 of 663 fridge
predictions pass the existing uncertainty heuristic. Signed errors can cancel
in total energy. Lamp MAE is worse than always-off for both learned models.
Perfect microwave F1 here reflects a limited synthetic benchmark, not real-world
perfection. No live model was changed, and no House 2 data entered fitting.

Next checkpoint: declare real-data development/training partitions and an
untouched evaluation recording, then test without silently interpolating irregular
samples. Cadence matching fixes a methodology problem; it does not fix the
simulator-to-household domain gap or establish sensor calibration.
