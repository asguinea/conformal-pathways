# Claim register

Status at version 0.1.0.dev0. An intended capability is not a verified claim.

| ID | Statement | Status | Evidence / next requirement |
| --- | --- | --- | --- |
| C1 | The project installs independently and runs a generated-data example | Batch 1 verification | [Installation and test record](batch-1-verification.md); scope limited to the recorded environment |
| C2 | The source supplies two small three-stage decision workflows and an experimental evaluation harness | Implemented | `workflows/`, `eval/`, migrated smoke tests; no claim about clinical correctness |
| C3 | Decisions use only information available at decision time | Not established; known violations | Contract R1–R2; direct and indirect leakage regression tests required |
| C4 | Candidate sets have a stated finite-sample coverage guarantee | Not established | Define the precise event and assumptions; resolve R4–R7; mathematical argument plus independent implementation checks |
| C5 | Reported metrics faithfully implement the declared toy rules and denominators | Not established; known violations | R3, R8–R9; exhaustive truth tables and hand-computed metric fixtures |
| C6 | A selected path is clinically safe or improves patient outcomes | Unsupported and outside current scope | These datasets and toy rules do not establish this claim |
| C7 | The method outperforms baselines or reproduces a quantitative benchmark | Not established | Correct implementations, frozen protocol, fresh runs, paired comparisons, and uncertainty estimates in Batch 3 |
| C8 | Image-model experiments are reproducible from identified inputs and weights | Not established | R6 and R11; exact dataset, transform, weight, split, environment, and cache provenance |
| C9 | The project is cleared for public redistribution | Pending | Confirm ownership, license, attribution, and final distributed-asset review |

The package name describes the research area. It does not certify that a formal
conformal guarantee currently applies. Terms such as `safe` and
`guideline_first` in the experimental API name particular predicates or policies;
they do not supply independent evidence for those predicates or policies.

## Evidence required for future results

Each promoted quantitative claim must link to a versioned configuration, code
revision, dataset and model provenance, split IDs, raw per-case records with
appropriate distribution rights, an aggregation command, and its regenerated
table or figure. Record failures, exclusions, uncertainty intervals, compute
requirements, and limitations. Select the protocol before examining test results.

A theorem must identify its target event and assumptions. Empirical event
frequencies test implementation and behavior in a stated experiment; they do not
prove distribution-free validity. Rule compliance and clinical outcomes remain
separate even if a coverage result is established.
