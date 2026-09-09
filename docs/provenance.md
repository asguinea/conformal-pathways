# Provenance and distribution boundaries

Release review: 2026-09-09, version 0.4.0.

## Project source and license

Conformal Pathways is maintained by Alejandro Sanchez Guinea (`asguinea`). The
starting source was a selectively migrated prototype supplied by the project
owner. This repository has its own history and package namespace. The source
inventory found no inherited copyright/license notices or vendored third-party
implementation. This records the review, not a claim that absence of notices
proves sole authorship.

The maintainer selected Apache-2.0 for publication. [LICENSE](../LICENSE) contains
the unmodified license, and [NOTICE](../NOTICE) identifies the project and dataset
acknowledgments. The license applies to project-owned source and documentation;
it does not grant rights to external datasets, pretrained assets, or dependencies.
See the [Apache application guidance](https://www.apache.org/foundation/license-faq.html#Apply).
Future contributions must identify third-party adaptations and their terms.

## Distributed assets

| Asset | Distribution decision |
| --- | --- |
| Project Python source, tests, scripts and documentation | Included under Apache-2.0 |
| Synthetic fixtures | Generated at runtime; no downloaded images or participant records |
| Synthetic and aggregate real-image evidence | Included: trial-level aggregate numerators/denominators, calibration thresholds, statistical tables, research figures and provenance digests |
| Dataset images, source annotations and provider code | Excluded |
| Patient/image manifests, individual exclusions, per-image predictions and diagnostic traces | Excluded; recreated locally by authorized dataset users |
| Embeddings, trained classifiers and pretrained checkpoints | Excluded |
| External Python packages and native/GPU libraries | Not vendored; exact resolved versions and hashes are in `uv.lock` |
| Local logs, credentials, environments, caches and build directories | Excluded by tracked-file and distribution audits |

Compact real records summarize fixed evaluation cohorts of 102 IDRiD or 146
RIM-ONE images. They contain no per-image labels, identifiers, image bytes, or
patient linkage. Digests identify aggregate input/model/report content for
reproduction; they are not distributed source records. The release includes
statistical research outputs, not copies or subsets of the source databases.
This boundary is not an assessment of every possible future derived artifact.
Review any new export independently before adding it.

## External datasets and weights

IDRiD's provider describes CC BY 4.0 data and requests attribution. RIM-ONE DL's
maintainers permit research/education while prohibiting copying, redistribution,
and unauthorized commercial use. Its images, annotations and provider software
are not included. Required dataset credits and links are retained in
[NOTICE](../NOTICE) and [dataset evidence](dataset-evidence.md).

The real-image simulations used externally obtained ResNet-50 weights. The
[torchvision documentation](https://docs.pytorch.org/vision/stable/models.html)
notes that pretrained assets can carry conditions from their training data.
Neither a library license nor this project's Apache license licenses those
weights for every use. The checkpoint identity and transform are documented;
users obtain and use it independently under applicable terms.

Other adapters (EyePACS, Messidor-2, REFUGE) describe local layouts only. They do
not download data or grant access rights and were not promoted as verified
benchmarks. See the dataset document for their limitations and provenance leads.

## Dependencies, history, and evidence

The [version-specific dependency inventory](dependency-licenses.md) covers all
locked resolutions, including optional platform-specific native packages.
Metadata is a review aid, not a relicensing of third-party components. No binary
redistribution bundle, container image, or pretrained model is provided.

The release preserves the evaluated source tags and evidence bytes. Its
scientific Python source is unchanged from `sequential-benchmark-v1`; packaging
metadata and development tooling have advanced to 0.4.0. Use the original
checkout and wheel for frozen experiments. See [reproduction](reproducing.md)
and the [release verification](release-verification.md).
