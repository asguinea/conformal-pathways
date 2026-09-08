# Provenance and licensing inventory

Inventory date: 2026-09-08. This records what is included and what remains to be
verified; it is not redistribution clearance.

## Project source

The starting source is a selectively migrated prototype supplied by the project
owner. The migration includes the reusable Python modules, 36 synthetic test
modules, and a result-plotting script. Package imports were renamed. Packaging,
documentation, the small demo CLI, and installation verification were added here.
The repository starts with a fresh history.

No explicit license or copyright notices were found in the migrated source at
inventory time. That absence does not establish sole ownership. The owner still
needs to confirm authorship, collaborators, organizational rights, and any
third-party source adaptation. Preserve any attribution identified during that
review. Select and add the public code license only after that confirmation.

No public repository URL, author identity, license grant, or citation metadata
has been invented. A development-only package classifier blocks accidental PyPI
upload through tooling that honors `Private :: Do Not Upload`; it does not
prevent Git publication or replace the release review.

## Included and excluded assets

| Asset | Included? | Status |
| --- | --- | --- |
| Python source and generated-fixture tests | Yes | Authorship confirmation pending |
| New documentation and packaging | Yes | Project development material; license selection pending |
| Synthetic records / solid-color test images | Generated at runtime | No real participant records or downloaded imagery |
| Real dataset images and annotations | No | Obtain independently under the relevant terms |
| Dataset manifests, patient IDs, cached embeddings, model weights | No | Distribution rights and privacy review required before adding any derived asset |
| Benchmark outputs and local result traces | No | Fresh evidence required under the corrected protocol |
| Vendored third-party libraries | No | Installed from public registry; versions and hashes in `uv.lock` |

## Dataset adapters

Adapters describe file layouts; their presence does not grant access to or rights
over a dataset. Exact archive versions, checksums, accepted terms, annotation
sources, and permitted uses must be recorded before a dataset benchmark.

| Adapter | Provenance entry point | Current label interpretation | Outstanding checks |
| --- | --- | --- | --- |
| IDRiD | [Provider portal](https://idrid.grand-challenge.org/) | Retinopathy grade; macular-edema risk converted to Boolean | Portal retrieval was unavailable during this inventory; verify terms and grading semantics. The converted risk label is a proxy, not an OCT result. |
| Messidor-2 | [ADCIS](https://www.adcis.net/en/third-party/messidor2/) | Severity and binary adjudicated DME from a caller-supplied annotation CSV | Review image terms and the separate origin/terms of the actual annotation file. |
| EyePACS | [Kaggle competition](https://www.kaggle.com/competitions/diabetic-retinopathy-detection) | Retinopathy grade; DME unavailable | Record exact source and accepted access terms; verify patient pairing from IDs. |
| REFUGE | [Provider portal](https://refuge.grand-challenge.org/) | Folder labels mapped to illustrative high/low status | Portal retrieval was unavailable during this inventory; verify access terms and avoid interpreting a disease class as a clinical risk estimate. |
| RIM-ONE DL | [Maintainer repository](https://github.com/miag-ull/rim-one-dl) | Folder labels mapped to illustrative high/low status | Verify dataset version, terms, participant grouping, and preservation of official partition hints. |

Provider links are provenance leads, not legal conclusions. Do not infer that
public download availability permits redistribution. No real dataset was downloaded
for Batches 1 or 2.

## Dependencies and pretrained assets

| Component | Role | Provenance / release task |
| --- | --- | --- |
| NumPy, pandas | Core numeric and tabular processing | Registry resolutions and hashes in `uv.lock`; include applicable notices if redistributing dependencies |
| scikit-learn | Optional embedding classifier | `models` / `imaging` extra; same version-specific license review |
| PyTorch, torchvision, Pillow | Optional image processing and embeddings | `imaging` extra; review package notices separately from weights |
| matplotlib | Optional plotting | `plots` extra; retain required notices for any redistributed dependency assets |
| pytest, build, setuptools, wheel, Ruff | Development and build tools | Locked development group; not vendored in this repository |
| torchvision ResNet-50 weights | Optional externally fetched model | Not included; exact weight identity, checksum, transform, and applicable training-data/weight terms remain to be recorded |

The [torchvision model documentation](https://docs.pytorch.org/vision/stable/models.html)
distinguishes pretrained assets and their use conditions from library code.
The corrected extractor requests explicit `IMAGENET1K_V2` weights and the
associated transform. Loading failures propagate. A separately seeded random
baseline is explicit in provenance. Generated-image CPU checks passed in Batch 2;
real pretrained extraction and dataset-level reproduction remain Batch 3 work.

## Public-release decisions still required

- Confirm source ownership and required acknowledgments; choose a code license.
- Complete a version-specific direct/transitive dependency license inventory.
- If publishing dataset-derived outputs, establish their rights and privacy
  treatment independently of the source-code license.
- Review the final repository history and distribution contents after all fixes.

None of these pending decisions prevents local development or the synthetic
installation exercise. They do prevent declaring the project cleared for release.
