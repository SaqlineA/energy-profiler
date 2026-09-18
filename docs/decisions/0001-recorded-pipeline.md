# ADR-001: Keep the local stack; separate measurements from inference

Status: Implemented for local prototype; not approved for public deployment.
Date: 2026-09-16

## Context

The original app knew only synthetic one-second readings and a joint appliance
class. The next useful milestone is honest evaluation on recorded data, without
hardware purchases or adding a large research toolkit to the live backend.

## Decision

Keep FastAPI, SQLite, vanilla JavaScript, and scikit-learn. Use normalized CSV as
the first external source, nullable measured labels, explicit cadence, causal
five-point windows, and separate state/power outputs per appliance. Split raw
recordings before windowing; compare every model with same-test baselines.
Version model artifacts and save measurement/model provenance. Preserve legacy
database rows through an additive table migration.

## Alternatives and tradeoffs

- Full NILMTK integration: richer dataset support, but unnecessary runtime weight
  for the current three-appliance prototype. Borrow architecture, not source code.
- Centered sequence models: useful research baselines, but require future data
  and delayed predictions. Trailing windows make live alignment unambiguous.
- Filling gaps with zero: simpler charts, incorrect consumption semantics. Skip
  unobserved energy intervals and expose coverage instead.
- Immediate neural networks/GPU: greater complexity without an established
  real-data baseline. Keep forests and measure before changing model families.
- A public service: would require authentication, quotas, retention/deletion
  policy, hardened artifact management, and deployment review. Remain local-only.

## Consequences

Recordings require explicit column/unit mapping. No real dataset is bundled and
synthetic scores are not evidence of real-household detection. State probabilities
and residual-based abstention are heuristic; adding an appliance still requires
changing the schema, labels, and dashboard. Model files are trusted local joblib,
not safe upload formats. Old recordings and original learning exercises remain.
