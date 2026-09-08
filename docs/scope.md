# Scope

Conformal Pathways is a research software project for studying how uncertainty,
observation timing, and explicit rules affect sets of candidate decisions in
small branching workflows. The immediate goal is a reproducible and auditable
experimental implementation.

## What exists

Two illustrative workflows enumerate diagnostic, management, and follow-up
actions. The code includes group-aware splitting, a class-prior predictor,
optional logistic regression on cached image embeddings, stage-wise scoring,
path filtering, selection policies, and metrics. All scientific APIs remain
experimental. This version builds open-loop sets using entry observations; it
does not evaluate contingent treatment policies or recalibrate after a new test
result. Explicit diagnostic state transitions are separate building blocks.

The synthetic demo exercises a complete train/calibrate/evaluate pipeline.
Its labels are randomly generated; its predictor returns training-class
frequencies for every example. It establishes that the software runs, not
that uncertainty is informative or that a clinical recommendation is correct.

## Boundaries

- A rule predicate describes a specified toy model. It does not establish
  guideline compliance or patient safety without external validation.
- A reference-path inclusion event differs from the existence of an acceptable
  path, the absence of unacceptable paths, and the acceptability of a selected
  path. These require separate evidence.
- Dataset labels may be retrospective proxies. A grading label is not a
  recorded response to a diagnostic action or a treatment-outcome label.
- There are no validated performance numbers in this version. New experiments
  follow correctness fixes and a frozen evaluation protocol.

## Completion criteria

A public research release requires the implemented behavior to match the
contract, meaningful regression tests, independently reproducible experiments,
a claim-to-evidence record, verified rights for distributed assets, and a clean
installation exercise. A polished README alone does not satisfy these criteria.
