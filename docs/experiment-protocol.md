# Experiment protocol: batch3-v1

This is a local, prospective specification for `entry-pathways-v2` and
`toy-rules-v2`. Freeze the implementation and this document **before running or
inspecting the designated experiments**. Generated unit-test fixtures and input
inventory checks are preparation, not benchmark outcomes. The machine-readable
[configuration](../experiments/batch3-v1.json) is authoritative for numeric
settings. Both workflows enumerate 18 complete, open-loop paths.

## Questions and comparisons

Measure reference-path inclusion, retained-set size, toy-rule exposure, and
selection/abstention behavior. Check whether implementation behavior agrees with
[the conditional coverage argument](method.md) under an explicit synthetic
sampling mechanism. Evaluate all four variants: `main`, `model_only`,
`rules_only`, and the unpruned `no_conformal` control. A common fitted model,
training/calibration/test membership, and cached entry predictions are reused
within each paired comparison. Weights, scoring, and selectors follow the
method document. Neither calibration labels nor benchmark results choose a
hyperparameter, selector, model, seed, or reporting subset.

The primary setting is total alpha 0.1. Uniform stage budgets apply to the three
filtered variants; the unpruned control has no alpha and is run only once per
trial/model. Both `observed_rules_first` and `min_total_score` are evaluated on
every setting. Primary contrasts are `main - model_only`, `main - rules_only`,
and `main - no_conformal`. A smaller set or observed violation rate alone does
not establish superiority, particularly if inclusion or abstention changes.

## Independent synthetic repetitions

Each repetition redraws training, calibration, and **one new test group**.
Each group has two images with a shared latent label and independent noisy
entry measurements. Groups are disjoint and their membership is known from
the generator. One test group per repetition makes the all-members reference
inclusion indicator a Bernoulli outcome across independent repetitions. Two
images from that group are never counted as two independent patients.

| Scenario | Repetitions per workflow | Train / calibration / test groups | Models | Total alpha |
| --- | --- | --- | --- | --- |
| IID | 128 | 50 / 99 / 1 | Class prior; known signal | 0.05, 0.1, 0.2 |
| Missing labels | 64 | 50 / 99 / 1 | Known signal | 0.1 |
| Tiny calibration | 16 | 50 / 9 / 1 | Known signal | 0.1 |

The two workflows yield 416 independently generated trials and 5,760
comparison records (5,120 IID; 512 missing-label; 128 tiny-calibration).
The seed is `2026090800 + scenario_index * 1000000 + workflow_index * 100000
+ repetition_index`, with zero-based indices in configuration order.

DR grades have probabilities `[.30, .15, .25, .15, .15]`. Conditional entry
measurements are Gaussian with means `[-2, -1, 0, 1, 2]` and standard deviation
0.8. Conditional DME-positive probabilities are `[.03, .10, .30, .60, .80]`.
Glaucoma high status has probability .35, with Gaussian means -1/1 and standard
deviation 1. These are invented mechanisms, not epidemiological estimates.
The known-signal predictor evaluates the exact Bayes posterior for the specified
entry measurement; it knows generator parameters and is not a trained clinical
model. The class-prior control learns only training-label frequencies.

In the missing-label scenario, each image independently loses the required DME
label (DR) or glaucoma label with probability .2, independently of disease and
signal. Partly labelled calibration groups are excluded as complete groups.
Group inclusion is unavailable for partly labelled test groups. Case-based rule
metrics use their documented case eligibility; they do not silently inherit a
complete-group estimand. Unavailability and excluded calibration counts are
retained. This checks this specified missing-at-random mechanism only.

With nine calibration groups and three uniform budgets at total alpha .1, the
corrected rank exceeds the number of groups at every stage. Infinite thresholds
and all 18 retained paths are the prespecified tiny-calibration behavior.

## Real-data descriptive extension

Use IDRiD disease grading and RIM-ONE DL's provider random partition, subject to
[the input audit](dataset-evidence.md). The planned grid has 80 records:
two datasets × five split seeds × two models × four variants at alpha .1.
Seeds are 101, 202, 303, 404, 505. IDRiD has 413 provider training and 103 test
images; RIM-ONE has 339 training and 146 test images. Keep official test membership
fixed. Carve calibration exclusively from provider training data using
`floor(n_train * .6 / (.6 + .2))` training images and the remainder for calibration
(309/104 for IDRiD and 254/85 for RIM-ONE). Do not stratify, tune, or repartition
the provider test set.

Models are a training-only class prior and frozen ResNet-50 `IMAGENET1K_V2`
features followed by logistic regression (`C=1`, `lbfgs`, `max_iter=1000`,
`random_state=0`, no feature scaling or hyperparameter search). Convergence
warnings fail the run. The checkpoint SHA-256 is recorded in configuration.
Use the [weight-specific preprocessing](https://docs.pytorch.org/vision/stable/models/generated/torchvision.models.resnet50.html),
CPU, two torch intra-op threads, deterministic algorithms, batch size 16, and
zero data-loader workers. The CLI fixes BLAS thread environment variables at 1;
actual torch inter-op threads and library versions are recorded with features.

Real images supply model input; no retrospective target is declared an entry
observation. IDRiD's positive macular-edema risk grade is a retrospective proxy,
not an OCT finding. RIM-ONE disease classes map to toy low/high status, not a
longitudinal risk prediction. Confirmed patient linkage is unavailable, so use
explicit sample-ID fallback groups and report image-level descriptive results.
Do not claim patient-level coverage or compare these surrogate metrics with a
provider's classification leaderboard.

The input seal is deliberately separate from the source freeze. After files
are fully local, `audit-data` verifies annotation hashes and partition counts,
rejects duplicate image bytes, records the ordered image-content identity, and
writes `experiments/batch3-inputs-v1.json`. Commit that seal **before any real
model fitting**. Every real run verifies it. This allows synthetic experiments
to proceed while external images are unavailable without changing this protocol.
No data-dependent model choice is permitted during the audit.

## Estimands and uncertainty

All records retain metric numerators, denominators, and unavailable counts.
The promoted metrics are group reference inclusion, mean paths, empty-set rate,
mean fraction of violating retained paths (`unsafe_exposure`), and selected-path
violation and abstention rates for each selector. A selected-path violation rate
is conditional on evaluable, nonempty selections. Exposure is conditional on
an evaluable nonempty set. Undefined rates remain null, including when all cases
abstain; they are never converted to zero.

For synthetic data, summarize the **mean of repetition metrics**, not a pooled
case rate. Compute approximate 95% Wilson intervals for the Bernoulli
all-members reference inclusion event; the implementation is checked against
[the NIST worked example](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm).
For other bounded means use the two-sided Hoeffding radius
`(upper - lower) * sqrt(log(2 / (1 - confidence)) / (2 * n))`, clipped to metric
bounds (0–1 or 0–18). This follows
[Hoeffding's bounded independent-sum inequality](https://doi.org/10.1080/01621459.1963.10500830).
Constant observed outcomes still have nonzero uncertainty. Approximate Wilson
coverage and conservative Hoeffding bounds are not interchangeable guarantees.

Paired differences use the same repetition IDs, verified input identities, and
fitted-model identities. Only jointly evaluable repetitions enter a difference;
report their number and unavailable pairs. Difference bounds are -1–1 or -18–18.
With random eligibility these intervals target the conditional distribution of
evaluable repetitions, not missing outcomes. Intervals are pointwise across the
large comparison grid; there is no multiplicity-adjusted superiority claim.

Real runs share the same test images across five seeds. Report their mean and
observed minimum/maximum only. These seed ranges are sensitivity descriptions,
not confidence intervals or five independent patient cohorts. Results cannot
establish treatment benefit, clinical safety, or validity under distribution
shift. Reference inclusion is distinct from safety of a selected pathway.

## Freezing, running, and reproduction

From a checkout with Python 3.12 and uv installed:

```sh
uv sync --locked --extra plots
# Maintainer preparation only, after committing source/configuration/protocol:
uv run --locked python -m conformal_pathways.benchmarks freeze --config experiments/batch3-v1.json
# Commit the generated .lock.json before designated runs.

uv run --locked python -m conformal_pathways.benchmarks run --config experiments/batch3-v1.json --suite synthetic --out artifacts/batch3/primary/synthetic
uv run --locked python -m conformal_pathways.benchmarks run --config experiments/batch3-v1.json --suite synthetic --out artifacts/batch3/repeat/synthetic
uv run --locked python -m conformal_pathways.benchmarks compare artifacts/batch3/primary/synthetic artifacts/batch3/repeat/synthetic
uv run --locked --extra plots python -m conformal_pathways.benchmarks publish-local --runs artifacts/batch3/primary/synthetic --allow-pending-real --out artifacts/batch3/report
uv run --locked python -m conformal_pathways.benchmarks verify-evidence artifacts/batch3/report
```

Consumers use the committed lock; they do not freeze a replacement. Verification
hashes configuration, package source, dependency lock, project metadata, and this
document. It also checks the imported package against that source when executing
an installed wheel. Run directories must be new/empty; failed attempts are
preserved with an execution status. No results are silently skipped or resumed.

Repeat the complete synthetic suite from a clean checkout and a separately
installed wheel using hashed dependencies from `uv export --locked --no-dev
--no-emit-project`. Run from outside the checkout with the clean configuration's
absolute path. No imaging or model packages are needed for synthetic execution.
Compare every metric, split, per-case outcome, and candidate/selected-path hash
exactly; probability and threshold absolute tolerances are 1e-10. For real-data
reproduction, independently re-extract features and require `atol=rtol=1e-6` as
well as exact downstream cases/metrics. Record exactness separately from passing
a tolerance. Use the same sealed input files. A mismatch is a failed reproduction,
not permission to adjust tolerances after inspecting results.

Each local raw bundle preserves inputs and split membership, model provenance
and predictions, case CSVs, full run JSONs, checksums, environment, timestamps,
elapsed time, and failures. Local raw real-data records are not redistributed.
The public evidence package contains compact trial summaries, regenerable
summary/paired tables, plots, and a manifest. A synthetic-only package must
explicitly declare the real suite pending. `publish-local` only writes files;
it performs no upload. Any post-outcome scientific change requires a named new
protocol/amendment with prior attempts retained and disclosed.
