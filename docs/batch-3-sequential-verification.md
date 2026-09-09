# Batch 3: sequential experiment verification

Completed on 2026-09-09 for the stated research scope. Both result-aware suites
reproduce exactly on the recorded host. The [machine-readable record](../evidence/batch3-sequential-verification.json)
contains source identity, environment records, comparisons, resource measurements,
and additional audits. This does not constitute public-release clearance.

## Prospective source and input identity

The implementation and [protocol](sequential-experiment-protocol.md) were committed
in `68b44d3`, then frozen in `8acc76d`, before benchmark execution. Git tag
`sequential-benchmark-v1` preserves that checkout. The freeze covers 82 source,
configuration, dependency, method, script and input-seal files. No frozen file
changed after the outcomes. The new protocol reused the exact existing data
seal after complete raw-input/exclusion audits matched it for both datasets.

Source SHA-256:
`9a7152d2931ccfc0aeec5ef5fd3de036e70365f04208c79430488f386bba3328`.

Both repeats installed the matching 0.4.0.dev0 wheel outside a clean archived
checkout, with locked hashed dependencies. Wheel SHA-256:
`5d27d7c19842168bd4af2fdbf75b0bdc2bdcf616c4e86616ead0554f7ec4e6a8`.
Synthetic repetition ran with only core dependencies; real repetition installed
the imaging extra and extracted features again. Network operations were blocked
during experiment execution. Setup could access the package registry; no data
or model download was needed.

## Completed runs and comparisons

| Suite | Primary records / seconds | Independent records / seconds | Scientific agreement |
| --- | --- | --- | --- |
| Synthetic | 11,392 / 267.67 | 11,392 / 339.59 | Exact |
| Real-image simulations | 400 / 253.35 | 400 / 315.53 | Exact |

All predictions, calibration thresholds, retained branches, selected actions,
case outcomes and sequential traces match exactly. Both fresh real feature
matrices are bit-for-bit identical, with maximum absolute difference 0.0.
Environment metadata and its enclosing report hash are the only predeclared
scientific-comparison exclusions; every original report hash is still validated.
The environments remain recorded rather than silently erased.

Additional byte comparisons cover all 2,512 entry-only case CSVs, 362 saved
input bundles, and 628 fitted-model provenance records across the two suites.
All are exact between primary and independent runs. No tolerance was widened,
no failed condition was dropped, and no experimental run required a source
amendment or rerun after changing the method.

## Correctness and retained evidence

- Preflight: 445 tests passed in 14.35 seconds, with one existing intentional
  EyePACS missing-image fixture warning. After adding the entry-group
  reaggregation check, all three focused benchmark tests passed again. Ruff
  and changed-file whitespace checks passed.
- Both fresh preflight dataset audits matched the existing seal: 506 IDRiD
  images and 485 RIM-ONE images. Source images, labels and exclusions were not
  changed. All 24 earlier tracked evidence/protocol files remain byte-identical
  to `baseline-entry-v2`.
- The 80 newly rerun real-image entry-only baselines reproduce all earlier
  metrics, fitted-model identities, calibration and case fingerprints. For
  this historical comparison, CSV columns are aligned by name; invocation IDs
  and an unused unpruned CSV alpha field are excluded. The newer protocol lists
  selectors in a different order but does not change their definitions.
- The post-run trace audit checks 79,360 initial policy decisions. Initial
  thresholds and decisions agree across all diagnostic mechanisms; result events
  follow diagnostic commitment. The script is available at
  [scripts/audit_sequential_results.py](../scripts/audit_sequential_results.py).
  This additional read-only audit does not alter the frozen experiment.
- All 384 tiny-calibration records have infinite thresholds and all 18 realized
  sequences. Missing-truth-label runs exclude between 23 and 48 of their 99
  calibration groups, reporting the exclusions explicitly.
- The public candidate evidence has 11,792 compact records, 2,496 summary rows,
  and 2,352 paired rows. Every table regenerates exactly. The generated figure
  was visually checked. Raw real-image cases, labels, images, features and
  models remain local.

## Resources and remaining scope

All four experimental runs were serial and monitored with the existing 8 GiB
process-group RSS guard. Maximum sampled RSS was 1,587,264 KiB (about 1.51 GiB),
with normal macOS memory pressure throughout. The guard polls every two seconds;
these are sampled process-group measurements, not exact allocation peaks.
Verification and table generation are separate read-only analysis work.
The cloud migration remained paused.

Local run directories, logs, archived checkouts, independently installed
environments, distributions and comparison records are preserved under
`artifacts/batch3-sequential-v1/`. The full experiment and repeat commands are
in the [prospective protocol](sequential-experiment-protocol.md). To repeat the
additional historical/trace audit, use the documented primary output paths and
the preserved `artifacts/batch3-v2/primary/real` baseline, then run:

```sh
python scripts/audit_sequential_results.py
python -m conformal_pathways.benchmarks.sequential verify-evidence evidence/batch3-sequential-v1
```

The [results and limitations](batch-3-sequential-results.md) distinguish gains
from diagnostic information, filtering, and selection. They preserve negative
and null findings. These simulations do not establish actual diagnostic-response
validity, patient-level exchangeability, clinical safety, universal superiority,
or cross-platform reproducibility.

**Batches 2 and 3 are complete. Batch 4 public-release preparation remains.**
There is no need to repeat these batches for the currently stated scope.
No repository was pushed and no package or release was published externally.
