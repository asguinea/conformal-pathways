# Claim register

Status at version 0.4.0. Implementation evidence and empirical benchmark
evidence have different scopes.

| ID | Statement | Status | Evidence / remaining requirement |
| --- | --- | --- | --- |
| C1 | Installs independently and runs generated-data examples | Verified in the recorded environment | [Release distribution and test record](release-verification.md); [earlier verification](batch-2-verification.md) |
| C2 | Supplies two small three-stage workflows and a shared evaluation harness | Implemented and exercised | 18 complete paths each; synthetic and generated-image integration tests |
| C3 | Built-in decision inputs respect declared observation timing | Contract tests pass | Entry-only baseline uses entry evidence; sequential sessions accept results only after test commitment. Hidden-label perturbation and pending/replay/skip checks; real observation timing still needs source verification |
| C4 | Reference retention has a marginal guarantee under stated exchangeability assumptions | Mathematical arguments and construction checks provided | [Entry-only method](method.md) and [result-aware method](sequential-method.md): group maxima, corrected ranks, fixed budgets, ties, union bound. Dataset exchangeability and true grouping are not established |
| C5 | Metrics implement the declared toy predicates and denominators | Independently checked | Exhaustive truth tables, mixed cohorts, missing-label/abstention fixtures, aggregate/per-case agreement |
| C6 | A selected path is clinically safe or improves outcomes | Unsupported; outside scope | The toy predicates and retrospective proxies cannot establish this |
| C7 | Universally outperforms the model-only baseline | Not established | [Sequential comparisons](batch-3-sequential-results.md) show setting-specific retention/selection benefits on IDRiD, with more testing, and equal promoted perfect-proxy outcomes on RIM-ONE. The [entry-only evidence](batch-3-v2-results.md) describes a different protocol |
| C8 | Image caches identify and validate their inputs and model request | Verified on the recorded CPU environment | Integrity/staleness checks, explicit seeds, no weight fallback; both real feature matrices independently re-extracted exactly. Accelerator and cross-platform behavior remain unverified |
| C9 | Project release contents reviewed for public distribution | Reviewed for the stated asset boundary | Apache-2.0 selected by the maintainer; code/history/distribution and dependency review in [release verification](release-verification.md) and [provenance](provenance.md). External data and model rights are not granted |
| C10 | Supplies a reproducible synthetic benchmark under a frozen protocol | Verified on one host | 5,760 records, 448 summary rows, 384 paired rows; all 5,760 records reproduce exactly from an isolated installed wheel. [Verification](batch-3-v2-verification.md), [results](../evidence/batch3-v2/README.md) and [interpretation](batch-3-results.md). V2 preserves these synthetic outcomes exactly under its disclosed [input amendment](batch3-v2-amendment.md) |
| C11 | Supplies reproducible real-image descriptive experiments | Verified on one host | All 80 records and case outcomes reproduce exactly, with bit-for-bit identical fresh features. [V2 verification](batch-3-v2-verification.md). No patient-level coverage claim; IDRiD mean inclusion is below nominal |
| C12 | Diagnostic results can change subsequent decisions, with matched reference calibration | Implemented and checked with generated fixtures | [Sequential contract](sequential-method.md) and [verification](batch-2-sequential-verification.md): result-aware sessions, missing/noisy scenarios, grouped reference scores, execution traces, exact reaggregation |
| C13 | Diagnostic information can change downstream behavior and selected toy violations in the specified simulations | Descriptively supported; not a universal or clinical claim | [Results and limitations](batch-3-sequential-results.md) distinguish information, filtering, test usage and abstention. Errors can worsen results; the unpruned informed selector already performs similarly on some outcomes |
| C14 | Supplies reproducible result-aware synthetic and real-image simulations | Verified on one host | 11,392 synthetic and 400 real-image comparison records reproduce exactly, with identical fresh features. [Verification](batch-3-sequential-verification.md) and [complete evidence](../evidence/batch3-sequential-v1/README.md). Dataset exchangeability, real diagnostic responses and clinical benefit remain unverified |

The `safety` module and metric names containing `safe` refer only to the
[toy predicates](toy-rules.md). A selected-path violation rate is conditional on
an evaluable, non-abstaining selection. Reference inclusion, existence of an
acceptable candidate, and absence of violating candidates are distinct events.
Result-aware stage decisions use fixed thresholds and a fixed predictor. Their
retention argument concerns marginal reference reachability, not conditional
coverage along the deployed selector's history or selected-path safety. Online
calibration and sequential learning are not supported. C10/C11 describe
the earlier entry-only evidence; the separate result-aware argument and
assumptions are given in [sequential method](sequential-method.md).

Each future quantitative claim must link to a frozen configuration, code
revision, identified dataset/model/environment, split IDs, appropriately handled
raw records, and commands regenerating its aggregation and uncertainty estimate.
Report exclusions and failures. Repeated random splits are not independent
patients. A successful test suite alone is insufficient to promote a performance
or clinical claim.
