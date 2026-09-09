# Batch 2: sequential extension verification

Completed on 2026-09-09 with Python 3.12.13 on macOS arm64. Package 0.4.0.dev0,
algorithm `result-aware-pathways-v1`. The [machine-readable record](batch-2-sequential-verification.json)
contains the checked source/test hashes, wheel identity, results, resource
records, and baseline-preservation checks.

## Completed behavior

- Sessions choose a diagnostic, wait for an explicit result, update observed
  state, and compute subsequent retained actions. Skipping reveals no result;
  premature, mismatched, and repeated deliveries fail. Unavailable results are
  recorded separately from negative results.
- Grouped calibration scores the reference on its actual simulated observation
  history, using fixed budgets, the corrected finite-sample rank, and inclusive
  ties. Missing truth labels exclude complete groups; missing test results alone
  do not. Training/calibration/test separation remains explicit.
- The offline evaluator shares fixed entry predictions across branches and
  selectors, keeps selection scoring fixed across filter ablations, executes
  decisions before inspecting retrospective alternatives, and exports auditable
  case traces and metric denominators. The existing frozen embedding predictor
  integrates without refitting between variants.
- Reference reachability, existential toy acceptability, selected violations,
  and partial-execution abstentions have separate definitions. The
  [method](sequential-method.md) provides the assumptions and marginal retention
  argument; it does not claim conditional or selected-path safety.

## Verification results

| Check | Result |
| --- | --- |
| Full regression suite | 442 passed in 9.37 seconds; no skips in the recorded full environment |
| New sequential checks | 54 passed; included in the full total |
| Warning | One existing intentional EyePACS fixture warning for a missing generated image |
| Ruff | Passed across the repository |
| Changed-file whitespace | `git diff --check` passed |
| Dependency lock | `uv lock --check --offline` passed; only the local package version changed |
| Distribution build | Source distribution and wheel built successfully |
| Isolated installation | Hashed locked core dependencies; optional dependencies absent; imported outside the checkout |
| Offline demonstrations | Entry and sequential demos for both workflows match between console, module, and socket-blocked runs |
| Wheel/source agreement | Every packaged Python source matches the checked working-tree bytes |
| Preserved baseline | All 24 tracked evidence/protocol files byte-equal to `baseline-entry-v2` (`1a798b9`) |
| Evidence reaggregation | Both existing bundles pass; v2 still has 5,840 records, 576 summary rows, and 480 paired rows |
| Old protocol source guard | Correctly rejects the new implementation; its lock was not rewritten |

Independent fixtures include hand-calculated post-result group maxima, positive
and negative result divergence, unavailable and erroneous test results, exact
reference traversal/retention across all toy truth states and diagnostic values,
finite exchangeable-group enumeration, hidden-truth perturbations, skipped-test
access traps, premature/replayed result rejection, and detached-state mutation
checks. Pipeline checks independently reconstruct exported denominators and
toy predicates. Explicit examples cover later-stage abstention and a retained
acceptable reference alongside a violating selected sequence.

The final full test run peaked at 632,288 KiB (about 618 MiB) of sampled process
group RSS; the installation check peaked at 106,048 KiB. Both ran under the
existing 8 GiB guard with normal macOS memory pressure. Samples are taken every
two seconds, so these values are not exact allocation peaks. No real-data
experiments, feature extraction runs, or cloud transfers were started.

## Reproduction commands

Run from this revision with the locked full test environment:

```sh
uv sync --locked --extra imaging --extra plots
uv run --locked pytest -q
uv run --locked ruff check .
git diff --check
uv lock --check --offline
uv run --locked python -m build --no-isolation --outdir artifacts/batch2-sequential/final-distribution
uv run --locked python scripts/verify_distribution.py artifacts/batch2-sequential/final-distribution/conformal_pathways-0.4.0.dev0-py3-none-any.whl
```

For a focused core check, run `pytest -q tests/test_result_aware_sessions.py
tests/test_result_aware_calibration.py tests/test_result_aware_evaluation.py`.
The embedding integration fixture explicitly skips when scikit-learn is absent;
the core result-aware engine requires no optional imaging dependencies.

The recorded run used the installed `.venv` executables and the existing
`scripts/run_monitored.py` wrapper. Local logs, earlier verification attempts,
the final wheel, and resource records remain under `artifacts/batch2-sequential/`.
The preliminary wheel predates the fixed-selector ablation check; the final
verified wheel is the one under `final-distribution/`. Its SHA-256 is
`2404add8e68524ba55365585095d843edaeaa6cf900d6abe3344621c6b76fd88`.
Rebuilt wheels may differ in archive timestamps; source and behavior checks
matter alongside recorded artifact identity.

## What this completion establishes

The missing result-aware implementation and correctness work is complete for
the two existing three-stage toy workflows. Earlier correctness fixes and
entry-only benchmark evidence are preserved. The original repositories remain
untouched; all work is in the separate development repository.

The next step is the sequential **Batch 3** protocol and experiments, including
declared proxy-result/error/missingness assumptions, matched baseline comparisons,
and independent reproduction. Existing data audits and baseline evidence can be
reused where applicable. **Batch 4** public-release preparation remains pending.
Passing fixtures does not establish clinical safety, improvement over baselines,
real diagnostic-response validity, patient-level exchangeability, or readiness
for public redistribution. See the [claim register](claims.md) and
[roadmap](roadmap.md).
