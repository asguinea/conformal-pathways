# Four-batch roadmap

## Batch 1 — Independent foundation

Create a separate repository and package namespace, selectively migrate code and
synthetic tests, declare and lock dependencies, add an offline demo, and record
scope, behavioral contracts, claims, and asset provenance.

Acceptance: a distribution installs in an isolated environment and runs from
outside the checkout without external datasets or local project dependencies.
Record test results and all remaining limitations. Ownership confirmation may
remain pending; public distribution remains gated on it.

## Batch 2 — Correctness

Resolve R1–R11 in the [behavioral contract](behavioral-contract.md), prioritizing
information flow, label semantics, calibration, metric denominators, and exact
baselines. Derive tests independently from the contract, including exhaustive
checks for the small workflows. Change or remove scientifically misleading APIs.

Acceptance: the implemented algorithm and stated assumptions agree; regression
tests expose the previous failures and pass after correction. Any intended
guarantee has a precise event, justified assumptions, and a supporting argument.
Unsupported capabilities are explicitly reduced or removed.

## Batch 3 — Reproducible evidence

Freeze a protocol and configurations. Run synthetic mechanism checks and any
eligible dataset benchmarks from identified inputs. Record split membership,
weights, transforms, cache identity, code/environment versions, compute, and
failures. Produce uncertainty estimates and fair baseline comparisons from
recomputable records. Update the claim register only with actual evidence.

Acceptance: a clean run regenerates each promoted result within declared
tolerances, with no unsupported quantitative claim.

## Batch 4 — Public release preparation

Finish documentation and examples, CI, formatting and type checks, contribution
guidance, licensing and attribution, release metadata, and privacy/security
review of the complete distribution and new Git history. Exercise the public
quick start in a clean checkout and verify external data instructions.

Acceptance: a reviewable release candidate with all public claims supported and
all distributed assets cleared. Remove the development-only upload classifier
only at this stage. Creating a remote repository, pushing, or publishing a
release is a separate owner decision.
