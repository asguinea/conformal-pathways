# Public research release verification

Version 0.4.0, prepared on 2026-09-09. The source repository is
[asguinea/conformal-pathways](https://github.com/asguinea/conformal-pathways).
This records release engineering and asset review; the scientific claims and
limitations remain in the [claim register](claims.md).

## Scientific continuity

All 74 scientific package files are byte-identical to the evaluated
`sequential-benchmark-v1` snapshot. The original benchmark locks, source tags,
and evidence files are retained. Release metadata changes the package version
to 0.4.0 and adds licensing/URLs; development tooling adds scoped static typing
and upgrades the build backend. No experimental outcome was changed or rerun
to improve the release's headline results.

Both original source freezes are checked against their Git tags by
`scripts/audit_release.py`. The release's packaging changes intentionally make
its current checkout differ from the old complete freeze. The
[reproduction guide](reproducing.md) directs users to the correct original
checkout and wheel. Batches 2 and 3 remain complete.

## Local validation

- Full generated-data and generated-image suite: 445 passed, with the existing
  intentional EyePACS missing-image fixture warning, under Python 3.12.13 on
  macOS arm64. The run took 16.35 seconds.
- Ruff lint and Python formatting, strict typing of the release-audit script,
  and Actionlint workflow checks are part of release validation. Static typing
  does not cover the entire scientific package.
- All three distributed evidence bundles regenerate their tables and pass
  integrity/design checks without accessing real datasets.
- The source archive and wheel are built with the locked tools and inspected
  for their permitted contents. The wheel is installed in a clean environment
  outside the checkout and both entry/sequential demos run with core
  dependencies, including with Python network operations blocked.
- The public quick start passed from a clean Git checkout: 430 core tests
  passed, 12 optional checks skipped, and both sequential demos completed.
  The 11 additional portable-audit regression checks also pass. Benchmark
  records are not used as substitutes for installation checks.

## Asset and dependency review

The maintainer selected Apache-2.0. LICENSE, NOTICE, software citation,
contribution guidance, security reporting, and the
[version-specific dependency inventory](dependency-licenses.md) are included.
The inventory covers all 64 external package/version resolutions and returned
no known PyPI advisory for the current locked versions at review time.

The build backend was upgraded from setuptools 82.0.1 to 83.0.0 because of
[GHSA-h35f-9h28-mq5c](https://github.com/advisories/GHSA-h35f-9h28-mq5c).
The historical locks remain unchanged. This repository's asset boundaries are
also checked directly rather than relying only on filename exclusions.

Current tracked contents and every reachable historical blob/commit were
reviewed for unexpected files, private machine paths, identifiers, and local
source references. Gitleaks 8.30.1 scans the full Git history. Its generic API-key
rule initially reported the generated 20-hex-character trial identifiers.
These are context hashes created by the benchmark, not credentials. The
committed exception applies only to that exact JSON field format in the three
known aggregate evidence files; every other rule/path remains enabled. The
reviewed history scan reports no secrets.

No dataset images, source annotations, patient/image manifests, per-image
traces, model files, feature caches, credentials, or local run logs are tracked
or included in distributions. Dataset credits and external terms remain
explicit. See [provenance](provenance.md). This release does not license external
assets or establish the privacy of arbitrary future exports.

## Continuous checks

The CI workflow uses immutable action commit pins, read-only repository
permissions, non-persisted checkout credentials, bounded jobs, and no privileged
pull-request trigger. It checks core Python 3.11–3.14 on Linux, numerical/plotting
extras on Linux, and the full generated-image suite on macOS arm64. The release
job checks lint, scoped typing, tags/source integrity, evidence, secrets, builds,
and isolated installation. The [Actions page](https://github.com/asguinea/conformal-pathways/actions)
records the actual hosted outcomes; CI coverage is not a cross-platform
numerical reproduction claim.

Dependency update proposals are enabled for the lock and pinned Actions.
Changes to dependencies do not rewrite historical benchmark locks or evidence.
No package-registry upload, dataset upload, pretrained-model publication, or
clinical deployment is configured.

The first hosted run passed all six software test jobs. Its strict Linux table
regeneration check failed, so a separate portable aggregation audit was added.
It preserves exact file hashes, design, counts, means, ranges and identifiers,
allowing at most 1e-12 absolute difference only in interval endpoints. Each run
reports actual differences. Eleven regression checks reject changed means,
counts/ranges, missing endpoints, non-finite values and material interval changes.
The original exact verifier, experiment locks and evidence are unchanged. This
is a release-engineering check, not a new experiment or a retroactive change
to the original reproduction criterion.

Hosted Linux diagnostics measured a maximum absolute endpoint difference of
1.1102230246251565e-16: 40 differing endpoint entries across the sequential
JSON/CSV summaries, and four in each entry-only bundle. All counts, means, ranges,
identifiers and evidence-file hashes agreed exactly. The portable audit and
Linux distribution/installation checks then passed. The updated core Python 3.12
job passed 441 tests with 12 optional skips; the scientific package is unchanged.
