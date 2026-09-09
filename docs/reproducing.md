# Reproducing the experiments

There are three levels: verify distributed aggregates, run a generated-data
example, or reproduce the frozen experiments from independently obtained inputs.
The public evidence contains aggregate results and provenance hashes. Full
real-image case records, annotations, features, and weights stay local.

## Verify the distributed tables

From the current repository:

```sh
uv sync --locked --extra plots
uv run --locked --extra plots python scripts/verify_evidence_portable.py evidence/batch3-sequential-v1
uv run --locked --extra plots python scripts/verify_evidence_portable.py evidence/batch3-v2
uv run --locked --extra plots python scripts/verify_evidence_portable.py evidence/batch3-v1
```

These checks validate integrity, design completeness, and aggregation from the
included compact records. File hashes, design, counts, means, ranges and identifiers
must match exactly. The portable check permits at most 1e-12 absolute difference
only in recomputed interval endpoints and reports the observed difference. This
accounts for platform-dependent floating-point interval arithmetic; it does not
relax any frozen experiment/reproduction comparison. The original
`verify-evidence` module commands remain available for strict byte/number equality.
These checks do not reconstruct undistributed patient-level
inputs or independently establish that source observations are correct.
The [quick-start demos](../README.md#quick-start) exercise generated fixtures.

## Reproduce the result-aware benchmark

Use Python 3.12 for the recorded experiment. Its source and dependency files
are frozen at `sequential-benchmark-v1`; current release metadata deliberately
has a different version. Create an isolated checkout of the original tag:

```sh
git fetch --tags
git worktree add --detach ../conformal-pathways-sequential sequential-benchmark-v1
cd ../conformal-pathways-sequential
uv sync --locked --extra imaging --extra plots
uv run --locked python -m build --no-isolation
```

The tag contains the exact evaluated scientific source and 0.4.0.dev0 package
metadata. Use that checkout's commands and wheel for both runs. All experiment
output directories must be new; existing attempts are preserved.

For the synthetic suite, no dataset or weights are needed:

```sh
uv run --locked --extra imaging --extra plots python scripts/run_monitored.py --record artifacts/repeat/synthetic-memory.json --log artifacts/repeat/synthetic.log -- uv run --locked --extra imaging --extra plots python -m conformal_pathways.benchmarks.sequential run --config experiments/batch3-sequential-v1.json --suite synthetic --out artifacts/repeat/synthetic
uv run --locked python scripts/reproduce_benchmark.py --engine sequential --config experiments/batch3-sequential-v1.json --suite synthetic --wheel dist/conformal_pathways-0.4.0.dev0-py3-none-any.whl --out artifacts/repeat/independent-synthetic
uv run --locked python -m conformal_pathways.benchmarks.sequential compare artifacts/repeat/synthetic artifacts/repeat/independent-synthetic/synthetic
```

The primary suite contains 11,392 comparisons. The repeat creates another clean
checkout and installs the matching wheel outside it with locked core dependencies.
Use the memory guard for the independent command too if resources are limited;
run experiments serially. Network access is blocked during the independent
experiment, after dependency installation.

## Real-image simulations

Obtain the complete original IDRiD and RIM-ONE DL datasets directly from their
providers and follow their terms and [directory layouts](dataset-evidence.md).
Set `DATA_ROOT` to your local parent directory. The audited inputs include
excluded duplicates so the runner can reconstruct and verify the entire audit;
do not delete or relabel source images.

The frozen protocol requests ResNet-50 `IMAGENET1K_V2` weights. The primary
extractor can download the checkpoint if it is not cached; obtain permission
under the applicable terms first. The independent run needs that same verified
checkpoint in its Torch cache because its network access is blocked. See the
[model identity and checksum](dataset-evidence.md#pretrained-model-identity).

In the same frozen checkout, after the synthetic commands:

```sh
uv run --locked --extra imaging --extra plots python scripts/run_monitored.py --record artifacts/repeat/real-memory.json --log artifacts/repeat/real.log -- uv run --locked --extra imaging --extra plots python -m conformal_pathways.benchmarks.sequential run --config experiments/batch3-sequential-v1.json --suite real --data-root "$DATA_ROOT" --out artifacts/repeat/real
uv run --locked python scripts/reproduce_benchmark.py --engine sequential --config experiments/batch3-sequential-v1.json --suite real --data-root "$DATA_ROOT" --wheel dist/conformal_pathways-0.4.0.dev0-py3-none-any.whl --out artifacts/repeat/independent-real
uv run --locked python -m conformal_pathways.benchmarks.sequential compare artifacts/repeat/real artifacts/repeat/independent-real/real
uv run --locked --extra plots python -m conformal_pathways.benchmarks.sequential publish-local --runs artifacts/repeat/synthetic artifacts/repeat/real --out artifacts/repeat/evidence
```

`publish-local` creates a local report; it does not send anything to GitHub.
The primary real suite has 400 comparisons. The independent run extracts all
features again. CPU is the recorded device, with two Torch threads, batch size
16, and zero data-loader workers. Same-host equality was exact; other platforms
can differ numerically. Record differences without loosening the original
comparison or presenting a changed setup as an exact repeat.

## Entry-only and historical evidence

Use `baseline-entry-v2` in a separate worktree, its 0.3.0.dev0 wheel, and the
[entry-only protocol amendment](batch3-v2-amendment.md). Its synthetic and real
suites have 5,760 and 80 comparisons. The earlier v1 synthetic experiment remains
at commit `c52269b`; its real-data audit failed before fitting and was resolved
through the disclosed v2 amendment. Historical results and exclusions are retained.

Recorded outcomes and reproduction checks are in the
[sequential verification](batch-3-sequential-verification.md) and
[entry-only verification](batch-3-v2-verification.md). A new algorithm, cohort,
model, or protocol needs a new prospective freeze. Never overwrite historical
locks, evidence, or tags to accommodate a changed setup.
