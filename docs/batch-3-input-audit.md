# Real-data input audit

Historical v1 audit. The accepted resolution is specified separately in the
[v2 amendment](batch3-v2-amendment.md); this failed audit remains preserved.

Recorded 2026-09-08, after all required images became available locally.
**The frozen input audit failed before real model fitting.** No real input seal,
pretrained feature extraction, fitted real model, or real benchmark result was
created. The frozen implementation and protocol were not changed.

## Observations

| Check | IDRiD | RIM-ONE random partition |
| --- | ---: | ---: |
| Images present | 516 | 485 |
| Provider training / test counts | 413 / 103 | 339 / 146 |
| Unique SHA-256 image contents | 510 | 485 |
| Groups of byte-identical images | 6 pairs | 0 |
| Duplicate pairs crossing provider training/test | 1 | 0 |
| Duplicate pairs with conflicting DR or DME labels | 4 | Not applicable |

The IDRiD annotation files match both hashes in the frozen configuration.
Five duplicate pairs lie within provider training. The sixth spans provider
training and test and has different DR labels. Among the five training pairs,
two have different DR labels, one has different DME labels, and two agree on
both labels. Filename qualification avoids ID collisions but cannot resolve
these content/annotation conflicts.

The selected dataset directories passed byte comparison against their cloud
copies before the audit. All 12 implicated images were also downloaded from the
separate legacy `datasets/IDRiD` source copy and matched the corresponding bytes
in the experiment's `data/idrid` copy. This establishes consistency between those
stored copies, not validation against a freshly obtained provider release.

The [provider data page](https://idrid.grand-challenge.org/Data/) describes a
dataset without duplicated images. The discrepancy between that description
and the stored copies remains unresolved. The provider's IEEE Dataport download
page could not be retrieved during this check; no fresh authoritative download
was verified. Do not attribute the local discrepancy to the provider as an
established fact.

## Execution checks

The local checkout passed Git object integrity checks, and all 68 frozen files
matched their recorded hashes. The pretrained checkpoint matched its configured
SHA-256. A new environment installed the locked imaging and plotting dependencies
and passed all 375 tests in 156.05 seconds, with the one expected missing-image
fixture warning. This run used Python 3.12.13 on Darwin arm64; the earlier
synthetic verification used Python 3.12.14. Timings include local load and are
not performance claims.

The [compact audit record](../evidence/batch3-input-audit.json) contains counts,
hash identities, and status. Per-image diagnostics and labels remain in local
`artifacts/batch3-real-input-audit-failure.json`; the test log is local at
`artifacts/batch3-real-preflight-tests.log`. The prior synthetic evidence remains
unchanged.

## Required resolution

First reconcile the images and annotations with an authoritative provider copy.
Do not guess the correct label for identical images or arbitrarily keep one
conflicting annotation. If source verification confirms the conflicts, specify
a deterministic exclusion or grouping policy, disclose the resulting membership
and counts, and commit a named protocol amendment and new freeze before real
fitting. Preserve this failed audit and the original files. The existing
`batch3-v1` requires all provider images and rejects duplicate bytes; bypassing
that check would violate its specification.

After input resolution, complete and commit the input seal, run every specified
real comparison, and independently repeat fresh feature extraction. Exact-byte
uniqueness alone does not establish absence of near duplicates or verified
patient independence. RIM-ONE passing this duplicate check does not yet establish
a completed benchmark or patient-level coverage.
