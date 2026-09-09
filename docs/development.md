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

The full correctness suite uses generated images and explicitly seeded random
ResNet-50 weights. It does not download pretrained weights or read real datasets:

```sh
uv sync --locked --extra imaging --extra plots
uv run --locked --extra imaging --extra plots pytest
```

Actual pretrained extraction requests `IMAGENET1K_V2` and its associated
preprocessing. Weight-loading failures propagate; there is no fallback. A random
backbone requires both `weights="random"` and an integer `random_seed`, and its
cache metadata identifies it as such. Reusing a cache checks image bytes, IDs,
weight request, preprocessing, environment, and saved-artifact hashes. Use an
explicit output path. A mismatching cache fails; `force_extract=True` replaces
it only when explicitly requested. See [method](method.md) for the provenance
contract. CPU checks do not establish accelerator reproducibility.

## Build and isolated installation

```sh
uv sync --locked
uv run --locked python -m build --no-isolation
uv run --locked python scripts/verify_distribution.py dist/conformal_pathways-0.3.0.dev0-py3-none-any.whl
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

Tests derived from the contract cover exact arithmetic, hidden-label
perturbations, exhaustive toy rules, grouping, missingness, baselines, cache
integrity, and complete pipeline exports. See [Batch 2 verification](batch-2-verification.md).
Test success does not establish a clinical claim, dataset exchangeability, or
superiority over a baseline. The [original Batch 3 protocol](experiment-protocol.md)
and [v2 amendment](batch3-v2-amendment.md) define the current experiment. The
[dataset evidence](dataset-evidence.md) records the filtered IDRiD cohort and
sealed inputs. Multi-platform CI, typing and release checks remain Batch 4 work.

## Benchmark reproduction from a wheel

After building, run the committed verification script with a new output folder:

```sh
uv run --locked python scripts/reproduce_benchmark.py --config experiments/batch3-v2.json --suite synthetic --wheel dist/conformal_pathways-0.3.0.dev0-py3-none-any.whl --out artifacts/batch3-v2/independent-synthetic
uv run --locked python -m conformal_pathways.benchmarks compare artifacts/batch3-v2/primary/synthetic artifacts/batch3-v2/independent-synthetic/synthetic
```

The script archives the requested Git revision (`HEAD` by default), installs a
copy of the wheel with hashed core dependencies in a separate environment, checks
that optional dependencies are absent, and runs the entire synthetic suite with
Python socket operations blocked. The checkout, wheel, requirements, execution
records, and environment remain local for inspection. Complete the primary run
using the protocol commands first. Use the committed matching protocol/source;
post-freeze scientific changes fail verification rather than silently changing
the experiment. No real dataset or model weights are needed for this check.

For the real suite, pass `--suite real --data-root "$DATA_ROOT"` and a new output
directory. The script installs the locked imaging extra, uses the cached
checkpoint, blocks Python network connection/resolution/bind/send events and
extracts all features again. It does not borrow a feature cache or model from the
primary run. Verify both bundles with `compare`; the frozen tolerances must not
be widened in response to results. The same-host repeat does not establish
cross-platform reproducibility.

Wrap each command with `scripts/run_monitored.py --record /path/to/new-memory.json
--log /path/to/new-run.log -- COMMAND ...` to record resident memory and stop the
new command's process group if it exceeds 8 GiB or macOS reports critical memory
pressure. The guard checks every two seconds by default; its sampled RSS is an
operational bound, not a precise allocation profiler. Run suites sequentially.
