# Batch 1 verification

Date: 2026-09-08. Version: 0.1.0.dev0. **Foundation gate passed.**
This record concerns packaging, migration, and executable smoke checks. It does
not close the scientific correctness gaps in the behavioral contract.

## Changes

- Created an independent project with a fresh Git repository and the installed
  namespace `conformal_pathways`.
- Selectively migrated 51 source modules, 36 synthetic test modules, and one
  plotting script. No datasets, pretrained assets, existing result bundles,
  virtual environments, or earlier Git history were copied.
- Added package metadata, a public-PyPI dependency lock, optional capability
  groups, the demo CLI, installation verification, and new command-boundary tests.
- Changed evaluation and model package exports to load optional APIs on demand.
  The core demo does not require the optional image/model/plotting stack.
- Established scope, observed-versus-latent data contracts, target metric
  definitions, a claim register, a provenance inventory, and the remaining roadmap.

The migration changed import paths and package-loading boundaries. The inherited
scientific algorithm and its known defects were retained for the next batch.

## Executed checks

| Check | Result |
| --- | --- |
| `uv sync --locked` | Passed in a new Python 3.12.14 environment |
| `uv run --locked pytest -q` | 95 passed, 6 optional-module skips, 1 expected fixture warning |
| `uv sync --locked --extra models --extra plots` | Passed |
| `uv run --locked --extra models --extra plots pytest -q` | 98 passed, 3 imaging-module skips, 1 expected fixture warning |
| Ruff check on the seven new/changed CLI, package-boundary, test, and verification files | Passed; this is not a claim of repository-wide lint compliance |
| Wheel build with locked development build tools | Passed |
| `scripts/verify_distribution.py` on the built wheel | Passed; details below |
| Migration-content scan | No retained source namespace imports, excluded project references, personal home paths, or matches for the checked credential patterns |
| Original project preservation | Python source/test/script hashes and complete Git status matched the pre-migration snapshot |

The single warning comes from a test that deliberately references one missing
image to exercise the adapter's skip behavior. It does not indicate missing
external data for the validation run.

The three skipped modules exercise embedding extraction, embedding-based
evaluation, and the image-grid runner. PyTorch/torchvision execution and pretrained
asset handling remain unverified. Core-only execution also skips the cached-model
test and two plotting modules; those three passed with `models` and `plots` enabled.

## Distribution isolation

The verification script installed the wheel and locked, hash-checked core
dependencies into a temporary virtual environment. From an unrelated empty
directory it checked:

1. The package imports from that environment's installed files.
2. The old import namespace and optional scientific/image/test packages are absent.
3. The demo and ingestion console commands both provide help.
4. Both workflow demos produce identical JSON through the console command,
   `python -I -m conformal_pathways`, and a run that rejects Python socket operations.
5. Demo output identifies its configuration and pending scientific validation.
6. The working directory remains empty. Temporary verification files are removed.

The wheel contains only package modules and distribution metadata. The source
distribution additionally includes tests, scripts, documentation, and the lock.
Binary distributions and local environments are ignored by Git.

## Recorded environment

Python 3.12.14 on macOS ARM64; NumPy 2.5.3, pandas 3.0.5, pytest 9.1.1,
scikit-learn 1.9.0, matplotlib 3.11.1, setuptools 82.0.1, build 1.6.0,
and Ruff 0.16.6. Exact dependency resolutions and artifact hashes are in
`uv.lock`. No cross-platform or accelerator validation is claimed here.

The content scan is a focused initial hygiene check, not a complete secret or
license audit. The public-release review must examine the final content and
history again after the remaining work.

## Next gate

Implement Batch 2 against R1–R11 and replace tests that encode incorrect behavior.
Do not promote the current experimental metrics to benchmark or safety claims.
Source ownership and license selection are still pending before public release.
