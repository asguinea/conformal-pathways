# Development

Use Python 3.12 for the recorded research environment. Core CI covers Python
3.11–3.14 on Linux; optional numerical/plotting checks run on Linux and the full
generated-image suite runs on macOS arm64. CI verifies software behavior, not
cross-platform identity of the real-image experiment.

## Install and check

```sh
uv sync --locked
uv run --locked pytest -q
uv run --locked conformal-pathways --version
uv run --locked conformal-pathways sequential-demo --workflow dr --n 100 --seed 0
```

The lock records exact package resolutions and hashes from public PyPI. Core
installation includes NumPy, pandas, and development tools. Tests that need
absent optional dependencies report explicit skips. Tests use generated fixtures
and do not read an external dataset tree.

| Extra | Dependencies | Purpose |
| --- | --- | --- |
| `models` | scikit-learn | Fit logistic regression to supplied features |
| `plots` | matplotlib | Plot result tables |
| `imaging` | torch, torchvision, Pillow, scikit-learn | Extract image features and fit the image predictor |

```sh
uv sync --locked --extra imaging --extra plots
uv run --locked --extra imaging --extra plots pytest -q
uv run --locked ruff check .
uv run --locked ruff format --check src tests scripts
uv run --locked mypy --strict scripts/audit_release.py
uv run --locked python scripts/audit_release.py
```

Image tests use generated images and seeded random ResNet-50 weights; they do
not download pretrained weights. The real extractor explicitly requests
`IMAGENET1K_V2` and its associated transform. Loading failures propagate without
a fallback. The random baseline requires an explicit integer seed.

Formatting checks cover Python source, tests, and scripts. Frozen Markdown
protocols are preserved byte-for-byte, including embedded code formatting.
Strict typing currently covers the release-audit script; full scientific-package
static typing is not claimed. Runtime and scientific contracts are checked by
the test suite. Do not add a repository-wide type-check claim based on this
limited scope.

## Build and verify installation

```sh
uv sync --locked
uv run --locked python -m build --no-isolation
uv run --locked python scripts/verify_distribution.py dist/conformal_pathways-0.4.0-py3-none-any.whl
```

The wheel contains the installed package and license/metadata. The source
archive also includes tests, scripts, documentation, experiment configurations,
and aggregate evidence. Neither contains datasets, caches, local run outputs,
or model files. The verifier installs hashed core dependencies and the wheel
in a temporary environment outside the checkout. It checks both workflows and
both entry points, including a run with Python socket operations blocked.
Installation requires registry access; the examples themselves are offline.

A local `pip install .` resolves allowed dependency ranges rather than the
committed lock. Use `uv sync --locked` for recorded development resolutions.
No package-registry upload is configured by this repository.

## Experiments and data

Use the [reproduction guide](reproducing.md) for benchmark commands. The public
release's metadata differs from the evaluated 0.4.0.dev0 snapshot, so frozen
runs must use the matching historical tag and wheel. Do not edit a source lock
to make the current checkout pass it.

Dataset adapters consume user-supplied local paths. Treat manifests, traces,
feature matrices, and models as local artifacts. Reusing a feature cache checks
image bytes, IDs, weight identity, preprocessing, environment, and artifact
hashes. A mismatching cache fails; replacement requires explicit
`force_extract=True`. The [method](method.md), [claim register](claims.md), and
[dataset evidence](dataset-evidence.md) describe the scientific boundaries.

For expensive runs, use `scripts/run_monitored.py` with new record/log paths.
It samples process-group resident memory every two seconds and stops above
8 GiB or at critical macOS memory pressure. Run experimental suites serially.
These sampled operational measurements are not exact allocation peaks.
