# Conformal Pathways

Experimental Python tools for uncertainty-aware decision workflows.

The project provides small branching workflows, calibration and path-filtering
code, dataset adapters, and an evaluation harness. Its first examples use
illustrative retinal decision workflows with three stages.

**Development status: sequential correctness extension; new benchmarks and public-release review pending.**
Version 0.4.0.dev0 supports choosing a diagnostic action, receiving its result,
and updating later decisions. Results enter only after the test is committed;
skipped tests reveal nothing. Calibration follows the same reference histories,
using one maximum score per declared group and stage. The entry predictor and
thresholds stay fixed throughout execution.

The [sequential method and retention argument](docs/sequential-method.md) define
the exact behavior and assumptions. Reference retention and the acceptability
of an actually selected sequence are measured separately. The
[toy rules](docs/toy-rules.md) have no validated clinical interpretation.
Diagnostic results in offline evaluation are explicitly simulated proxies.
See the [claim register](docs/claims.md) and
[correctness verification](docs/batch-2-sequential-verification.md).

The preserved [entry-only baseline benchmark](evidence/batch3-v2/README.md) contains 5,760 synthetic
and 80 real-image comparison records under a frozen protocol. Both suites
reproduce exactly from separate installed-wheel environments on the same host, including
fresh real feature extraction. The real runs use
506 filtered IDRiD images and 485 RIM-ONE images, a class-prior control and
frozen ResNet-50 features with logistic regression. A disclosed
[input amendment](docs/batch3-v2-amendment.md) excludes ten duplicate/conflicting
IDRiD copies from analysis manifests while preserving all source files.
These records concern `entry-pathways-v2`, which chooses complete action sequences
from entry observations. They do not evaluate the new result-aware algorithm.
The matching source is preserved at Git tag `baseline-entry-v2` (`1a798b9`).
Reproducing that protocol requires the matching checkout and wheel; its source
lock intentionally rejects this changed implementation.

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
uv run --locked conformal-pathways sequential-demo --workflow dr --n 100 --seed 0
uv run --locked conformal-pathways sequential-demo --workflow glaucoma --n 100 --seed 0
uv run --locked pytest
```

Installation needs access to the package registry. The demo then runs offline
on generated data without images, model weights, credentials, or dataset access.
It prints strict JSON with configuration, calibration, decision/result traces,
and explicitly experimental metrics. The generated fixtures and fitted
class-frequency predictor check implementation behavior. They are not evidence
of predictive performance. The `demo` command still exercises the entry-only
baseline.

`python -m conformal_pathways sequential-demo` is an equivalent entry point in the installed
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
  conformal/    Entry-only calibration and pathway filtering
  sequential/   Result-aware sessions, reference calibration, simulation and evaluation
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
- [Sequential method and contract](docs/sequential-method.md)
- [Batch 2 sequential extension verification](docs/batch-2-sequential-verification.md)
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
