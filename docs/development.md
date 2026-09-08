# Development

Use Python 3.12 for the currently verified environment. The dependency manifest
separates core runtime dependencies, optional capabilities, and development
tools using [uv dependency groups and extras](https://docs.astral.sh/uv/concepts/projects/dependencies/).
`uv.lock` records exact resolutions and artifact hashes from public PyPI.

## Core workflow

```sh
uv sync --locked
uv run --locked pytest
uv run --locked conformal-pathways --version
uv run --locked conformal-pathways demo --workflow dr --n 100 --seed 0
```

The default environment includes NumPy, pandas, and development tools. Tests
for absent optional packages report explicit skips. Core tests use generated
fixtures and do not read a local dataset tree. Do not set `PYTHONPATH` or import
through a top-level package called `src`; the installed namespace is
`conformal_pathways`.

## Optional capabilities

| Extra | Direct dependencies | Purpose |
| --- | --- | --- |
| `models` | scikit-learn | Fit logistic regression on existing embeddings |
| `plots` | matplotlib | Plot supplied result tables |
| `imaging` | torch, torchvision, Pillow, scikit-learn | Extract embeddings and fit an image-based model |

```sh
uv sync --locked --extra models --extra plots
uv run --locked --extra models --extra plots pytest
```

The `imaging` extra is declared and locked but is outside the Batch 1 execution
gate. Its current smoke tests can download pretrained weights. The extractor
also has a known fallback to random weights when loading fails; it must be
corrected before benchmark use. Installing the extra alone does not establish
reproducibility on a particular accelerator or platform.

## Build and isolated installation

```sh
uv sync --locked
uv run --locked python -m build --no-isolation
uv run --locked python scripts/verify_distribution.py dist/conformal_pathways-0.1.0.dev0-py3-none-any.whl
```

This builds both a source distribution and a wheel with build tools installed
from the lock. The verification script installs the wheel into a temporary
environment with hashed, locked core dependencies and runs both demos outside
the checkout, including a run that blocks Python socket operations. It removes
the temporary environment after checking. A local `pip install .`
also works, but resolves allowed dependency ranges rather than using `uv.lock`.
Do not upload these development distributions.

## Experimental module entry points

```sh
uv run --locked conformal-pathways-ingest --help
uv run --locked python -m conformal_pathways.eval.runner --help
```

Dataset adapters operate on paths supplied by the caller. Dataset access and
terms must be established separately; see [provenance](provenance.md). Treat
evaluation exports, traces, manifests, and embedding caches as local artifacts.

## Validation boundaries

The inherited suite is a migration baseline, not a specification of scientific
correctness. Batch 2 must replace assertions that encode the known defects and
add tests derived independently from the contract. Automated formatting, typing,
multi-platform CI, and release checks are scheduled after the core corrections.
