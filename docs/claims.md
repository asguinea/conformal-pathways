# Claim register

Status at version 0.3.0.dev0. Implementation evidence and empirical benchmark
evidence have different scopes.

| ID | Statement | Status | Evidence / remaining requirement |
| --- | --- | --- | --- |
| C1 | Installs independently and runs generated-data examples | Verified in the recorded environment | [Distribution and test record](batch-2-verification.md) |
| C2 | Supplies two small three-stage workflows and a shared evaluation harness | Implemented and exercised | 18 complete paths each; synthetic and generated-image integration tests |
| C3 | Built-in prediction, candidate construction, and selection use declared entry information | Contract tests pass | Label-free inference type; direct/indirect hidden-label perturbations; diagnostic provenance tests. Real observation timing still needs source verification |
| C4 | Reference paths have a specified conditional coverage statement | Mathematical argument and construction checks provided | [Method](method.md): group maxima, corrected ranks, fixed budgets, ties, union bound. Dataset exchangeability and true grouping are not established |
| C5 | Metrics implement the declared toy predicates and denominators | Independently checked | Exhaustive truth tables, mixed cohorts, missing-label/abstention fixtures, aggregate/per-case agreement |
| C6 | A selected path is clinically safe or improves outcomes | Unsupported; outside scope | The toy predicates and retrospective proxies cannot establish this |
| C7 | Outperforms the model-only baseline | Not established | [Prespecified synthetic comparisons](batch-3-results.md) do not establish an advantage for `main`; no real-image result is available |
| C8 | Image caches identify and validate their inputs and model request | Implemented; generated-image CPU tests pass | Integrity/staleness checks, explicit seeds, no weight fallback. Real pretrained extraction, accelerator behavior, and full experiment reproduction remain unverified |
| C9 | Cleared for public redistribution | Pending | Ownership, license, attribution, and final distributed-asset/history review |
| C10 | Supplies a reproducible synthetic benchmark under a frozen protocol | Verified on one host | 5,760 records, 448 summary rows, 384 paired rows; all 5,760 records reproduce exactly from an isolated installed wheel. [Verification](batch-3-verification.md), [results](../evidence/batch3-v1/README.md) and [interpretation](batch-3-results.md). Real-data suite blocked by [duplicate images and label conflicts](batch-3-input-audit.md) |

The `safety` module and metric names containing `safe` refer only to the
[toy predicates](toy-rules.md). A selected-path violation rate is conditional on
an evaluable, non-abstaining selection. Reference inclusion, existence of an
acceptable candidate, and absence of violating candidates are distinct events.
Adaptive replanning and online conformal validity are not supported capabilities.

Each future quantitative claim must link to a frozen configuration, code
revision, identified dataset/model/environment, split IDs, appropriately handled
raw records, and commands regenerating its aggregation and uncertainty estimate.
Report exclusions and failures. Repeated random splits are not independent
patients. A successful test suite alone is insufficient to promote a performance
or clinical claim.
