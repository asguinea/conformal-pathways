# What the synthetic evidence supports

These observations describe the frozen `batch3-v1` experiment. They do not
establish performance on retinal images. [Generated results](../evidence/batch3-v1/README.md),
[all summaries](../evidence/batch3-v1/summary.csv), and
[paired comparisons](../evidence/batch3-v1/paired.csv) retain the complete design.
The [protocol](experiment-protocol.md) defines populations, metrics, and intervals.

## Primary setting

At alpha .1 with the known-signal model, `main` retained every group member's
reference path in 123/128 independent DR repetitions (96.1%; approximate 95%
Wilson interval 91.2–98.3%) and 125/128 glaucoma repetitions (97.7%; 93.3–99.2%).
Mean retained-set sizes were 5.40 and 4.75 paths, respectively, out of 18.
These are observations under the invented mechanism, not a proof of coverage
on a different population. The conditional mathematical argument has separate
assumptions documented in the method.

`model_only` achieved 125/128 DR inclusions and a mean of 5.21 paths; its primary
glaucoma summaries equal `main`. The paired uncertainty estimates do not
establish an advantage for the combined score. `rules_only` and `no_conformal`
retained all 18 paths in the primary setting. Their 100% reference inclusion
comes with no set reduction. The class-prior control retained eight paths and
had 100% inclusion, showing why coverage alone is an insufficient utility measure.

The primary selected toy-rule violation rates for `main` were 32.8% (DR) and
21.1% (glaucoma) using `observed_rules_first`, versus 12.1% and 7.4% using
`min_total_score`. These are mean repetition rates; all primary cases were
evaluable and no primary sets were empty. There was no prespecified inferential
contrast between the selectors, so these are descriptive observations, not a
basis for selecting a winner after test inspection. The reported intervals for
individual rates are conservative Hoeffding intervals in the full tables.
The names containing `unsafe` identify toy predicates, not clinical outcomes.

High reference inclusion therefore does not make an individual selected path
safe, even under this simplified rule system. The project should be presented as
an auditable experimental toolkit with reproducible mechanisms and limitations;
this experiment does not support a claim of clinical safety or superiority.

## Stress scenarios and limits

All 128 tiny-calibration records retained 18 paths with unbounded thresholds,
as specified by the corrected quantile rank. This exposes a limitation of
small calibration sets rather than concealing it through threshold truncation.

In the missing-label scenario, group inclusion was evaluable in only 44/64 DR
repetitions and 40/64 glaucoma repetitions; the others remain unavailable.
For `main`, inclusion among those complete groups was 42/44 and 39/40.
Eligible calibration-group counts ranged from 51–73 (DR) and 54–75 (glaucoma)
out of 99. Case-level rule metrics have different eligible populations: 106/128
DR cases and 99/128 glaucoma cases. A reader must not substitute these case
counts for the number of independent groups or treat missing outcomes as safe.

Intervals across the full design are pointwise, with no multiplicity-adjusted
superiority test. The IID experiments use 128 independent repetitions per
workflow; the missing-label and small-calibration scenarios use fewer. The
analytic model has privileged knowledge of generator parameters. No patient
outcomes, diagnostic responses, deployment study, distribution-shift experiment,
or completed real-image benchmark is represented in this evidence package.
