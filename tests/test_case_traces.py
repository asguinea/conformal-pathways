from __future__ import annotations

import json
from pathlib import Path

from conformal_pathways.data import Sample
from conformal_pathways.eval.case_traces import export_case_trace
from conformal_pathways.eval.runner import run_synthetic_experiment
from conformal_pathways.workflows import Action, DRWorkflow, Pathway


class _DummyPredictor:
    def uncertainty(self, samples):
        return [0.25 for _ in samples]


def test_export_case_trace_writes_expected_json(tmp_path: Path) -> None:
    workflow = DRWorkflow()
    sample = Sample(
        sample_id="case_0",
        dataset_source="synthetic",
        image_path=None,
        labels={"dr_severity": "moderate", "dme_positive": True, "dme_label_available": True},
        meta={"patient_id": "p0", "eye_id": "left"},
    )
    predictor = _DummyPredictor()
    pi = [
        Pathway(
            actions=[
                Action("order_OCT"),
                Action("refer_retina"),
                Action("followup", {"weeks": 4}),
            ]
        ),
        Pathway(
            actions=[
                Action("order_OCT"),
                Action("anti_VEGF"),
                Action("followup", {"weeks": 12}),
            ]
        ),
    ]
    out_path = tmp_path / "trace.json"

    export_case_trace(
        out_path=str(out_path),
        workflow=workflow,
        sample=sample,
        predictor=predictor,
        alpha=0.1,
        alpha_allocation="uniform",
        stage_thresholds={1: 2.0, 2: 2.0, 3: 2.0},
        selection_policies=["guideline_first", "min_rule_penalty"],
        pi=pi,
        extra_context={"dataset": "synthetic", "variant": "main", "seed": 0},
    )

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert "run" in payload
    assert "sample" in payload
    assert "thresholds" in payload
    assert "paths" in payload
    assert "retained_set" in payload
    assert "selection" in payload
    assert "oracle_policy" in payload
    assert len(payload["paths"]) > 0
    assert all(len(path_entry["actions"]) == 3 for path_entry in payload["paths"])
    assert all(isinstance(path_id, int) for path_id in payload["retained_set"]["retained_path_ids"])


def test_synthetic_runner_case_trace_export_smoke(tmp_path: Path) -> None:
    _ = run_synthetic_experiment(
        workflow_name="dr_workflow",
        n=20,
        seed=0,
        alpha=0.1,
        export_case_traces=",".join(f"dr_{i}" for i in range(20)),
        case_trace_out_dir=str(tmp_path),
        case_trace_subgroup_keys="dr_severity",
    )
    exported = list(tmp_path.glob("*.json"))
    assert exported
