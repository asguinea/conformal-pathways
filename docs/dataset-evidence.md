# Dataset evidence and eligibility

Input/provenance review: 2026-09-09. The v2 input audit was sealed before fitting; both real runs now reproduce
exactly. See [verification](batch-3-v2-verification.md).
This document distinguishes provider facts, local inventory, and assumptions.
The benchmark configuration and separate input seal identify exact content;
folder names alone do not identify a reproducible dataset version.

## Selected descriptive datasets

| Dataset | Provider facts and acknowledgment | Local interpretation / boundary |
| --- | --- | --- |
| IDRiD | 516 fundus images, retinopathy and macular-edema risk grades; provider data page states CC BY 4.0. Credit Prasanna Porwal, Samiksha Pachade, Ravi Kamble, Manesh Kokare, Girish Deshmukh, Vivek Sahasrabuddhe, and Fabrice Meriaudeau, *Indian Diabetic Retinopathy Image Dataset (IDRiD)*, IEEE Dataport (2018), DOI 10.21227/H25W98. [Data](https://idrid.grand-challenge.org/Data/), [provider citation](https://idrid.grand-challenge.org/Rules/). | Source partition: 413 training / 103 test images. The disclosed v2 exclusions retain 404 / 102. Retinopathy grades 0–4; risk grade >0 becomes the toy DME proxy. This is not an observed OCT response. Patient linkage is unverified. |
| RIM-ONE DL | 313 normal and 172 glaucoma images; random and hospital partitions provided. Maintainers permit research/education and restrict copying, redistribution, and unauthorized commercial use. Credit Francisco José Fumero Batista, Tinguaro Diaz-Aleman, Jose Sigut, Silvia Alayon, Rafael Arnay, and Denisse Angel-Pereira, *RIM-ONE DL: A Unified Retinal Image Database for Assessing Glaucoma Using Deep Learning*, Image Analysis & Stereology 39 (2020), 161–167, DOI 10.5566/ias.2346. [Maintainer repository](https://github.com/miag-ull/rim-one-dl). | Use only `partitioned_randomly`: 339 training / 146 test. Disease class maps to illustrative low/high, not future risk. No verified patient IDs are inferred from filename stems. The hospital partition is not a second independent cohort. |

Obtain data through the linked providers under their current terms. The code
license does not grant dataset rights. This repository includes neither images,
source annotations, patient manifests, embeddings, nor pretrained/trained weights.
RIM-ONE assets remain local; eligibility for this local research check does not
clear derived assets for public redistribution.

Set a local `DATA_ROOT` containing these provider layouts:

```text
idrid/
  B. Disease Grading/
    1. Original Images/a. Training Set/
    1. Original Images/b. Testing Set/
    2. Groundtruths/a_IDRiD_Disease_Grading_Training_Labels.csv
    2. Groundtruths/b_IDRiD_Disease_Grading_Testing_Labels.csv
rimone/
  partitioned_randomly/
    training_set/{normal,glaucoma}/
    test_set/{normal,glaucoma}/
```

IDRiD resets image numbers between provider partitions. The adapter now uses
partition-qualified IDs (`idrid/train/IDRiD_001`, `idrid/test/IDRiD_001`) and retains
the raw source ID separately. This fixes the collision without inventing patient
identities. Exact label-file SHA-256 values and expected partitions are in the
configuration. The audit requires all original images, applies the frozen IDRiD
exclusion policy, and rejects any RIM-ONE duplicates. It seals raw and retained
content identities and the exclusions before fitting. It does not infer
independence from the absence of identical bytes.

## Resolved input blocker and cohort definition

All 516 IDRiD images and 485 selected RIM-ONE images are local. The v1 audit
rejected six IDRiD duplicate pairs, including one crossing provider partitions.
Four pairs have conflicting source DR or DME grades. The
[historical input audit](batch-3-input-audit.md) is preserved.

The [v2 amendment](batch3-v2-amendment.md) excludes every conflicting copy and
keeps one deterministic representative when source grades agree. Ten IDRiD
files are excluded from the analysis manifest; the original files and labels
are untouched. The filtered cohort contains 404 provider-training and 102
test images. RIM-ONE's 339/146 partition is unchanged. All excluded source bytes,
annotation identities, policy and retained identities are covered by the
[committed input seal](../experiments/batch3-inputs-v2.json). Future consumers
verify this seal; changing data requires a new amendment, not replacing the seal.

For reproducibility, obtain the entire original release, including excluded
images. The runner rebuilds the manifest and verifies the complete audit.
Analysis subsets and individual exclusion records are generated locally.
Dataset images, filenames with grades, embeddings and case records are not
part of the distributed evidence. The exact-byte policy does not establish
patient independence or eliminate every possible near-duplicate relationship.

```sh
uv sync --locked --extra imaging --extra plots
uv run --locked --extra imaging python -m conformal_pathways.benchmarks run --config experiments/batch3-v2.json --suite real --data-root "$DATA_ROOT" --out artifacts/batch3-v2/primary/real
```

For the independent repeat, use `scripts/reproduce_benchmark.py --config
experiments/batch3-v2.json --suite real --data-root "$DATA_ROOT" --wheel
/absolute/path/to/wheel.whl --out artifacts/batch3-v2/independent-real` under
Python 3.12. This creates a fresh environment, checkout and feature directory.
Compare both complete bundles with the benchmark `compare` command. Both real
and synthetic bundles are required for a complete report; omit
`--allow-pending-real` when generating it with `publish-local`.

## Excluded or deferred inputs

| Input | Reason it is outside this frozen benchmark |
| --- | --- |
| EyePACS | The local manifest supplies DR grade but no DME endpoint; it cannot support complete-label DR reference calibration. Patient pairing and access terms require separate verification. |
| Messidor-2 | Local inventory has 1,744 images versus the provider's 1,748. Annotation-file origin and patient/eye pairing are unverified. The provider supplies image pairs and no official grading annotations; third-party annotation provenance must be audited separately. [Provider](https://www.adcis.net/en/third-party/messidor2/). |
| REFUGE | Deferred from this focused two-dataset design; source/terms, annotation mapping, and participant grouping have not been verified. Local images are cloud-only. |
| Existing embedding caches and old result files | No reuse. Fresh features and corrected-run outputs must establish their own provenance under the frozen implementation. |

## Pretrained model identity

The selected ImageNet ResNet-50 checkpoint is `IMAGENET1K_V2` from
[torchvision](https://docs.pytorch.org/vision/stable/models/generated/torchvision.models.resnet50.html).
Its complete SHA-256 is
`11ad3fa62ca79e40addfd354a8ec4b7c75143b3038b8d2a807fbc68deab379ca`.
The existing local checkpoint matched that hash during preparation. Model identity
is not evidence of completed feature extraction. The model and associated data
terms need their own release review; the checkpoint is never bundled here.
