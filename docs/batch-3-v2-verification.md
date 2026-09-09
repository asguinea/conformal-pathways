# Batch 3 v2 verification

Recorded 2026-09-09 for `0.3.0.dev0`. **Batch 3 is complete for its documented
scope.** Both synthetic and real-image suites reproduce exactly on the same
host from separate installed-wheel environments. This is not public-release
clearance. The [machine-readable record](../evidence/batch3-v2-verification.json)
contains commits, complete source identity, input audit, environments,
comparisons, timings and resource measurements.

## Prospective input amendment and provenance

The v1 synthetic outcomes and failed real-input audit were already known.
The [v2 amendment](batch3-v2-amendment.md) was committed in `a0d3f04`, its
[source lock](../experiments/batch3-v2.lock.json) in `b7b1423`, and the
[input seal](../experiments/batch3-inputs-v2.json) in `bc8a7d0`, all before real
feature extraction or fitting. No algorithm, seed, model, hyperparameter,
metric, selector or tolerance changed. No frozen scientific file changed
after the v2 outcomes. Earlier attempts and v1 artifacts remain preserved.

The amendment excludes ten IDRiD copies from analysis manifests, leaving 404
provider-training and 102 test images. RIM-ONE remains 339/146. All original
source files and annotations are untouched. The seal covers original inputs,
exclusions and retained inputs, so changing even an excluded image is detected.
Patient linkage remains unverified. The supplementary perceptual screen and
its limits are disclosed in the amendment.

## Completed experiments and verification

| Check | Outcome |
| --- | --- |
| Primary real suite | 80/80 records; 185.39 seconds |
| Independent real suite | 80/80 records; 218.61 seconds |
| Primary synthetic suite | 5,760/5,760 records; 101.02 seconds |
| Independent synthetic suite | 5,760/5,760 records; 132.31 seconds |
| Within-v2 reproduction | All scientific run records exact in both suites, including paired inputs and fitted-model identities |
| Cases and predictions | Every case outcome and candidate/selected-path fingerprint matches; predictions pass the frozen absolute tolerance of 1e-10 and scientific fingerprints match exactly |
| Fresh real features | Both IDRiD and RIM-ONE matrices are bit-for-bit identical; maximum absolute difference 0.0; frozen tolerance remains atol=rtol=1e-6 |
| v1 synthetic regression | All 5,760 scientific records exact; all 5,760 case files, 416 inputs, 672 prediction files and 672 model records have identical hashes |
| Complete table regeneration | 5,840 records, 576 summary rows and 480 paired rows; no pending suite |
| Raw aggregation | Saved metrics recomputed from case exports; complete grids and all saved file hashes checked |
| Tests | 388 passed in 9.64 seconds; one expected warning from an intentionally missing fixture image |
| Static checks | Ruff lint/format and git diff whitespace checks passed |
| Installed distribution | Wheel contains package/metadata only; isolated core install and both offline demos pass |

Both independent runs used a clean archive of `bc8a7d0`, a separate environment
with hashed locked dependencies, and the same wheel, executed outside the
checkout with Python isolation enabled. The synthetic environment lacks imaging,
model, plot and test packages. The real environment adds the imaging extra;
both feature directories start empty and all features are re-extracted.
The imported wheel source is checked against the 69-file source lock.

Python socket audit events are blocked throughout the synthetic repeat and
public-table verification. Connection, name-resolution, bind and send events
are blocked during the real repeat; its checkpoint was already local and
hash-verified. This is an application-level check, not a native-code or
operating-system network sandbox. Installation can use the package registry.

Both repeats used Python 3.12.13 on Darwin arm64, NumPy 2.5.3 and pandas 3.0.5.
Real extraction/fitting used torch 2.14.0, torchvision 0.29.0, Pillow 12.3.0 and
scikit-learn 1.9.0. This demonstrates independent installation and re-execution
on one host, not independent hardware, an independent investigator,
cross-platform reproducibility or clinical validation. Timings are local
wall-clock observations, not speed benchmarks.

The reproduction wheel SHA-256 is
`57316d4e562329e87656bb10a0f93b5028dc5e009f5aedcaaf23eee84c6771fb`.
It is retained locally with both checkouts, requirements, logs and environments.
Later documentation-only wheel metadata may differ; the scientific source
must still match the committed freeze. The source archive and release metadata
receive their final release review in Batch 4.

## Memory and local artifacts

The four suites ran sequentially. The guard sampled process-group resident
memory every two seconds, with an 8 GiB stop threshold and a stop on macOS
critical memory pressure. Sampled peaks were 1.44 GiB for primary real, 1.51 GiB
for independent real, 97.8 MiB for primary synthetic and 112.6 MiB for independent
synthetic. All guards completed without intervention; the highest reported
macOS pressure level was 1. These are sampled RSS observations, not an exact
allocation profiler. No designated v2 experiment failed.

The bulk cloud migration remained paused. Experiments used only the local
external-volume data snapshot. Neither the original project nor original
datasets were removed or overwritten.

Raw bundles remain in ignored local directories:

```text
artifacts/batch3-v2/primary/{real,synthetic}/
artifacts/batch3-v2/isolated-real/real/
artifacts/batch3-v2/isolated-synthetic/synthetic/
```

The [combined evidence](../evidence/batch3-v2/README.md) contains compact records,
regenerable tables, the visually checked plot and a checksum manifest. Raw real
inputs, image rows, per-case traces, predictions, features and fitted-model
details are excluded. Aggregate-result redistribution review remains a Batch 4
task before public publication.

Git attributes preserve the evidence's exact generated bytes. CSV CRLF record
terminators and Matplotlib SVG path-line spaces are explicitly accepted by
whitespace checks; they are not edited after hashing. Authored source and
documentation retain ordinary whitespace checks.

```sh
uv run --locked python -m conformal_pathways.benchmarks verify-evidence evidence/batch3-v2
uv run --locked python -m conformal_pathways.benchmarks compare artifacts/batch3-v2/primary/real artifacts/batch3-v2/isolated-real/real
uv run --locked python -m conformal_pathways.benchmarks compare artifacts/batch3-v2/primary/synthetic artifacts/batch3-v2/isolated-synthetic/synthetic
```

See [development](development.md) for clean-wheel reproduction and the memory
guard, and [dataset evidence](dataset-evidence.md) for input acquisition/layout.
The independent core environment also verified the public package offline and
confirmed that its synthetic compact records equal v1 exactly.

## Interpretation and remaining work

The [results](batch-3-v2-results.md) retain the negative findings. IDRiD `main`
mean reference inclusion is 84.9%, below the nominal 90%, versus 92.0% for
`model_only`; it has smaller sets without better selected-path violation rates.
The promoted RIM-ONE metrics agree between those variants. No clinical-safety,
patient-level coverage or superiority claim is promoted. Real seed ranges are
descriptive, not confidence intervals.

Batch 4 remains: ownership/license confirmation, attribution and derived-output
review, CI, type checks, final documentation/distribution/history review, and
release metadata. Nothing was pushed or published remotely.
