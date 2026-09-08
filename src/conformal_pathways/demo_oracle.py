from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from conformal_pathways.safety import enumerate_all_pathways, is_safe, oracle_pathway
from conformal_pathways.safety.patterns import (
    DR_UNSAFE_PATTERNS_STRICT,
    GLAUCOMA_UNSAFE_PATTERNS_STRICT,
)
from conformal_pathways.workflows.dr import DRWorkflow
from conformal_pathways.workflows.glaucoma import GlaucomaWorkflow


@dataclass(frozen=True)
class OracleCaseResult:
    workflow_name: str
    sample_meta: dict[str, Any]
    pathway_count: int
    strict_safe_count: int
    oracle_action_names: list[str]
    oracle_followup_weeks: int | None
    oracle_is_safe: bool


def evaluate_oracle_case(workflow, sample_meta: dict[str, Any]) -> OracleCaseResult:
    pathways = enumerate_all_pathways(workflow)

    strict_safe_count = 0
    for pathway in pathways:
        final_state = workflow.rollout(sample_meta, pathway)
        if is_safe(workflow.name, sample_meta, final_state, pathway):
            strict_safe_count += 1

    oracle = oracle_pathway(workflow, sample_meta, safety_mode="strict")
    oracle_final_state = workflow.rollout(sample_meta, oracle)
    oracle_is_safe = is_safe(workflow.name, sample_meta, oracle_final_state, oracle)

    return OracleCaseResult(
        workflow_name=workflow.name,
        sample_meta=sample_meta,
        pathway_count=len(pathways),
        strict_safe_count=strict_safe_count,
        oracle_action_names=oracle.to_names(),
        oracle_followup_weeks=oracle_final_state.get("followup_weeks"),
        oracle_is_safe=oracle_is_safe,
    )


def demo_cases() -> list[tuple[object, dict[str, Any]]]:
    return [
        (
            DRWorkflow(),
            {"dr_severity": "moderate", "dme_positive": True, "dme_label_available": True},
        ),
        (
            DRWorkflow(),
            {"dr_severity": "moderate", "dme_positive": False, "dme_label_available": True},
        ),
        (GlaucomaWorkflow(), {"glaucoma_risk": "high"}),
        (GlaucomaWorkflow(), {"glaucoma_risk": "low"}),
    ]


def run_demo() -> list[OracleCaseResult]:
    print("Illustrative rules only. DR violation patterns:")
    for pattern in DR_UNSAFE_PATTERNS_STRICT:
        print(f"- {pattern}")
    print("")

    print("Glaucoma toy-rule violation patterns:")
    for pattern in GLAUCOMA_UNSAFE_PATTERNS_STRICT:
        print(f"- {pattern}")
    print("")

    results: list[OracleCaseResult] = []
    for workflow, sample_meta in demo_cases():
        result = evaluate_oracle_case(workflow, sample_meta)
        results.append(result)
        print(f"Case: {result.workflow_name} meta={result.sample_meta}")
        print(f"  pathways: {result.pathway_count}")
        print(f"  strict-safe: {result.strict_safe_count}")
        print(
            "  oracle: "
            f"actions={result.oracle_action_names}, "
            f"followup_weeks={result.oracle_followup_weeks}"
        )
        print(f"  oracle_is_safe: {result.oracle_is_safe}")
        print("")

    return results


if __name__ == "__main__":
    run_demo()
