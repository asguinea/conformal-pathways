# Illustrative rule specification

Version: `toy-rules-v2`. These predicates are deliberately small software test
models. Action names and intervals do not express medical advice or a validated
standard of care. No treatment outcomes or actual diagnostic response sequences
are observed in the benchmark.

## DR workflow

Required labels: `dr_severity` (integer 0–4, or mild/moderate/severe) and Boolean
`dme_positive`. Severe means grade 3/4 or the string `severe`.

A complete path is acceptable exactly when all applicable constraints hold:

- DME-positive requires `order_OCT`.
- DME-positive or severe disease prohibits `monitor` and a 24-week follow-up.
- DME-negative prohibits `anti_VEGF`.

| Privileged labels | Acceptable paths of 18 | Deterministic reference |
| --- | --- | --- |
| DME-negative, not severe | 12 | no_OCT → monitor → 12 weeks |
| DME-negative, severe | 4 | no_OCT → refer_retina → 4 weeks |
| DME-positive, any severity | 4 | order_OCT → refer_retina → 4 weeks |

The stage-2 action space is `refer_retina`, `anti_VEGF`, `monitor`. Follow-up
choices are 4, 12, and 24 weeks. Acceptable does not mean optimal: several paths
may satisfy the same predicate, while exactly one is the reference target.

## Glaucoma workflow

Required label: `glaucoma_risk`, low or high. High risk requires
`order_extra_tests`, prohibits `monitor`, and prohibits 24-week follow-up. These
are three separate requirements. Low risk prohibits `treat`.

| Privileged label | Acceptable paths of 18 | Deterministic reference |
| --- | --- | --- |
| Low | 12 | no_extra_tests → monitor → 12 weeks |
| High | 4 | order_extra_tests → refer_glaucoma → 4 weeks |

The other management choice is `treat`; follow-up choices are 4, 12, and 24 weeks.
A missing required label yields an unavailable predicate and reference, not a
successful outcome. Invalid labels or incomplete/nonadmissible paths raise errors.
The checker derives the outcome from the actions and ignores a supplied stale
final state. Exhaustive fixtures check every path for all five DR grades with
both DME values, and both glaucoma labels.

## Adapter semantics and limitations

Adapters validate labels before conversion. They never truncate fractional
grades. IDRiD's configured mapping sets the DME proxy positive for risk grades
1 or 2; grade 0 is negative. Messidor-2's configured mapping requires a binary
adjudicated DME field. These mappings are explicit benchmark assumptions, not
equivalence to an observed OCT result. Missing labels remain missing in loaded
manifests. Do not run a clinical interpretation through either mapping.

Known provider split hints are preserved; carving calibration from training
leaves official test membership fixed. Missing/conflicting hints fail. A caller
may explicitly request repartitioning, which is recorded as a different protocol.
Patient identity is not inferred from a unique image name. The EyePACS filename
pairing convention is marked unverified; other adapters without actual patient
IDs fall back to image-level groups and state that identity is unverified. A
patient-level coverage claim requires separately verified patient linkage.

Full dataset-version, source-format, grouping, partition, eligibility, and rights
verification remains part of Batch 3. No real dataset was used to establish the
truth tables or software tests in Batch 2.
