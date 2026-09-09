# Four-batch roadmap

## Batch 1 — Independent foundation (complete)

Create a separate repository and package namespace, selectively migrate code and
synthetic tests, declare and lock dependencies, add an offline demo, and record
scope, behavioral contracts, claims, and asset provenance.

Acceptance: a distribution installs in an isolated environment and runs from
outside the checkout without external datasets or local project dependencies.
Record test results and all remaining limitations. Ownership confirmation may
remain pending; public distribution remains gated on it.

## Batch 2 — Correctness (entry baseline and sequential extension complete)

Resolve R1–R11 in the [behavioral contract](behavioral-contract.md), prioritizing
information flow, label semantics, calibration, metric denominators, and exact
baselines. Derive tests independently from the contract, including exhaustive
checks for the small workflows. Change or remove scientifically misleading APIs.

Acceptance: the implemented algorithm and stated assumptions agree; regression
tests expose the previous failures and pass after correction. Any intended
guarantee has a precise event, justified assumptions, and a supporting argument.
The intended staged behavior includes executing a diagnostic, receiving its
result, and updating later decisions. The original entry-only implementation
and verification did not complete that requirement. Version 0.4.0.dev0 adds the
[sequential contract](sequential-method.md), result-aware calibration and
execution, information-flow checks, and reproducible fixture exports. See the
[extension verification](batch-2-sequential-verification.md). This preserves the
earlier corrections and baseline instead of replacing their recorded evidence.

## Batch 3 — Reproducible evidence (entry baseline complete; sequential runs pending)

Freeze a protocol and configurations. Run synthetic mechanism checks and any
eligible dataset benchmarks from identified inputs. Record split membership,
weights, transforms, cache identity, code/environment versions, compute, and
failures. Produce uncertainty estimates and fair baseline comparisons from
recomputable records. Update the claim register only with actual evidence.

Entry-only baseline acceptance met on the recorded host: 5,760 synthetic and 80 real-image records
reproduce exactly from independent installed-wheel environments, including
fresh real features. The [v2 amendment](batch3-v2-amendment.md) resolves the
IDRiD duplicate/label-conflict blocker through disclosed manifest exclusions
and a new source/input freeze. The original files and v1 evidence are preserved.
All 5,840 compact records regenerate 576 summary and 480 paired rows. Negative
findings, including below-nominal IDRiD reference inclusion, are retained;
no clinical-safety or superiority claim is promoted. See
[verification](batch-3-v2-verification.md) and
[results and limitations](batch-3-v2-results.md).

Next: freeze a separate protocol for `result-aware-pathways-v1`; compare the
result-aware selectors with the entry-only baseline using the same eligible
cohorts, splits, and model predictions where applicable. Pre-specify diagnostic
simulation, missing/error-result sensitivity, action/test usage, reference
retention, existential toy acceptability, selected violations, and abstention
denominators. Run and reproduce those experiments before making quantitative
claims about result-aware decisions. Existing data audits, filtered manifests,
feature verification, and entry-only evidence remain useful completed work.
No new sequential benchmark is implied by the Batch 2 fixtures.

The entry-only source snapshot is `baseline-entry-v2` (`1a798b9`). Its frozen
protocol must be executed from that matching source and wheel. Do not refresh
its source lock to make a new algorithm appear to reproduce the old experiment.

## Batch 4 — Public release preparation

Finish documentation and examples, CI, formatting and type checks, contribution
guidance, licensing and attribution, release metadata, and privacy/security
review of the complete distribution and new Git history. Exercise the public
quick start in a clean checkout and verify external data instructions.

Acceptance: a reviewable release candidate with all public claims supported and
all distributed assets cleared. Remove the development-only upload classifier
only at this stage. Creating a remote repository, pushing, or publishing a
release is a separate owner decision.
