# Software roadmap checklist

- [x] Days 1–3: document replay flow, convert 200 real rows, verify replay totals.
- [x] Days 4–5: frozen-model evaluation, partial-label metrics and limitations.
- [x] Days 6–7: seeded realistic simulation with background/noise/overlap.
- [x] Days 8–10: configurable windows/features and reproducible comparisons.
- [x] Days 11–12: actual/predicted, experiments, quality and session analytics.
- [x] Day 13: experimental multi-stage washing machine and overlap tests.
- [x] Day 14: validated simulator-independent sensor reading contract.
- [x] Final checkpoint: tests, browser verification and learner documentation.

Verification: 48 core tests + 4 research tests; JS syntax checks, pip check,
independent real 200-row integration, desktop and 390px mobile browser checks.
The mobile grid overflow found during verification was fixed. Saved evaluation
was exercised through the UI; original live model version remains unchanged.
Results and limitations: `docs/software-roadmap.md`. Changes are local, not deployed.

Days 15–18 physical integration and validation: deferred to the user.
Graphify generation is paused; it is not an implementation prerequisite.
