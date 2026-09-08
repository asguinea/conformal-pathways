# Behavioral contract

Version 0.2.0.dev0 implements the entry-observation protocol specified in
[method](method.md), with [toy-rules-v2](toy-rules.md). The scope is complete
open-loop paths; adaptive decision policies and online calibration are not
supported. Breaking API and metric changes invalidate comparisons to older
experimental outputs.

## Inputs, splits, and state

- Sample IDs are globally unique strings, preserved through CSV loading. Group
  identities are namespaced by dataset and identity kind. Cross-source patient
  linkage requires an explicit `global_patient_id`; absent identity falls back
  to a sample group without claiming patient independence.
- Training, calibration, and test splits are disjoint at the declared group
  level and cover every supplied sample exactly once. Official hints are honored
  unless repartitioning is explicitly requested and recorded. Group splitting
  alone cannot establish that the declared identities or exchangeability are true.
- Only explicit stage-zero observations reach built-in prediction and selection.
  Target labels and arbitrary metadata are absent from `PredictionInput`.
  Observation columns must be separate from target columns. Retrospective labels
  belong only to fitting, reference calibration, and outcome evaluation.
- A diagnostic result is an explicit, action-matched, stage-matched observation.
  Positive, negative, and unavailable values are distinct. A skipped or merely
  hypothetical diagnostic does not reveal its hidden result. Observed values
  can change subsequent action preferences in a separately executed transition.
- The reference path is privileged and deterministic. Selection uses entry
  observations, fixed scoring, and deterministic tie breaks. An empty candidate
  set produces abstention; exceptions are errors and terminate evaluation.

## Calibration and sets

Use one stagewise maximum over each fully labelled calibration group. Exclude
incomplete groups as groups, report exclusion counts, and reject empty eligible
calibration sets. Training/calibration group overlap is rejected. Quantiles use
`ceil((n + 1) * (1 - alpha_t))`, with infinity if the rank exceeds n. Acceptance
includes ties. Budgets and scoring are fixed before calibration, finite inputs
are checked, and allocated budgets sum conservatively to at most alpha.

`variance_weighted`, scalar-uncertainty scoring, arbitrary path truncation, and
hidden DME cohort filtering are rejected. Action preferences have the explicit
heuristic interpretation in [method](method.md). The unpruned baseline is the
full 18-path Cartesian product and does not require calibration labels.
All evaluation entry points share the same implementation.

## Metrics and denominators

Let P be the retained set, r the reference, and V(p) the versioned toy violation
predicate. Rule eligibility requires every label needed by that workflow.
Missing required labels yield unavailable outcomes with a reason. Invalid labels
fail. A zero denominator yields `None` / JSON `null`, not zero.

| Export | Definition and denominator |
| --- | --- |
| `oracle_retained` | r is in P, averaged over reference-evaluable cases; empty sets are false |
| `group_oracle_retained` | All members' reference paths retained, averaged over fully evaluable declared test groups; a partially labelled group is unavailable |
| `existential_safe` | At least one nonviolating path in P, averaged over rule-evaluable cases; empty sets are false |
| `any_unsafe_rate` | At least one violating path, averaged over rule-evaluable nonempty sets |
| `unsafe_exposure` | Violating count / set size, macro-averaged over rule-evaluable nonempty sets |
| `chosen_unsafe_rate__POLICY` | Violating selections / rule-evaluable, non-abstaining selections |
| `chosen_empty_rate__POLICY` | Explicit abstentions / all evaluated cases |
| `chosen_label_missing_rate__POLICY` | Missing required labels / all evaluated cases, including abstentions |
| `set_size`, `empty_set_rate` | Mean size and empty-set frequency over all evaluated cases |
| `topK_has_safe_rate__POLICY` | At least one acceptable returned path, over rule-evaluable cases |
| `topK_all_safe_rate__POLICY` | All returned paths acceptable, over rule-evaluable cases; empty sets are false |

Top-k returns min(k, set size) paths and exports actual count and completeness.
Every rate/mean has `__numerator`, `__denominator`, and `__unavailable`; for a
mean the numerator is a sum, not an event count. Missing outcomes and abstentions
have separate fields; their counts may overlap. Runtime summaries are descriptive
per-case durations. The allocation-ablation summary explicitly identifies an
unweighted mean of run metrics, with run-count denominators and a link to the
raw result table; it is not a pooled patient estimate or an uncertainty interval. `chosen_error_rate` is zero for completed runs because errors
abort; it does not estimate failures across attempted runs.

Per-case records include declared group IDs and can regenerate aggregates.
Subgroup means exclude unavailable values and report actual denominators;
all-unavailable groups cannot become a reported worst group. A rule violation
is not a measured patient harm. Group-respecting uncertainty estimates and
promoted quantitative results remain Batch 3 work.

## Batch 2 correction evidence

| ID | Resolution | Independent evidence |
| --- | --- | --- |
| R1 | Strict Boolean/grade parsing; explicit diagnostic provenance and availability | `test_correctness_contract.py`, workflow tests, adapter validation tests |
| R2 | Label-free inference boundary; hypothetical paths have no hidden results | Hidden-label/metadata perturbation tests for sets and every selection policy; future observations excluded |
| R3 | Missing rule labels yield unavailable outcomes; cohorts remain visible | Mixed-label pipeline and denominator fixtures |
| R4 | Correct rank with infinite threshold; decimal boundary handling | Exact rational order-statistic examples, ties, leave-one-out rank checks, invalid inputs |
| R5 | Only fixed, calibration-independent allocations | Budget boundary tests, including zero/subnormal alpha; adaptive mode rejected |
| R6 | Declared group maxima, duplicate/split guards, official partitions preserved | Hand-computed grouped scores, incomplete-group exclusion, leakage rejection, repeated-seed partition tests. Real patient identity remains unverified |
| R7 | Action-specific fixed preference scores; scope reduced to entry paths | Label-distribution and observed-result score tests. No adaptive model-update or sequential-learning claim |
| R8 | Versioned and bounded toy rules include DR severity and separate glaucoma constraints | Exhaustive 180 DR and 36 glaucoma label/path combinations; deterministic references |
| R9 | Selection risk excludes abstention; empty exposure unavailable; failures propagate | Hand-calculated mixed cohorts, all-missing subgroups, complete export reaggregation |
| R10 | Unpruned baseline exactly enumerates all admissible paths | Independent Cartesian-product equality; no eligible calibration needed; shared runner/grid tests |
| R11 | Explicit weight identity, no fallback, content/provenance cache checks | Mocked loading failure, generated-image CPU extraction and repeatability, stale image/seed/cache and training-label checks |

See the [verification record](batch-2-verification.md) for commands, results, and
remaining boundaries. Dataset verification is not implied by passing fixtures.
