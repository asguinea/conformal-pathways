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
experimental. Version 0.4.0.dev0 adds result-aware sessions and an offline
evaluator that executes a diagnostic before receiving its simulated result,
then updates later decisions. The entry predictor and calibration thresholds
stay fixed. The prior open-loop entry-only API remains available as a baseline.
See [sequential method](sequential-method.md) for the exact supported behavior.

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
- The entry-only baseline has independently reproduced descriptive results on
  one host. They do not validate the result-aware extension. Its scientific
  evaluation requires a new frozen Batch 3 protocol and independent runs.

## Completion criteria

A public research release requires the implemented behavior to match the
contract, meaningful regression tests, independently reproducible experiments,
a claim-to-evidence record, verified rights for distributed assets, and a clean
installation exercise. A polished README alone does not satisfy these criteria.
