# Result-aware pathways: method and contract

Algorithm `result-aware-pathways-v1`, package 0.4.0.dev0. This implementation
supports decisions that respond to delivered diagnostic results in the two
three-stage toy workflows. It uses fixed split-conformal thresholds and a fixed
entry predictor. It does not retrain the predictor or recalibrate online.

## Information available at each decision

The deployment object, `SequentialSession`, receives a label-free
`PredictionInput`, an entry prediction distribution, and a `StageFilter`. Target
labels, arbitrary sample metadata, and the diagnostic simulator are absent.
Only explicitly declared stage-zero observations initialize the state. Their
provenance and actual availability remain the data provider's responsibility.

At stage 1 the session returns retained diagnostic/skip actions. `choose(action)`
commits one retained action. Choosing the diagnostic puts the session in
`awaiting_result`; further decisions are rejected until `receive(result)` gets
an action-matched, stage-matched `DiagnosticResult`. A positive result, negative
result, and explicit unavailable result are distinct. Skipping never queries
the result provider. Invalid deliveries leave the pending state recoverable;
duplicate, premature, and late deliveries fail. Snapshots and traces are detached
copies. This is an accidental-leakage boundary, not a Python security sandbox.

Stages 2 and 3 compute new action scores from the current observed state.
The original image distribution stays fixed. The existing deterministic
`action_preferences` mapping incorporates the newly delivered observation:
for example, an observed high glaucoma proxy changes the escalation preference
to 1. A negative DME proxy does not imply low DR severity. Missing test results
preserve any prior observed evidence and record unavailability. A later explicit
result replaces the corresponding earlier observation; no evidence-fusion or
measurement-error model is claimed by this deterministic update.

For each action, the score is

```
S_t(a; H_t) = w_u * (1 - preference(a; H_t)) + w_r * observed_rule_penalty(a; H_t)
A_t(H_t) = {admissible a : S_t(a; H_t) <= q_t}
```

Here H_t contains only entry evidence, prior executed actions, and delivered
results. Preferences are heuristics, not probabilities that care is appropriate.
Weights and stage budgets are fixed before calibration. `main`, `model_only`,
and `rules_only` use weights (1,1), (1,0), and (0,1). `no_conformal` uses (1,1)
and infinite thresholds and needs no eligible calibration labels.

The supported selectors are stage-local and deterministic:

| Selector | Ordering of retained actions |
| --- | --- |
| `min_stage_score` | Score, then action name and parameters |
| `observed_rules_first` | Observed rule penalty, intervention/referral burden, distance from 12-week follow-up, score, then action identity |

Their names and definitions differ from the entry-only complete-path selectors.
Selection always uses the fixed (1,1) score, including for tie breaks, across
all four filter variants. Thus these ablations change set construction while
preserving the selector applied to each retained set. Trace records distinguish
the construction `score` from `selection_score`.
Neither selector inspects future potential results or retrospective retained
paths. An empty action set triggers terminal abstention at that stage, retaining
the partial execution trace. A retained action may lead to a downstream empty
set; the implementation does not promise a successful continuation for every
action or result. A complete run consists of exactly three actions.

## Diagnostic simulation and reference calibration

An offline `DiagnosticScenario` specifies one potential diagnostic result per
case, together with a source and observation-mechanism identifier. Calibration
and test scenarios must cover their supplied case IDs exactly and identify one
pre-specified mechanism. The identifier documents the caller's declaration;
matching strings cannot prove identical data-generating processes.

The same potential value is reused across reference traversal, retrospective
branch inspection, and every executed selector for that case. This consistency
assumes the single stage-one diagnostic has a well-defined potential result.
The current workflows do not model repeated tests, treatment-dependent outcomes,
multiple diagnostic stages, or competing test choices. Future extensions to
those settings need an explicit history-dependent observation model.

`proxy_scenarios` is an explicit opt-in simulation of a perfect reveal of a
held-back proxy label. Missing proxy labels yield unavailable results. An IDRiD
DME risk label is not an OCT measurement; a RIM-ONE class label is not a measured
visual-field or RNFL response. Custom scenarios may instead supply noisy or
unavailable outcomes, fixed before calibration and evaluation. Such outcomes
are not automatically inferred, corrected, or resampled by the evaluator.

The privileged, fixed reference action sequence is the existing `oracle_pathway`
under `toy-rules-v2`. It is a target for calibration/evaluation, not a deployable
selector. For each calibration case, traverse this reference, score its action
before each transition, and reveal a diagnostic value only after the reference
orders that diagnostic. Use the same scoring/update code as execution. The
reference remains fixed by the toy truth labels even if the simulated test is
wrong. A wrong result can therefore increase reference scores.

Calibration groups are disjoint from training groups. At each stage use the
maximum reference score across every member of a declared group. Exclude a
group with any missing required truth label and record its identity. Missing
diagnostic results alone do not exclude a truth-evaluable group. Reject an empty
eligible calibration set, except for the unpruned baseline.

For n eligible calibration groups and fixed budget alpha_t, use rank
`ceil((n + 1) * (1 - alpha_t))`. The threshold is the corresponding order
statistic, or positive infinity if the rank exceeds n. Include ties. The existing
decimal rank and conservative budget implementation is reused. Supported
allocations are uniform, front-loaded, and back-loaded, summing to at most alpha.
Calibration-score-dependent allocation and online alpha adaptation are rejected.

## Exact retention statement and its limits

Condition on the independently fitted predictor, score/update/reference rules,
fixed budgets, and pre-specified observation mechanism. Assume the n eligible
calibration groups and one eligible test group are exchangeable **as complete
episodes**, including entry inputs, latent labels, potential diagnostic results,
group sizes, and within-group dependence. Eligibility must define the same
population for calibration and test. Sample IDs alone do not establish these
assumptions or true patient grouping.

Let M_gt be group g's maximum stage-t score on its reference histories, including
results of the tests ordered by those references. Those histories are defined
without using fitted thresholds or the deployed selector. Thus, for each stage,
the n+1 group scores are exchangeable. The corrected rank and inclusive ties give
`Pr(M_test,t > q_t) <= alpha_t`, marginally over calibration and the test group.
No independence between stages or between group members is required. A union
bound gives

```
Pr(all reference trajectories in the test group are retained) >= 1 - sum(alpha_t)
                                                               >= 1 - alpha.
```

To see the trajectory event, consider the implicit tree of retained actions
and possible delivered results. If every score on a case's reference is below
its stage threshold, induction over the stages keeps its reference prefix,
its corresponding result branch, and finally its complete reference. Conversely,
a rejected reference action removes that reference trajectory. The reference is
acceptable under the specified toy predicate, so reference retention implies
existence of at least one toy-acceptable trajectory in the case's realized tree.

This is a **marginal reference-reachability statement at entry**, conditional
only on the independently fixed design and the specified eligible population.
It is not coverage conditional on a particular calibration set, image, subgroup,
observed result, or policy-selected history. It does not bound the violation
rate of an arbitrary selected action sequence or ensure that the reference
remains reachable after the selector has departed from it. Observed-rule
consistency does not imply truth-level acceptability. Tests include a retained
acceptable reference alongside an actually selected violating sequence.

## Offline evaluation and denominators

`evaluate_sequential` validates exhaustive disjoint group splits, preserves
official partitions unless explicit repartitioning is recorded, fits only on
training cases, and predicts each calibration/test entry once. Predictions are
fixed across branches and selectors. The evaluator executes each selector with
the restricted decision context before inspecting retrospective alternatives.

For inspection only, `realized_prediction_set` enumerates complete action
sequences compatible with the case's fixed potential result. It projects the
implicit contingent tree onto one realized scenario. These are not entry-visible
candidates, and the set's size is not the number of contingent policies. Under
infinite thresholds the two supported workflows each have 18 such sequences.

| Metric | Numerator / denominator |
| --- | --- |
| `reference_retained` | Retained references / truth-evaluable cases; empty projections count false |
| `group_reference_retained` | Groups retaining every member's reference / fully truth-evaluable groups |
| `existential_toy_acceptable` | Cases with at least one acceptable realized sequence / truth-evaluable cases; empty projections count false |
| `realized_set_size` | Sum of complete realized sequence counts / all cases |
| `completed`, `abstained` | Completed or abstaining executions / all cases, for each selector |
| `diagnostic_ordered` | Executions ordering the test / all cases |
| `result_unavailable` | Unavailable delivered results / executions ordering the test |
| `chosen_toy_violation` | Violating completed executions / truth-evaluable completed executions |
| `label_unavailable` | Cases missing required truth labels / all cases, including abstentions |

Each record includes its numerator, denominator, unavailable count, and value;
zero denominators yield JSON null. Unavailability counts may overlap across
different metrics. Partially executed abstentions are not scored as complete
paths, safe outcomes, or completed violations. Errors abort evaluation.

Case exports include declared entry observations and distinguish execution traces
from `evaluation_only` fields holding the required truth labels, privileged
reference, potential result, and realized alternatives. The
deployment selector never receives those fields. Every aggregate can be rebuilt
from the cases. Reports include splits, eligible/excluded groups, calibration
scores, thresholds/budgets, fixed entry predictions, source/environment identity,
and input/scenario/prediction/report digests. These are local research records;
do not publish patient identifiers or raw case traces without review.

An input-manifest digest is not a raw-image audit. A reproducible scientific
benchmark still needs a frozen source/input protocol, model specification,
data and image provenance, independent execution, declared comparisons, and
appropriate uncertainty estimates. Those are the next Batch 3 extension.
Generated tests and `sequential-demo` establish implementation behavior only.

## Using the API

```python
from conformal_pathways.sequential import evaluate_sequential, proxy_scenarios

# samples, splits, workflow and predictor are supplied by the caller.
# Choosing this helper explicitly declares a perfect proxy-reveal simulation.
evaluation_cases = [s for s in samples if s.sample_id not in splits["train"]]
scenarios = proxy_scenarios(workflow, evaluation_cases)
report = evaluate_sequential(
    workflow, samples, splits, predictor, scenarios,
    alpha=0.1, allocation="uniform", variant="main",
    model_spec={"description": "caller-supplied fixed model configuration"},
)
```

For real result delivery, construct a `SequentialSession` from a calibrated
filter and the matching fixed predictor, call `decision()` and `choose(action)`,
then supply an explicit `DiagnosticResult` through `receive` when awaiting a
test result. The lower-level API cannot verify that a supplied predictor or
observation mechanism matches calibration; that is a caller obligation. The
integrated evaluator uses one fixed configuration throughout.

The entry-only `conformal.build_prediction_set` and `eval.evaluate_experiment`
remain available under `entry-pathways-v2`. Their preserved numerical evidence
does not measure this new algorithm. See [roadmap](roadmap.md) and
[extension verification](batch-2-sequential-verification.md).
