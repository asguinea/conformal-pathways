# Result-aware experiment evidence

Results use simulated diagnostic proxy responses and illustrative toy predicates. They are not clinical safety or treatment-outcome measurements.

## Primary synthetic setting

Known-signal model, main filter, alpha 0.1. Each repetition has one new independent two-member test group. Intervals are pointwise 95% Wilson intervals for group retention.

| Workflow | Diagnostic information | Group retention [interval] | Mean realized sequences | Selected violation: score / rules | Abstention: score / rules |
| --- | --- | --- | --- | --- | --- |
| dr | perfect | 0.914 [0.853, 0.951] | 3.11 | 0.039 / 0.066 | 0.000 / 0.000 |
| dr | missing20 | 0.938 [0.882, 0.968] | 3.84 | 0.051 / 0.098 | 0.000 / 0.000 |
| dr | error20 | 0.953 [0.902, 0.978] | 3.45 | 0.023 / 0.066 | 0.000 / 0.000 |
| dr | unavailable | 0.930 [0.872, 0.963] | 5.47 | 0.137 / 0.352 | 0.000 / 0.000 |
| dr | entry_only | 0.930 [0.872, 0.963] | 5.47 | 0.137 / 0.352 | 0.000 / 0.000 |
| glaucoma | perfect | 0.953 [0.902, 0.978] | 2.66 | 0.105 / 0.105 | 0.000 / 0.000 |
| glaucoma | missing20 | 0.969 [0.922, 0.988] | 3.13 | 0.105 / 0.141 | 0.000 / 0.000 |
| glaucoma | error20 | 0.984 [0.945, 0.996] | 11.11 | 0.160 / 0.160 | 0.000 / 0.000 |
| glaucoma | unavailable | 0.984 [0.945, 0.996] | 5.02 | 0.105 / 0.266 | 0.000 / 0.000 |
| glaucoma | entry_only | 0.984 [0.945, 0.996] | 5.02 | 0.105 / 0.266 | 0.000 / 0.000 |

## Real-image descriptive simulation

Frozen ResNet-50 features and logistic regression, main filter, alpha 0.1. Values are means across five training/calibration splits sharing the same held-out images; seed ranges in the figure are not confidence intervals.

| Dataset | Diagnostic information | Reference retention | Mean realized sequences | Selected violation: score / rules | Abstention: score / rules | Test ordered: score / rules |
| --- | --- | --- | --- | --- | --- | --- |
| idrid | perfect | 0.904 | 1.69 | 0.027 / 0.029 | 0.047 / 0.047 | 1.000 / 1.000 |
| idrid | missing20 | 0.888 | 2.42 | 0.090 / 0.127 | 0.000 / 0.000 | 1.000 / 1.000 |
| idrid | error20 | 0.865 | 2.40 | 0.104 / 0.141 | 0.000 / 0.000 | 1.000 / 1.000 |
| idrid | unavailable | 0.849 | 4.54 | 0.380 / 0.600 | 0.000 / 0.000 | 1.000 / 1.000 |
| idrid | entry_only | 0.849 | 4.54 | 0.380 / 0.600 | 0.000 / 0.000 | unavailable / unavailable |
| rimone | perfect | 0.947 | 2.25 | 0.088 / 0.088 | 0.000 / 0.000 | 0.355 / 0.355 |
| rimone | missing20 | 0.971 | 3.38 | 0.088 / 0.112 | 0.000 / 0.000 | 0.355 / 0.355 |
| rimone | error20 | 0.975 | 11.52 | 0.137 / 0.137 | 0.000 / 0.000 | 0.355 / 0.355 |
| rimone | unavailable | 0.975 | 5.15 | 0.088 / 0.258 | 0.000 / 0.000 | 0.355 / 0.355 |
| rimone | entry_only | 0.975 | 5.15 | 0.088 / 0.258 | 0.000 / 0.000 | unavailable / unavailable |

![Real-image descriptive simulation](real-results.png)

`score` means the stage-local min-stage-score selector for sequential arms and the complete-path min-total-score selector for entry-only. `rules` also operates at different decision levels. Comparisons to entry-only therefore change more than diagnostic information. The unavailable-result sequential control isolates information availability while preserving the stage-local selector.

Selected violation rates condition on evaluable completed selections. Always read them alongside abstention and test-use rates. They are not an overall harm rate. Realized sequence counts are retrospective projections, not numbers of deployable policies.

Full tables include all variants, class-prior controls, truth-label missingness, tiny calibration, denominators, unavailable counts, and paired differences. Synthetic mean/difference intervals use conservative independent-repetition Hoeffding bounds; there is no multiplicity-adjusted superiority claim. Real uncertainty is descriptive only.

See [the prospective protocol](../../docs/sequential-experiment-protocol.md), [method](../../docs/sequential-method.md), and [dataset provenance](../../docs/dataset-evidence.md). Public files exclude raw real-image cases, labels, images, and model artifacts.
