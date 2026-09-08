# Method: entry-observation path sets

Algorithm version: `entry-pathways-v2`. Rule version: `toy-rules-v2`.

## Information and target

Each case has entry observations, retrospective target labels, and grouping
metadata. Inference receives a `PredictionInput` with identity, image path, and
only stage-zero observations; it has no labels or arbitrary metadata. Loading
an observation requires an explicit mapping from a separate manifest column.
The caller must substantiate that the observation was actually available on
entry. A declared source string alone does not establish this fact.

A candidate is a complete, open-loop action sequence. Both workflows have
2 diagnostic choices, 3 management choices, and 3 follow-up choices: 18 paths.
The projected state records actions but receives no hypothetical diagnostic
results. Separately, an executed diagnostic can accept a `DiagnosticResult`
with action, source, stage, and value. These transitions do not constitute an
adaptive evaluation protocol or inherit the coverage statement below.

The target is the deterministic, full-information reference path in
[toy-rules](toy-rules.md). Its labels are used only for training, calibration
of reference scores, and retrospective evaluation. It is not a deployable policy.

## Fixed scoring and calibration

The built-in predictors fit only on the training split. The class-prior demo
returns training frequencies; the optional image model fits logistic regression
on frozen ResNet-50 embeddings. Model fitting, score weights, and budget choice
must precede calibration. The supported protocol has no calibration-based
hyperparameter tuning, source stratification by default, or adaptive budgets.

For each stage and action, `score = w_model * (1 - preference) + w_rule * penalty`.
The preferences are fixed heuristics, not probabilities of appropriate care:

| Stage | Preference distribution |
| --- | --- |
| Diagnostic | Order: p; skip: 1 − p |
| Management | Refer: p; monitor: 1 − p; intervene: 0 |
| Follow-up | 4 weeks: p; 12 weeks: 1 − p; 24 weeks: 0 |

For DR, p is the model's total probability of grade 3/4 or `severe`; an observed
severity overrides it, and observed DME-positive status sets p to 1. For glaucoma,
p is the high-risk model probability, overridden by observed low/high risk.
The penalty is 1 for a rule violation detectable in the observed state and 0
otherwise. Additionally, skipping OCT while DME status is unknown incurs 1;
this is a stated conservative heuristic. Missing outcomes are never revealed by
this penalty. Zero preference does not prove an action is inappropriate.

For each fully rule-evaluable calibration group, take the maximum reference-path
score over its members, separately for every stage. Exclude an entire group if
any member lacks a required rule label; report the group counts. An empty
eligible calibration cohort is an error. Group IDs cannot overlap training.

Stage budgets are uniform, front-loaded (0.6, 0.3, 0.1), or back-loaded
(0.2, 0.3, 0.5) multiples of alpha, fixed independently of calibration scores.
Floating-point allocations are rounded conservatively so their decimal values
sum to at most alpha. With n eligible groups, use rank
`ceil((n + 1) * (1 - alpha_t))`, including an infinite threshold when rank exceeds
n. Zero budgets also yield infinity. Keep a path exactly when every stage score
is at most its threshold; ties are retained. No truncation is applied.

## Conditional coverage argument

Assume that, conditional on the fitted training procedure and the number n of
eligible calibration groups, those groups and one new eligible group are
exchangeable. Apply the same fixed reference rule and scoring function to each
group. Eligibility must use the same complete-label rule in calibration and in
the population to which the claim refers.

At stage t, the n calibration group maxima and the new group's maximum are
exchangeable. The corrected order statistic gives probability at most alpha_t
that the new maximum exceeds its threshold (ties are conservative; an infinite
threshold cannot be exceeded). By the union bound, the probability of any stage
failure is at most the sum of the budgets, hence at most alpha. When no stage
fails, every member's reference path satisfies every threshold and is retained.
No independence between stages or between images within a group is needed.

This is a marginal statement for one new eligible group, conditional on the
training procedure; it is not conditional coverage for each patient or subgroup,
nor simultaneous coverage of an entire test cohort. A sample-weighted inclusion
rate has a different estimand. `group_oracle_retained` measures the matching
all-members event; partially labelled groups have unavailable outcomes.

This construction applies the standard split-conformal rank argument; general
background is given by [Angelopoulos and Bates](https://arxiv.org/abs/2107.07511v6).
The group maximum and union-bound reasoning above specify this implementation.
Tests check construction and arithmetic, not the empirical truth of assumptions.
Official partitions, unverified patient IDs, curated datasets, distribution
shift, tuning after test inspection, and missing-label selection can invalidate
a proposed application. Outputs explicitly record that dataset assumptions
have not been verified. There is no selected-path, clinical, or adaptive guarantee.

## Comparisons, selection, and provenance

`main`, `model_only`, and `rules_only` use score weights (1,1), (1,0), and (0,1).
The `no_conformal` baseline returns exactly all 18 paths and bypasses calibration.
All runners share split validation, fitting, metrics, and export code. Selection
policies remain fixed across these set-construction ablations. In particular,
`min_total_score` uses the (1,1) score; `min_rule_penalty` uses it to break penalty
ties. `observed_rules_first` breaks penalty ties by management burden, distance
from a 12-week interval, then lexicographic action/parameter strings. Empty sets
produce explicit abstention. Errors terminate the run.

Outputs include split membership, eligible group IDs/counts, thresholds, budgets,
score weights, input fingerprints, configuration identifiers, and every metric's
numerator, denominator, and unavailable count. Per-case exports carry declared
group IDs; traces separate entry observations from evaluation-only labels.
These identities prevent accidental configuration collisions; they are not a
substitute for Batch 3's frozen configuration and code-revision record.

Image caches additionally record ordered image-content hashes, IDs, architecture,
explicit weights and seed, model-state hash, preprocessing, device, batch size,
workers, library versions, and embedding/ID-file hashes. Reuse validates the
request and artifact integrity. The pretrained request is `IMAGENET1K_V2` with
its [Torchvision preprocessing](https://docs.pytorch.org/vision/stable/models/generated/torchvision.models.resnet50.html).
Weight loading must succeed; moving `DEFAULT` and silent random fallback are
unsupported. An explicitly seeded random backbone is a separate experiment.
Fresh pretrained and accelerator runs remain to be verified in Batch 3.
