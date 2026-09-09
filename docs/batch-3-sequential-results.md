# Result-aware evaluation: results and limitations

The frozen `batch3-sequential-v1` experiment evaluates diagnostic commitment,
result delivery, and subsequent decisions. Its 11,392 synthetic records and
400 real-image simulation records cover the prospective design. See the
[complete evidence](../evidence/batch3-sequential-v1/README.md),
[protocol](sequential-experiment-protocol.md), and
[verification record](batch-3-sequential-verification.md).

The results support a reproducible study of result-aware filtering and decision
policies. They do not establish clinical safety, a universal advantage over
baselines, or that conformal filtering itself causes a large reduction in
selected violations. Diagnostic information, set construction, selection, and
abstention have distinct effects.

## Primary real-image simulation

These are means across five seeds with fixed held-out images, using frozen
ResNet-50 features, logistic regression, the main filter, and alpha 0.1. The
diagnostic outcomes are simulated retrospective proxies. Selected violation
conditions on truth-evaluable completed executions; read it with abstention.

| Dataset / result mechanism | Reference retention | Mean realized sequences | Score selector violation | Rules selector violation | Abstention, both selectors |
| --- | --- | --- | --- | --- | --- |
| IDRiD / perfect proxy | 90.39% | 1.69 | 2.66% | 2.86% | 4.71% |
| IDRiD / 20% unavailable | 88.82% | 2.42 | 9.02% | 12.75% | 0% |
| IDRiD / 20% incorrect | 86.47% | 2.40 | 10.39% | 14.12% | 0% |
| IDRiD / no results | 84.90% | 4.54 | 38.04% | 60.00% | 0% |
| RIM-ONE / perfect proxy | 94.66% | 2.25 | 8.77% | 8.77% | 0% |
| RIM-ONE / 20% unavailable | 97.12% | 3.38 | 8.77% | 11.23% | 0% |
| RIM-ONE / 20% incorrect | 97.53% | 11.52 | 13.70% | 13.70% | 0% |
| RIM-ONE / no results | 97.53% | 5.15 | 8.77% | 25.75% | 0% |

Both main selectors order the diagnostic for every IDRiD image and for an
average 35.48% of RIM-ONE images. Initial decisions and diagnostic-use rates
are identical across the four result mechanisms: the new information affects
later decisions, and calibration adapts its later-stage thresholds to the
specified result mechanism. The model, split and selector stay fixed within
each paired comparison. Actual unavailable proportions differ slightly from
the assumed 20% rate because the diagnostic outcomes are finite seeded draws.

Perfect proxy information substantially reduces IDRiD selected toy violations
relative to the matched no-result control, with some downstream abstention.
On RIM-ONE, it reduces realized set size and the rules-first selector's violations;
the score selector's violation rate does not improve. Incorrect glaucoma results
can expand retained sets and worsen actual selections even while reference
retention remains high. Retaining an acceptable reference is not a bound on
the violation rate of an arbitrary selected sequence.

## What the ablations do and do not show

| Perfect-proxy setting | Main | Model-only filter | Unpruned |
| --- | --- | --- | --- |
| IDRiD reference retention | 90.39% | 84.51% | 100% |
| IDRiD mean realized sequences | 1.69 | 1.56 | 18 |
| IDRiD score-selector violation | 2.66% | 10.91% | 2.94% |
| IDRiD abstention | 4.71% | 4.71% | 0% |
| IDRiD diagnostic ordered | 100% | 70.78% | 100% |
| RIM-ONE reference retention | 94.66% | 94.66% | 100% |
| RIM-ONE mean realized sequences | 2.25 | 2.25 | 18 |
| RIM-ONE score-selector violation | 8.77% | 8.77% | 8.77% |

The large IDRiD gain relative to no results should not be attributed primarily
to conformal filtering. With the same perfect proxy information, the unpruned
score selector already has a 2.94% violation rate and no abstention. Filtering
reduces its 18 possible realized sequences to 1.69 on average, trades away some
reference retention, and sometimes abstains. Conditional selected-violation
rates with different completion denominators are not directly an overall
benefit estimate.

In the IDRiD perfect-proxy setting, main retains more references and has fewer
selected violations than model-only, but orders substantially more tests and
has slightly larger sets. On RIM-ONE, main and model-only agree on the promoted
perfect-proxy outcomes. These findings support specific descriptive trade-offs,
not universal superiority or demonstrated cost effectiveness. The toy workflow
does not model real diagnostic costs or harms.

The full tables also retain rules-only, class-prior, error and missingness
ablations. In particular, result errors need not change every metric monotonically:
they also change calibration thresholds and the heuristic selector's behavior.
We do not select only favorable settings or reinterpret an assumed test-error
rate as measured diagnostic accuracy.

## Synthetic reference retention

For the IID known-signal model with main filtering and perfect proxy results,
group reference retention is 91.41% for DR and 95.31% for glaucoma. Pointwise
95% Wilson intervals are [85.27%, 95.13%] and [90.15%, 97.83%], respectively,
over 128 independent repetitions per workflow. These are compatible with the
specified marginal retention construction; finite Monte Carlo estimates do not
prove a distribution-free guarantee. The mathematical argument and its
assumptions are in the [method](sequential-method.md).

Corresponding mean realized set sizes are 3.11 and 2.66. Missing-truth-label
experiments preserve latent diagnostic simulation while explicitly excluding
incomplete calibration groups and recording unavailable test metrics. Tiny
calibration uses the corrected infinite-threshold behavior. Full denominators,
paired differences, and conservative intervals are in the evidence tables.
Intervals are pointwise, not a multiplicity-adjusted superiority analysis.

## Boundaries for public claims

These experiments implement the staged purpose: choose a test, receive its
result, and update later decisions. The earlier entry-only results remain valid
baseline evidence and reproduce unchanged in all 80 real-data comparisons.
They were not an evaluation of this result-aware behavior.

The real diagnostic responses are still simulated: an IDRiD DME-risk label is
not a paired OCT response, and a RIM-ONE class label is not a visual-field/RNFL
measurement. Perfect proxy reveal is an optimistic information condition. The
error/missingness settings are declared sensitivity assumptions. No treatment
outcomes or clinical guideline compliance are measured.

Provider test images remain fixed across seeds. Seed ranges describe sensitivity,
not independent patients or confidence intervals. Patient linkage and
train/test exchangeability remain unverified. For example, IDRiD perfect-proxy
reference retention ranges from 87.25% to 95.10% across seeds despite a mean near
90%; the mean alone does not establish a dataset-level guarantee. A subset of
the sensitivity settings also has below-nominal empirical retention.

The public project can accurately present an auditable research implementation,
controlled diagnostic-information simulations, reproducible descriptive image
experiments, finite-sample reference-retention assumptions, and explicit failure
modes. Clinical deployment, a selected-action safety guarantee, and broad
superiority remain unsupported claims.
