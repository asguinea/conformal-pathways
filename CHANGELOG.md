# Changelog

## 0.4.0 — 2026-09-09

First public research release of Conformal Pathways.

- Result-aware sessions commit diagnostic actions before receiving results and
  update later decisions using fixed predictors and calibration thresholds.
- Group-aware calibration, reference-retention arguments, exhaustive toy-rule
  checks, and separate reference, selection, abstention, and test-use metrics.
- Frozen synthetic and descriptive real-image benchmarks with diagnostic-error
  and unavailability controls, paired ablations, and exact same-host reproduction.
- Apache-2.0 licensing, contribution and security guidance, software citation,
  locked dependencies, CI, and distribution checks.

The package's scientific Python source is byte-identical to the independently
verified `sequential-benchmark-v1` snapshot (0.4.0.dev0). Release metadata and
development tooling changed; numerical results were not rerun or relabeled.
Use the original tags and locks to reproduce recorded experiments.

The workflows and diagnostic outcomes are illustrative simulations. The results
do not establish clinical safety, actual diagnostic accuracy, patient-level
exchangeability, or universal superiority. See
[results and limitations](docs/batch-3-sequential-results.md).
