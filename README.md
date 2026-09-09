# Conformal Pathways

Experimental Python tools for uncertainty-aware decision workflows.

The project provides small branching workflows, calibration and path-filtering
code, dataset adapters, and an evaluation harness. Its first examples use
illustrative retinal decision workflows with three stages.

**Development status: Batch 3 reproduced; public-release review pending.**
Version 0.3.0.dev0 evaluates complete action sequences from explicitly declared
entry observations. Hypothetical tests do not reveal retrospective labels.
Calibration uses one maximum reference-path score per declared group and stage;
metrics distinguish unavailable labels, abstention, and rule violations.

The [method and conditional coverage argument](docs/method.md) define the exact
inclusion event. The [toy rules](docs/toy-rules.md) are illustrative surrogates,
with no validated clinical interpretation. Adaptive replanning and online
coverage are outside this version's scope. See the [claim register](docs/claims.md)
and [Batch 3 verification](docs/batch-3-v2-verification.md).

The [current benchmark](evidence/batch3-v2/README.md) contains 5,760 synthetic
and 80 real-image comparison records under a frozen protocol. Both suites
reproduce exactly from separate installed-wheel environments on the same host, including
fresh real feature extraction. The real runs use
506 filtered IDRiD images and 485 RIM-ONE images, a class-prior control and
frozen ResNet-50 features with logistic regression. A disclosed
[input amendment](docs/batch3-v2-amendment.md) excludes ten duplicate/conflicting
IDRiD copies from analysis manifests while preserving all source files.

The results do not establish superiority or clinical safety. On filtered IDRiD,
`main` has smaller candidate sets but lower mean reference inclusion than
`model_only` (84.9% versus 92.0%); on RIM-ONE their reported metrics agree.
The IDRiD result is below the nominal 90% level. See
[results and limitations](docs/batch-3-v2-results.md) for the complete interpretation,
including why fixed-test seed ranges are not confidence intervals. Historical
[v1 synthetic evidence](evidence/batch3-v1/README.md) remains available.

## Quick start

From this project directory, with Python 3.12 and
[uv](https://docs.astral.sh/uv/getting-started/installation/) installed:

```sh
uv sync --locked
uv run --locked conformal-pathways demo --workflow dr --n 100 --seed 0
uv run --locked conformal-pathways demo --workflow glaucoma --n 100 --seed 0
uv run --locked pytest
```

Installation needs access to the package registry. The demo then runs offline
on generated data without images, model weights, credentials, or dataset access.
It prints a JSON record with the configuration and explicitly experimental
metrics. It uses a fitted class-frequency predictor, so it is an installation
check rather than a predictive-performance benchmark.

`python -m conformal_pathways demo` is an equivalent entry point in the installed
environment. Package metadata permits Python 3.11–3.14; the recorded validation
environment is Python 3.12. See [development](docs/development.md) for optional
dependencies and installation from a wheel.

## Project layout

```text
src/conformal_pathways/
  benchmarks/   Frozen protocols, paired experiments, and evidence verification
  data/         Sample records, manifest loading, group splits
  workflows/    States, actions, and illustrative branching workflows
  models/       Class-prior and optional embedding predictors
  conformal/    Experimental calibration and pathway filtering
  scoring/      Experimental action scoring
  safety/       Illustrative rule evaluators and reference pathways
  eval/         Experimental runners, metrics, selection, and traces
  ingest/       Adapters for externally obtained datasets
  features/     Optional image embedding extraction
  plots/        Optional result plotting
tests/          Synthetic unit and integration fixtures
docs/           Contracts, claims, provenance, and validation records
```

The module name `safety` is historical API terminology for an illustrative rule
checker. Its outputs are not measurements of clinical outcomes.

## Development and scope

- [Scope and intended use](docs/scope.md)
- [Behavioral contract and correction evidence](docs/behavioral-contract.md)
- [Claim register](docs/claims.md)
- [Provenance and licensing inventory](docs/provenance.md)
- [Development commands](docs/development.md)
- [Four-batch roadmap](docs/roadmap.md)
- [Batch 1 verification](docs/batch-1-verification.md)
- [Batch 2 verification](docs/batch-2-verification.md)
- [Current protocol amendment](docs/batch3-v2-amendment.md) and [original protocol](docs/experiment-protocol.md)
- [Dataset evidence and exclusions](docs/dataset-evidence.md)
- [Batch 3 verification](docs/batch-3-v2-verification.md)
- [Current results and limitations](docs/batch-3-v2-results.md)
- [Historical synthetic interpretation](docs/batch-3-results.md)

The included evidence consists of synthetic records, aggregate real benchmark
metrics, plots, and provenance digests.
No real dataset images, source annotations, embeddings, trained models, or raw
experiment traces are distributed here. Code ownership, the project license and
redistribution review remain to be completed before public release; see the
provenance inventory. This is a
development project, not a clinical decision support product.
