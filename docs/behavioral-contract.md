# Behavioral contract

Version 0.1, established in Batch 1. **This specifies the target behavior for
Batch 2; the migrated implementation does not yet satisfy it.** The final table
records the known gaps. No guarantee follows from documenting this contract.

## Records and information available to a decision

The present `Sample` record contains `sample_id`, `dataset_source`, `image_path`,
`labels`, and `meta`. That container is convenient for offline experiments but
does not enforce an information boundary. The corrected APIs must separate:

| Role | Allowed information | Restrictions |
| --- | --- | --- |
| Predictor during fitting | Training inputs and training targets | No calibration or test fitting, including preprocessing choices |
| Predictor at inference | Declared inputs available at that time | No held-out targets or undeclared label-derived metadata |
| Workflow state | Initial observations, performed actions, returned observations | Each observation has an availability time and provenance |
| Action scorer and selector | The current observed state, frozen model, fixed calibration output | No latent record, retrospective outcome, or privileged reference policy |
| Observation environment | Latent values needed to simulate a completed diagnostic action | Only the result of an actually performed action may be returned |
| Offline evaluator/reference policy | Held-out labels required by its explicit predicate | Privileged information is confined to evaluation |

Initial DR severity or glaucoma status is an observation only in a benchmark
that explicitly declares it available at entry. Otherwise it must be a model
output or remain unknown. Renaming a target to metadata does not make it observed.

A retrospective photograph grade is not an OCT result. If a label is used to
simulate a diagnostic result, the experiment must identify that proxy and its
assumptions; it must not present the result as an observed clinical measurement.

## Identity, missingness, and splitting

1. Sample IDs must be nonempty and unique within a source; joins must use the
   source plus sample ID or an explicitly unique global ID. Reject duplicate
   records and mismatched embedding IDs instead of overwriting or skipping them.
2. Use verified patient/group identifiers to keep related records together.
   Namespace local identifiers by source unless a documented cross-source
   identity map establishes the same patient. An image filename does not prove
   that two records are independent patients.
3. Record a dataset's official partition and its provenance. Repartitioning an
   official test set requires a declared alternative protocol; never silently
   reinterpret it as training data. Validate split disjointness and completeness.
4. Labels have present, missing, or invalid status. Normalize valid Boolean
   encodings explicitly; reject invalid values. Missing DME labels are not
   negative DME labels, and label availability is not observation availability.
5. Persist split membership and its configuration. All fitting and model-choice
   decisions precede the locked calibration and held-out evaluation stages.

## State transitions and selection

- The initial state contains only declared entry observations.
- A diagnostic action reveals its result only when executed and when that
  result is available. A skipped diagnostic action leaves the value unknown.
  An unavailable result remains unknown with an explicit reason.
- A selection policy must be a function of observed history. Two records with
  identical observed history and different hidden labels must produce the same
  decision before either label is revealed. This test applies to indirect leaks
  through candidate sets, scores, and ranking, not only direct label reads.
- Branch-dependent future decisions must be represented as contingent behavior
  or made after new observations arrive. Evaluating hypothetical branches with
  a latent label must not reveal the unperformed test result to today's selector.
- Tie-breaking must be deterministic and documented. An empty candidate set
  produces explicit abstention; a selection exception is an error, not an
  ordinary empty-set outcome.
- Full-information reference pathways are evaluation targets, not deployable
  policies. Both their tie-breaking rule and the rule predicate are versioned.

## Calibration and candidate sets

The target algorithm must define its calibration event, independent sampling
unit, score, stage indexing, and retained-set semantics before claiming coverage.
For a fixed split-conformal score and stage error budget `alpha_t`, let `n` be
the number of exchangeable calibration units and let
`k = ceil((n + 1) * (1 - alpha_t))`. Use the `k`-th smallest score when `k <= n`;
use positive infinity when `k = n + 1`. Do not cap that rank at `n`. Reject an
empty calibration set and invalid/nonfinite scores or error budgets explicitly.
Acceptance uses `score <= threshold`, including ties.

Stage budgets must be nonnegative and sum to at most the declared total alpha.
Any zero-budget stage uses an unbounded threshold. Budgets and score parameters
must be fixed before using the calibration scores for quantiles, or be supported
by a separately justified method for adaptive calibration. In particular,
estimating score variances and thresholds on the same calibration data does not
automatically inherit a fixed-budget guarantee.

Keeping patients out of different splits does not make multiple images from
one calibration patient independent units. A group-level calibration construction
or a documented sampling protocol is required for a group-level statement.

The scorer must have an explicit interpretation for candidate actions. Specify
how new observations change it. A single uncertainty value copied to every
action is not evidence of an action-specific probability or sequential learning.

An unpruned baseline enumerates every admissible complete pathway using the same
workflow and input protocol. Its score thresholds are unbounded; the largest
observed calibration score is not an unpruned baseline. Comparisons share split
IDs, fitted models, data eligibility, and metric implementations.

## Metric definitions for the corrected evaluation

Let `P_i` be the candidate set for case `i`, `a_i` the selected path (or
abstention), `r_i` the deterministic reference path, and `V_i(p)` an explicitly
defined rule violation predicate. Eligibility is determined by the labels
required for that predicate, before aggregating results. Missing labels yield
unavailable metrics with a reason; they never imply a successful outcome.

| Quantity | Intended definition and denominator |
| --- | --- |
| Reference-path inclusion | Fraction with `r_i in P_i` among cases with an evaluable reference; this event must match any formal coverage claim |
| Existence of a rule-acceptable path | Fraction with at least one `p in P_i` satisfying `V_i(p) = false`, among rule-evaluable cases; empty sets count as false |
| Any violating candidate | Fraction with at least one violating path among rule-evaluable nonempty sets; report empty-set frequency separately |
| Within-set violation fraction | Per-case violating-path count divided by set size, averaged over rule-evaluable nonempty sets; label this macro average |
| Selected-path violation rate | Violating selections divided by the number of rule-evaluable non-abstaining selections |
| Abstention rate | Number of explicit abstentions divided by all evaluated cases; selection failures are reported separately |
| Mean set size / empty-set rate | All evaluated cases, independent of label availability |
| Top-k metrics | State whether all or any returned paths must satisfy the rule, and report how sets smaller than k are handled |

Every rate export includes numerator, denominator, missing/unevaluable count,
and applicable abstention/error counts. A zero denominator yields unavailable,
not zero. Label-conditioned quantities must be accompanied by label-availability
rates per dataset and subgroup. Uncertainty intervals use the independent
sampling unit; repeated random splits are not independent patients.

These are rule-based surrogate outcomes. Neither reference-path inclusion nor
rule satisfaction measures a treatment benefit or the probability of patient harm.

## Known implementation gaps to close in Batch 2

| ID | Current behavior / issue | Code area | Required evidence |
| --- | --- | --- | --- |
| R1 | CSV loading does not reliably carry the availability signal used by diagnostic revelation | `data/loaders.py`, `workflows/dr.py` | CSV-to-state tests for positive, negative, missing, and invalid labels |
| R2 | Selection merges retrospective labels into policy inputs; initial states and branch construction also need an information-boundary audit | `eval/selection_policies.py`, `conformal/sequential.py`, `workflows/` | Hidden-label perturbation tests before and after diagnostic actions, including indirect candidate-set leaks |
| R3 | Missing DME can be treated as making every pathway acceptable | `safety/oracle.py`, `eval/metrics.py` | Missing-label cases produce unavailable outcomes and correct denominators |
| R4 | The finite-sample quantile rank is capped at the number of scores | `conformal/thresholds.py` | Independent order-statistic examples, tiny calibration sets, ties, and invalid inputs |
| R5 | Variance-based budget allocation uses the same calibration scores | `conformal/thresholds.py` | Fixed allocation or a separately justified and tested adaptation protocol |
| R6 | Group splitting exists, but calibration scores and metrics operate on image records; identifiers and official partitions need stronger validation | `data/splits.py`, `ingest/`, `conformal/calibration.py` | Verified group protocol, duplicate-ID rejection, partition preservation, and group-level sampling tests |
| R7 | Action scores reuse a scalar uncertainty; its direction can shrink sets as uncertainty increases; diagnostic actions do not trigger a new model prediction | `scoring/nonconformity.py`, `conformal/sequential.py` | Explicit score semantics and tests of decisions as observations change |
| R8 | DR severity does not affect the strict predicate; the glaucoma predicate covers a narrow conjunction of actions | `safety/oracle.py`, `safety/patterns.py` | Versioned toy-rule truth tables, exhaustive path checks, and clearly bounded claims |
| R9 | Selected-path risk includes abstentions; empty sets have exposure 1; errors may be absorbed as abstention | `eval/metrics.py` | Hand-calculated mixed cohorts and distinct denominators for risk, abstention, and missingness |
| R10 | The no-conformal baseline uses a finite calibration maximum | `eval/baselines.py`, `eval/grid_runner.py` | Exact equality to independent full enumeration across all cases |
| R11 | Pretrained-weight loading can fall back to random weights; caches lack complete provenance | `features/extract_embeddings.py` | Fail on unavailable requested weights; explicit separately named random baseline; weight, preprocessing, input, and cache identity checks |

The existing tests intentionally remain a migration baseline in Batch 1.
Any test that asserts an incorrect behavior must be replaced by a test of the
contract, rather than used to defend the inherited behavior.
