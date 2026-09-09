# Batch 3 v2: audited image exclusions

This amendment was specified after the v1 synthetic results and the failed
real-input audit were known, but before any real feature extraction or model
fitting. The original protocol, configuration, lock and synthetic evidence are
preserved. Commit `0e50ae3` contains the preceding implementation. The
[original protocol](experiment-protocol.md) applies except for the explicit
input and provenance changes below; [batch3-v2.json](../experiments/batch3-v2.json)
is the authoritative current configuration. This is a local prospective freeze,
not an externally registered study.

## Input amendment

The available IDRiD disease-grading release has 516 image files and 510 distinct
SHA-256 identities: six exact duplicate pairs. Four pairs have conflicting
source grades, including one train/test pair. Two pairs agree. Both local
folder layouts were compared and contain identical image and annotation bytes.
No authoritative erratum identifying these exact cases was located. We do not
infer corrected labels or attribute the discrepancy to a particular upstream
processing step. The previous [input audit](batch-3-input-audit.md) is retained.

Before any training/calibration split, group the entire dataset by image-file
SHA-256. The IDRiD policy is `exclude_conflicts_keep_lexicographic_v1`:

1. Compare the complete source `(Retinopathy grade, Risk of macular edema)`
   tuple, before converting the latter to a binary proxy. If any labels disagree,
   exclude every member of that duplicate group.
2. If all source grades agree, retain the lexicographically smallest qualified
   sample ID and exclude the others. Qualified IDs include the provider partition;
   `idrid/test/` sorts before `idrid/train/`. No test image is moved into training.
3. Preserve the source images and annotations. Apply exclusions only in generated
   analysis manifests. Store individual exclusions locally with reason and hash;
   publish aggregate counts and identities of the audit, without raw image rows.

This excludes eight conflicting copies and two redundant agreeing copies.
The remaining IDRiD cohort is **506 images: 404 provider training and 102 test**.
Each frozen seed uses 303 fitting and 101 calibration images. RIM-ONE remains
485 images (339 provider training and 146 test), with 254 fitting and 85
calibration images. RIM-ONE still rejects any exact duplicate. Require these raw
counts, analysis counts and exclusion counts; unexpected inputs fail the run.

A supplementary screen compared EXIF-oriented RGB pixel hashes and a 63-bit
DCT perceptual hash (32 by 32 luminance, low 8 by 8 coefficients excluding DC).
The pixel hashes recovered the same six IDRiD duplicate pairs. Perceptual
Hamming distance at most two flagged 81 IDRiD pairs, including the six exact
pairs, and no RIM-ONE pairs. Visual review of all six non-identical pairs with
distance zero showed different vessel patterns. This heuristic screen is not
an exhaustive near-duplicate or patient-identity audit and adds no exclusions.
Patient linkage remains unverified; all real metrics remain descriptive at
the image level, now explicitly for the filtered IDRiD provider-test cohort.

## Freeze and execution

Seal the original manifest identity, all original image identities, annotation
identities, policy, exclusion identity and retained analysis identity. Each run
must reproduce the entire sealed audit, including excluded source files.
Commit source/configuration and both protocol documents before generating the
v2 source lock; commit the source lock before experiments. Generate and commit
`experiments/batch3-inputs-v2.json` before any real fitting. The input seal is
separate from the source lock, as in v1. Consumers verify the committed locks;
they do not regenerate them against changed data.

There are no changes to algorithms, metrics, selectors, seeds, models,
hyperparameters, transformations or numerical tolerances. Run all 80 real
records and all 5,760 synthetic records under v2. Compare the v2 synthetic
scientific records and case files to the preserved v1 results, in addition to
an independent v2 reproduction. The previously observed synthetic outcomes
are disclosed; their rerun is a regression/reproduction check.

Execute suites sequentially on CPU, using the original batch size 16, zero
loader workers and two torch intra-op threads. Use the local external-volume
data snapshot; keep the interrupted bulk migration paused. Monitor each
experiment process group, stopping on resident memory above 8 GiB or macOS
critical memory pressure when available. Preserve any failed attempt. Resource
failure does not authorize changing scientific parameters after outcomes.

Reproduce from a clean committed snapshot and a separately installed wheel,
outside the checkout, with hashed locked dependencies. The synthetic environment
must lack optional imaging/model/plot/test packages. The real environment adds
only the imaging extra, reads the preverified checkpoint, and independently
re-extracts features into a fresh output directory. Python network connection,
name resolution, binding and send operations are blocked during real execution;
all Python socket audit events are blocked during synthetic execution. This is
an application-level check, not an operating-system network sandbox.

Require exact scientific records and per-case outcomes, probabilities and
thresholds within absolute tolerance `1e-10`, and independently extracted
features within `atol=rtol=1e-6`. Record exactness separately. Real seed ranges
are not confidence intervals. Reference-path inclusion is not selected-path
safety, treatment benefit or clinical validation. Do not claim comparative
superiority from descriptive differences on these filtered proxy datasets.

Example consumer commands (set DATA_ROOT to the local dataset root):

```sh
uv sync --locked --extra imaging --extra plots
uv run --locked python -m conformal_pathways.benchmarks run --config experiments/batch3-v2.json --suite real --data-root "$DATA_ROOT" --out artifacts/batch3-v2/primary/real
uv run --locked python -m conformal_pathways.benchmarks run --config experiments/batch3-v2.json --suite synthetic --out artifacts/batch3-v2/primary/synthetic
python scripts/reproduce_benchmark.py --config experiments/batch3-v2.json --suite real --data-root "$DATA_ROOT" --wheel /absolute/path/to/wheel.whl --out artifacts/batch3-v2/independent-real
python -m conformal_pathways.benchmarks compare artifacts/batch3-v2/primary/real artifacts/batch3-v2/independent-real/real
```

The reproduction script also accepts `--suite synthetic` without a data root.
Use `scripts/run_monitored.py --help` to wrap any command with the resource guard.
The public evidence package is generated locally; no upload is part of Batch 3.
