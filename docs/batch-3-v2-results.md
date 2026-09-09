# What the Batch 3 v2 evidence supports

The real-image results show a tradeoff, not an established advantage for the
combined method. On filtered IDRiD, `main` produces smaller candidate sets but
lower reference-path inclusion than `model_only`; on RIM-ONE their promoted
metrics agree. The complete [generated report](../evidence/batch3-v2/README.md),
[summary table](../evidence/batch3-v2/summary.csv), and
[paired comparisons](../evidence/batch3-v2/paired.csv) retain every frozen setting.

The [v2 amendment](batch3-v2-amendment.md) was frozen before real fitting. It
excludes ten IDRiD files from generated manifests: all eight copies in four
label-conflicting duplicate pairs, plus two redundant agreeing copies. Source
images and labels are preserved. The filtered cohort has 404 provider-training
and 102 test images; RIM-ONE uses 339/146. Exclusions depend on input and
annotation consistency. These are results for the retained cohort, not the
unmodified IDRiD release or its classification leaderboard.

## Real-image descriptive results

All results below use total alpha 0.1, frozen ResNet-50 features and the specified
training-only logistic regression. Values are means over five training/calibration
splits; parentheses show observed minimum and maximum. The same 102 or 146 test
images recur across seeds. These ranges are **not confidence intervals**, and
the five runs are not independent patient cohorts.

| Dataset | Variant | Reference inclusion, % (seed range) | Mean retained paths |
| --- | --- | --- | --- |
| Filtered IDRiD | main | 84.9 (81.4–93.1) | 4.54 |
| Filtered IDRiD | model_only | 92.0 (89.2–94.1) | 5.83 |
| Filtered IDRiD | rules_only | 100.0 (100.0–100.0) | 18.00 |
| Filtered IDRiD | no_conformal | 100.0 (100.0–100.0) | 18.00 |
| RIM-ONE | main | 97.5 (95.2–100.0) | 5.15 |
| RIM-ONE | model_only | 97.5 (95.2–100.0) | 5.15 |
| RIM-ONE | rules_only | 100.0 (100.0–100.0) | 18.00 |
| RIM-ONE | no_conformal | 100.0 (100.0–100.0) | 18.00 |

For IDRiD, the paired `main - model_only` difference is **−7.06 percentage
points** of inclusion (seed differences −10.78 to −0.98) and −1.29 paths
(−1.95 to −0.29). The mean fraction of violating retained paths falls by 8.14
percentage points, but neither selector's selected-path violation rate improves.
Smaller sets or lower exposure alone therefore do not establish superiority.
All eight promoted RIM-ONE metrics have zero paired differences between these
two variants in this grid.

The IDRiD `main` mean is below the nominal 90% reference-inclusion level. Do not
describe this experiment as achieving 90% coverage on IDRiD. The method's
conditional mathematical statement requires assumptions, including appropriate
exchangeability and grouping, that are not established for these provider
partitions. These observations do not identify the cause of the shortfall or
validate those assumptions. They are retained without changing thresholds,
models, splits, exclusions or tolerances after outcome inspection.

For `main`, selected toy-rule violation rates average 60.0% (IDRiD) and 25.8%
(RIM-ONE) with `observed_rules_first`, and 38.0% and 8.8% with `min_total_score`.
The same respective rates occur for `model_only`. All real settings have zero
empty-set/abstention rates and complete required proxy labels, so the denominator
does not hide an abstention or missing-label tradeoff here. Selector differences
are descriptive; no post-outcome selector choice is promoted as a new result.

The class-prior control has 100% reference inclusion and eight retained paths
for both `main` and `model_only` on both datasets. Rules-only and unpruned controls
retain all 18 paths. High inclusion can consequently arise with little or no
useful discrimination. Reference-path inclusion and the safety of an individual
selected path are different events.

## Synthetic evidence and interpretation

The v2 design preserves all 5,760 synthetic records, seeds and settings from v1.
The [v1 interpretation](batch-3-results.md) describes the synthetic mechanism,
missing-label and tiny-calibration findings. The current
[verification record](batch-3-v2-verification.md) records the complete v2 reruns,
independent comparisons and the check against the earlier synthetic outcomes.
These synthetic outcomes were already known when the input amendment was made;
the reruns are reproduction and regression checks, not a new prospective study.

Real images provide entry model input. IDRiD's macular-edema risk label remains
a retrospective proxy rather than an OCT response; RIM-ONE's disease class is
mapped to a toy status rather than future risk. Patient linkage and
exchangeability remain unverified. Exact-byte duplicate removal and a limited
perceptual screen cannot establish patient independence.

The supported presentation is an experimental toolkit with explicit information
flow, auditable data handling, paired comparisons, and reproducible limitations.
No clinical-safety, treatment-benefit, patient-level coverage, distribution-shift
robustness or comparative-superiority claim is supported. Public-release
clearance remains a separate Batch 4 task.
