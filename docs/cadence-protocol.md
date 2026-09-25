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
