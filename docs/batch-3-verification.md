# Batch 3 v1 verification (historical)

The subsequent [v2 amendment](batch3-v2-amendment.md) resolves the input blocker
under a new freeze. [V2 verification](batch-3-v2-verification.md) records the
completed synthetic and real suites; the record below describes v1 only.

Recorded 2026-09-08 for version `0.3.0.dev0`. **The synthetic portion is complete;
the real-data extension is blocked by duplicate images and conflicting labels.** This is not public-release
clearance. The [machine-readable record](../evidence/batch3-verification.json)
contains the earlier synthetic verification and offline-input status. The
[later input audit](batch-3-input-audit.md) records the blocker encountered at that stage.

## Results and independent reproduction

The implementation/protocol commit is `355ad9c`; the freeze was committed in
`c52269b` before either designated experiment. The
[frozen configuration and source hashes](../experiments/batch3-v1.lock.json)
remain unchanged after outcome inspection. No scientific amendment or benchmark
rerun with revised parameters was used.

| Check | Recorded outcome |
| --- | --- |
| Primary synthetic suite | 5,760 / 5,760 records; 416 generated trials; 117.15 seconds |
| Independent synthetic suite | 5,760 / 5,760 records; 143.49 seconds |
| Raw comparisons | All scientific run records exact, including input/split identities and fitted-model hashes |
| Case comparisons | Every exported case outcome and retained/selected-path hash exact |
| Numeric model predictions | Within the prespecified absolute tolerance of 1e-10; prediction fingerprints also match exactly |
| Table regeneration | 448 summary and 384 paired rows recomputed from all 5,760 compact records |
| Raw aggregation | Every saved aggregate checked against its case CSV; complete comparison grid and file hashes checked |
| Full test suite | 375 passed; one expected warning from an intentionally missing fixture image |
| Static checks | Ruff passed; all 108 Python files formatted; `git diff --check` passed |
| Isolation | Installed wheel, clean Git snapshot, hashed core dependencies, execution outside checkout, optional packages absent |
| Offline execution | Python socket operations blocked for the entire independent suite and public-table verification |
| Distribution | Final wheel installed in a fresh environment; both demos also passed offline. Package source matches the freeze; source archive includes protocol/evidence and excludes external assets |
| Original project | All 97 files in the migration snapshot retain their original SHA-256 hashes |

Both runs used Python 3.12.14 on Darwin arm64, NumPy 2.5.3 and pandas 3.0.5.
The primary environment included optional packages; the repeat contained no
PyTorch, torchvision, scikit-learn, Pillow, matplotlib, or pytest. This is an
independent installation/re-execution on the same host, not independent hardware,
a separate investigator, or evidence of cross-platform reproducibility.
Timings are wall-clock observations under local load, not speed benchmarks.

The reproduction wheel SHA-256 is
`8e22ea8b1ac14b987e80c1fd6883ed0b773baf6648b533ab8d03c5f1d4bd2efe`.
It is retained locally with the clean checkout and execution records. Later
documentation-only builds can have different wheel metadata; source verification
still requires the identical frozen scientific files. No wheel is uploaded.

## Evidence and interpretation

[The generated report](../evidence/batch3-v1/README.md) is backed by
`trials.jsonl`, `summary.json`, `summary.csv`, `paired.csv`, plots, and their
checksum manifest. The PNG was visually inspected for labels, clipping, and
agreement with the plotted values. Tables can be independently regenerated from
the included compact records with:

```sh
uv run --locked python -m conformal_pathways.benchmarks verify-evidence evidence/batch3-v1
```

Full raw bundles are local under `artifacts/batch3/primary/synthetic` and
`artifacts/batch3/isolated/synthetic`. Regenerate them using the
[protocol](experiment-protocol.md) and [wheel reproduction script](../scripts/reproduce_benchmark.py).
The small public verification record is assembled from the CLI comparison,
execution manifests, installation record, and checks above; it is distinct from
the fully generated result tables.

The [interpretation](batch-3-results.md) records the limits and negative findings.
No primary advantage for `main` over `model_only` is established. Reference-path
inclusion is not a selected-path safety guarantee. Missing outcomes stay
unavailable; tiny calibration returns unbounded thresholds. All prespecified
synthetic settings are retained, including controls and stress scenarios.

## Failures, exclusions, and work remaining

Preparation exposed an IDRiD source-ID collision across provider partitions;
partition-qualified IDs and regression coverage were added before the freeze.
A small fixture test also exposed a synthetic-only report completeness bug; that
was corrected before the freeze. Neither was a post-benchmark outcome adjustment.

Earlier audits were blocked by cloud-only images (228, then 193 IDRiD files and
all 485 selected RIM-ONE files). After restoring every required image locally,
the next audit found six IDRiD duplicate pairs, one crossing provider partitions,
and four pairs with conflicting labels. The runner rejected these inputs before
real fitting. All 375 tests also passed in the new local Python 3.12.13 environment.
The [input audit](batch-3-input-audit.md) documents this later result separately
from the earlier synthetic evidence. No images or labels were changed and no
real input seal was created.

Reconcile the image/annotation source and document any necessary amendment
before sealing inputs and running the 80-record suite and fresh-feature repeat.
Check [dataset evidence](dataset-evidence.md) for provider layout, attribution,
and commands. New source, labels, parameters, exclusions, or tolerances require a
disclosed amendment. No real-data performance claim or full Batch 3 completion
should be inferred in the meantime.

Batch 4 still covers public-release documentation, CI, type checking, ownership,
license/attribution decisions, and final asset/history review. The development-only
upload classifier remains. No remote repository was created and nothing was pushed.
