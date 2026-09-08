from __future__ import annotations

from conformal_pathways.conformal.calibration import (
    collect_oracle_scores_by_stage,
    oracle_actions_by_stage,
)
from conformal_pathways.data import Sample
from conformal_pathways.models import TrivialLabelPredictor
from conformal_pathways.scoring import score_action
from conformal_pathways.workflows.core import Action
from conformal_pathways.workflows.dr import DRWorkflow


def _dr_sample(
    sample_id: str,
    dr_severity: str,
    dme_positive: bool,
    dme_label_available: bool,
) -> Sample:
    return Sample(
        sample_id=sample_id,
        dataset_source="synthetic_dr",
        image_path=None,
        labels={
            "dr_severity": dr_severity,
            "dme_positive": dme_positive,
            "dme_label_available": dme_label_available,
        },
        meta={},
    )


def test_collect_oracle_scores_by_stage_shape_and_determinism() -> None:
    samples = [
        _dr_sample("s1", "mild", True, True),
        _dr_sample("s2", "moderate", False, True),
        _dr_sample("s3", "severe", True, True),
        _dr_sample("s4", "mild", False, True),
    ]
    predictor = TrivialLabelPredictor(
        label_key="dr_severity",
        class_values=["mild", "moderate", "severe"],
    )
    predictor.fit([_dr_sample("independent_training", "mild", True, True)])

    workflow = DRWorkflow()
    scores_1 = collect_oracle_scores_by_stage(
        workflow=workflow,
        samples=samples,
        predictor=predictor,
        workflow_name=workflow.name,
    )
    scores_2 = collect_oracle_scores_by_stage(
        workflow=workflow,
        samples=samples,
        predictor=predictor,
        workflow_name=workflow.name,
    )

    assert set(scores_1.keys()) == {1, 2, 3}
    assert all(len(scores_1[stage]) == len(samples) for stage in (1, 2, 3))
    assert scores_1 == scores_2


def test_stage1_oracle_score_not_worse_than_no_oct_for_dme_positive() -> None:
    sample = _dr_sample("s1", "moderate", True, True)
    predictor = TrivialLabelPredictor(
        label_key="dr_severity",
        class_values=["mild", "moderate", "severe"],
    )
    predictor.fit([sample])

    workflow = DRWorkflow()
    sample_meta = {**sample.labels, **sample.meta}
    state = workflow.initial_state(sample_meta)
    oracle_actions = oracle_actions_by_stage(workflow, sample_meta)

    oracle_stage1_score = score_action(
        workflow_name=workflow.name,
        stage=1,
        state=state,
        action=oracle_actions[0],
        action_probability=0.25,
    )
    no_oct_score = score_action(
        workflow_name=workflow.name,
        stage=1,
        state=state,
        action=Action("no_OCT"),
        action_probability=0.75,
    )

    if oracle_actions[0].name == "order_OCT":
        assert oracle_stage1_score <= no_oct_score
