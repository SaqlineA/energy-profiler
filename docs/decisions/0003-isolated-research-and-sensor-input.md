# ADR-003: Isolate research models and normalize local sensor input

Status: Implemented for local learning; physical integration deferred.
Date: 2026-09-22

## Context

REFIT sampling does not match the original one-second live model. Replacing the
model or relaxing live timing would disguise that mismatch. Simulator improvements
also need comparisons against unchanged baselines, including simple rules.

## Decision

Keep strict live inference and the existing artifact. Save frozen diagnostic and
research results separately as JSON. Explicitly label native-sample diagnostics
as non-equivalent time windows. Compare experimental models after the same warmup,
with disjoint generated sessions, partial-label metrics and coverage-aware energy.
Use a separate experimental washer model rather than silently extending three-device
artifact compatibility. Add sensor input through the same processing path, with
bounded JSON, monotonic aware timestamps, no invented truth and unchanged loopback
and same-origin protections. Extend SQLite additively for nullable washer readings.

## Alternatives and tradeoffs

- Automatically resampling REFIT to one second would invent intermediate evidence;
  diagnostics preserve native samples instead and cannot establish live validity.
- Promoting a best-looking model on 200 rows would overfit the evaluation sample.
- A separate sensor backend would duplicate timing and energy behavior.
- Public ingestion would require authentication and deployment work beyond this
  software-only milestone; local ingestion is preparation, not a finished IoT link.

## Consequences

Saved experiments are local files and need manual retention/backups. UI metrics
must distinguish synthetic performance, diagnostic results and real validation.
Physical access and accuracy still require separate engineering and testing.
