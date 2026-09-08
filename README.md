# Conformal Pathways

Experimental Python tools for uncertainty-aware decision workflows.

The project provides small branching workflows, calibration and path-filtering
code, dataset adapters, and an evaluation harness. Its first examples use
illustrative retinal decision workflows with three stages.

**Development status: foundation complete; scientific correctness review pending.**
The migrated evaluation has known limitations. Existing tests check software
behavior, including behavior that must change; they do not certify coverage,
guideline validity, or clinical safety. See the [claim register](docs/claims.md)
and [behavioral contract](docs/behavioral-contract.md).

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
environment. Package metadata permits Python 3.11–3.14; the Batch 1 validation
environment is Python 3.12. See [development](docs/development.md) for optional
dependencies and installation from a wheel.

## Project layout

```text
src/conformal_pathways/
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
- [Behavioral contract and known gaps](docs/behavioral-contract.md)
- [Claim register](docs/claims.md)
- [Provenance and licensing inventory](docs/provenance.md)
- [Development commands](docs/development.md)
- [Four-batch roadmap](docs/roadmap.md)
- [Batch 1 verification](docs/batch-1-verification.md)

No dataset images, annotations, embeddings, trained models, or benchmark outputs
are distributed here. Code ownership and the project license remain to be
confirmed before a public release; see the provenance inventory. This is a
development project, not a clinical decision support product.
