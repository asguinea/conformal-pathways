# Prospective result-aware evaluation protocol

Protocol `batch3-sequential-v1`, specified on 2026-09-09 before its experiment
outcomes. The earlier entry-only descriptive results and all Batch 2 correctness
fixtures are already known. The goal is to measure result-aware behavior and
its limitations with transparent simulated diagnostic information; no clinical
or superiority claim is pre-assumed. The algorithm and toy rules are unchanged
from the completed [sequential contract](sequential-method.md).

## Questions and paired design

1. Does reference retention behave as expected under exchangeable complete
   synthetic episodes, and how large are the realized retained sets?
2. How do actual selected toy violations, abstention, and test usage change when
   diagnostic information becomes available?
3. How do missing or incorrect results affect these outcomes? How does truth-label
   missingness differ from a diagnostic being unavailable?
4. Do the same qualitative effects appear in descriptive simulations using
   identified real images, and do independent executions reproduce them?

Every trial fixes its samples, group splits, and fitted entry predictions across
all four score/filter variants and both selectors. Training uses only its split.
The same preassigned potential diagnostic result is reused across variants and
selectors, and revealed only after commitment to a test.

The sequential mechanisms are: perfect proxy reveal; 20% unavailable results;
20% flipped binary/proxy-class results; and 100% unavailable results. The error
and unavailability specifications apply equally in calibration and test. They
are assumed sensitivity settings, not estimated device performance. Two uniform
draws per group come from the specified seeded generator; the same draws are
shared across arms. Group members share diagnostic error/availability. Results
are never resampled in response to a chosen action or outcome.

The unavailable-result sequential control keeps the stage-local decision policy
fixed and isolates information availability. Its reference/set metrics must
equal the entry-only algorithm's metrics in every trial. The original entry-only
complete-path method is also evaluated with the same predictions. Its selectors
operate on complete paths, so selected-risk comparisons to it change both
information handling and the level at which selection operates; they do not
isolate the value of a diagnostic result.

Variants are main (1,1), model-only (1,0), rules-only (0,1), and unpruned (1,1)
with infinite thresholds. Selection uses fixed (1,1) scores across filter
ablations. Stage budgets are uniform, total alpha 0.1. No thresholds, seed lists,
model hyperparameters, policies, or error rates are tuned after these outcomes.
An implementation change after freezing requires a prospective amendment and
preservation of all prior attempts.

## Synthetic sampling

Reuse the specified analytic generator from the previous benchmark, with a new
seed base and newly generated draws. Each group has two entry measurements and
shared latent truth. Each repetition independently regenerates training,
calibration, and one held-out test group. The known-signal model uses the
generator's analytic posterior; the class-prior control fits only training labels.

| Setting | Repetitions per workflow | Train / calibration / test groups | Models | Result mechanisms |
| --- | --- | --- | --- | --- |
| IID | 128 | 50 / 99 / 1 | Known signal and class prior | All four |
| Missing truth labels | 32 | 50 / 99 / 1 | Known signal | Perfect and unavailable |
| Tiny calibration | 16 | 50 / 9 / 1 | Known signal | Perfect and unavailable |

All settings include the entry-only baseline and all four variants. There are
**11,392 synthetic comparison records**. Missing-label probability is 0.2 per
member in the designated setting. Latent truth is generated before masking and
retained privately for diagnostic simulation; a missing evaluation label is
not automatically a missing diagnostic result. Entire incomplete calibration
groups are excluded; missing test truth remains visible through unavailable
metrics and group denominators. Tiny calibration at alpha 0.1 should produce
infinite per-stage thresholds under the corrected quantile.

## Real-image descriptive simulations

Reuse the sealed raw inputs, source annotations, exact duplicate exclusions,
and retained cohorts from `batch3-inputs-v2.json`. The new source lock includes
that seal's bytes rather than relabeling its original provenance as new evidence.
Rebuild and compare the complete audits before fitting. IDRiD retains 506 images
(404 provider training, 102 held out); RIM-ONE retains 485 (339 training, 146 held
out). All source files remain unchanged. Exact duplicate/conflict handling is
documented in [dataset evidence](dataset-evidence.md).

Seeds 101, 202, 303, 404, and 505 subdivide only the provider training partition
into model fitting and calibration. Held-out images stay fixed. Models are the
training class prior and logistic regression (C=1) on frozen ResNet-50
IMAGENET1K_V2 features. Keep the established checkpoint SHA-256, preprocessing,
CPU device, two Torch threads, batch size 16, and zero workers. Extract features
fresh in both primary and independent runs. All mechanisms/variants/models are
evaluated for both datasets and every seed: **400 real-image comparison records**.

IDRiD's retrospective DME-risk proxy is not a measured OCT response. RIM-ONE's
class proxy is not a measured visual-field/RNFL response or longitudinal risk.
Perfect reveal therefore means perfect knowledge of the proxy, not perfect
clinical testing. Group IDs fall back to image IDs; patient linkage and
exchangeability are not established. These are descriptive simulations, not a
prospective clinical test or a patient-level coverage validation.

## Metrics, uncertainty, and comparisons

Use the [sequential metric definitions](sequential-method.md), including case
and group reference retention, existence of a toy-acceptable realized sequence,
mean realized sequence count, and both selectors' conditional selected violation,
abstention, diagnostic usage, and unavailable-result rates. Export all numerators,
denominators, and unavailable counts. Entry-only does not execute tests, so
executed-test metrics are unavailable for that comparator. Realized sequences
are retrospective projections of a contingent tree, not numbers of policies.

Summaries average repetition metrics. Synthetic group retention has a pointwise
95% Wilson interval; other bounded means and paired differences use conservative
Hoeffding intervals over independent repetitions. A selected-violation metric is
conditional on truth-evaluable completed selections, and its repetition-level
mean excludes unavailable repetitions. Paired differences use jointly evaluable
repetitions. Always report abstention alongside selected violation; different
completion denominators do not support an unconditional risk claim. Intervals
are not adjusted for multiple comparisons. No family-wide superiority inference
will be made from isolated favorable estimates.

Real summaries give means and observed ranges across five seeds. Those seeds
share a test set and are not independent patients; no inferential interval or
significance test is constructed from them. Seeds also determine preassigned
diagnostic error draws, so sensitivity includes both calibration splitting and
the assumed result mechanism.

Predeclared pairs: main minus each other variant within each mechanism; perfect
main minus unavailable, missing20, error20, and entry-only main where present.
Require identical inputs and fitted-model identity for every pair; within a
mechanism, require identical potential-result tables as well. Interpret smaller
sets together with retention, selected violations, and abstention. Preserve
negative, null, and unavailable results.

## Provenance, verification, and completion

Commit the implementation/configuration/this protocol before creating the source
lock. Freeze all package sources, dependency files, both protocol/method documents,
the reused input seal, reproduction script, and memory guard. Both checkout bytes
and installed package bytes must match. Do not relax a mismatch to permit a run.

Local artifacts contain split inputs, latent simulation truth, fitted-model and
prediction identity, full compressed scientific reports, sequential cases/traces,
entry-only case exports, and hashes. Verify metrics by reaggregating cases and
verify the expected complete design before reporting. Errors fail the run and
preserve its attempt directory. Start repeats in new directories.

Reproduction uses an archived clean commit and independently installed wheel
outside the checkout. Synthetic reproduction has only core dependencies; real
reproduction installs the imaging extra and extracts features again. Network
access is blocked during experiment execution. Scientific reports must agree
exactly, including predictions, thresholds, branches, selections, and traces;
fresh feature matrices must be bit-for-bit equal. Only environment metadata and
its enclosing report digest are excluded from direct cross-environment equality,
and each original report digest is still validated. Environment records remain
available. Same-host reproduction does not establish cross-platform identity.

Run suites serially under `scripts/run_monitored.py`, with the existing 8 GiB
process-group RSS guard and critical-memory-pressure stop. Do not resume cloud
transfers. Public candidate evidence contains compact trial metrics, summary
tables, paired differences, plots, and provenance digests; raw real cases,
images, labels, embeddings, and model files remain local.

Completion requires both complete primary suites, independent runs, exact
scientific comparisons, regenerated compact evidence, and a results/limitations
document tied to the actual findings. Public redistribution and GitHub pushing
remain separate Batch 4/owner steps.

```sh
python -m conformal_pathways.benchmarks.sequential freeze --config experiments/batch3-sequential-v1.json
python -m conformal_pathways.benchmarks.sequential run --config experiments/batch3-sequential-v1.json --suite synthetic --out artifacts/batch3-sequential-v1/primary/synthetic
python -m conformal_pathways.benchmarks.sequential run --config experiments/batch3-sequential-v1.json --suite real --data-root "$DATA_ROOT" --out artifacts/batch3-sequential-v1/primary/real
python scripts/reproduce_benchmark.py --engine sequential --config experiments/batch3-sequential-v1.json --suite synthetic --wheel "$WHEEL" --out artifacts/batch3-sequential-v1/independent-synthetic
python scripts/reproduce_benchmark.py --engine sequential --config experiments/batch3-sequential-v1.json --suite real --data-root "$DATA_ROOT" --wheel "$WHEEL" --out artifacts/batch3-sequential-v1/independent-real
python -m conformal_pathways.benchmarks.sequential compare artifacts/batch3-sequential-v1/primary/synthetic artifacts/batch3-sequential-v1/independent-synthetic/synthetic
python -m conformal_pathways.benchmarks.sequential compare artifacts/batch3-sequential-v1/primary/real artifacts/batch3-sequential-v1/independent-real/real
python -m conformal_pathways.benchmarks.sequential publish-local --runs artifacts/batch3-sequential-v1/primary/synthetic artifacts/batch3-sequential-v1/primary/real --out evidence/batch3-sequential-v1
python -m conformal_pathways.benchmarks.sequential verify-evidence evidence/batch3-sequential-v1
```

Wrap each run in the memory guard and record new log paths. `$DATA_ROOT` is an
external local dataset directory; `$WHEEL` is the distribution built from the
matching frozen revision. These commands do not upload or publish externally.
