# Batch 2 verification

Date: 2026-09-08. Version: 0.2.0.dev0. **Correctness gate passed for the documented
entry-observation, open-loop protocol.** This is not a public-release approval or
a quantitative performance result.

## Changes and scope

R1–R11 are addressed through corrections or explicit scope reductions; the
[contract](behavioral-contract.md) maps each issue to evidence. Inference is
separated from retrospective labels, diagnostic revelation requires provenance,
calibration uses declared group maxima and corrected finite-sample quantiles,
and selection/metric code distinguishes missing labels, abstention, and errors.
Every runner uses one shared evaluation implementation. The unpruned baseline
is exact enumeration. Image extraction requires explicit weights and validated
cache provenance. The [method](method.md) defines a conditional reference-path
inclusion argument; [toy-rules-v2](toy-rules.md) bounds the surrogate outcomes.

The supported candidate sets are complete action sequences based on entry
observations. Adaptive replanning, online coverage, and clinical safety are not
implemented claims. This restriction removes a misleading interpretation of
hypothetical diagnostic branches.

## Tests and independent checks

The final suite passed **361 tests, zero failures, zero skips**, with imaging
and plotting extras installed. One expected warning comes from a fixture that
intentionally supplies a missing image and checks that the adapter excludes it.
The suite ran with Python socket operations blocked. No real images, annotation
files, or pretrained model weights were downloaded for this verification.

Evidence includes:

- Exact rational quantile fixtures over multiple calibration sizes and error
  budgets, ties, leave-one-out rank checks, infinity, invalid inputs, and
  conservative allocations including subnormal floating-point values.
- Hidden-label and metadata perturbations with unchanged prediction sets and
  selections, label-free predictor inputs, and exclusion of future observations.
- CSV-to-state positive/negative/missing cases, strict label parsing,
  contradictory availability rejection, and action-matched diagnostic results.
- Hand-computed group-max calibration scores, incomplete-group exclusions,
  training/calibration overlap rejection, globally duplicate IDs, namespace
  collisions, and official-test preservation across seeds.
- Exhaustive checks of 180 DR and 36 glaucoma label/path combinations against
  independent predicates, plus deterministic reference targets.
- Hand-computed mixed cohorts separating selected-path risk, abstention, missing
  outcomes, and empty sets; zero-denominator subgroups; exact reaggregation of
  per-case exports; explicitly identified means across runs.
- Independent 18-path Cartesian products for the unpruned baseline, shared
  pipeline comparisons, finite-threshold runs, and trace/retention agreement
  for all score variants. Output identities distinguish configurations/inputs.
- Generated-image CPU extraction, exact repetition with the same random seed,
  cache reuse, changed image/seed rejection, corrupted matrix/ID-file checks,
  absent provenance rejection, and a mocked pretrained-loading failure that
  cannot fall back to random initialization. Classifier fitting uses only the
  explicitly supplied training labels.

Reproduce the suite after installing the locked extras:

```sh
uv sync --locked --extra imaging --extra plots
uv run --locked --extra imaging --extra plots pytest -q
uv run --locked --extra imaging --extra plots ruff check src tests scripts
uv run --locked --extra imaging --extra plots ruff format --check src tests scripts
```

For the additional network check, run this in that installed environment:

```python
import sys


def prevent_network(event, args):
    if event.startswith("socket."):
        raise RuntimeError("Network disabled for correctness verification")


sys.addaudithook(prevent_network)
import pytest

raise SystemExit(pytest.main(["-q"]))
```

Lint passed for the repository's explicit E4/E7/E9/F/I rules. Formatting passed
for all 98 Python files. `git diff --check` passed. These are recorded checks;
they do not claim comprehensive static typing or multi-platform CI.

## Distribution and isolation

Built the wheel and source distribution using the locked build tools. The
wheel installed into a new temporary environment with hashed, locked core
requirements, outside this checkout. `scripts/verify_distribution.py` passed:

1. Imports resolve to the installed wheel; the old namespace and optional
   image/model/test packages are absent from that environment.
2. Both console commands provide help.
3. Both workflow demos return identical JSON through console, module, and
   socket-blocked entry points, with no working-directory artifacts.
4. The wheel contains package modules and metadata only.

The source-distribution Python payload matches the wheel and checkout. It
includes documentation, tests, scripts, and the lock, without local environments,
images, caches, or result files. Both distributions remain local and ignored
by Git. The original 97-file prototype snapshot still matches every recorded
SHA-256 hash. No remote was configured and nothing was pushed or published.

## Environment and remaining gates

Python 3.12.14 on macOS ARM64; NumPy 2.5.3, pandas 3.0.5, scikit-learn 1.9.0,
PyTorch 2.14.0, torchvision 0.29.0, Pillow 12.3.0, pytest 9.1.1, and Ruff 0.16.6.
`uv.lock` records the complete resolution and artifact hashes. During local
validation, macOS hidden flags on editable-install `.pth` files caused package
import failures; clearing those flags restored discovery and the complete suite
passed again. The separate wheel installation did not need that repair. Python's other
allowed versions, accelerators, and other operating systems were not tested.

Batch 3 still needs a frozen protocol, verified dataset versions/label mappings,
true grouping and observation timing, actual pretrained-model provenance, fresh
benchmark runs, paired comparisons, and group-appropriate uncertainty estimates.
Exchangeability on a real dataset is not established by these software tests.
Batch 4 still needs CI/release checks, ownership and license confirmation,
attribution, and review of the final public content and history. The focused
name/path/credential-pattern scan in this batch is not a comprehensive security
or rights audit. See the [claim register](claims.md) before describing results.
