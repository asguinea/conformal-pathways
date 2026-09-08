from conformal_pathways.safety import enumerate_all_pathways, is_safe, oracle_pathway
from conformal_pathways.workflows.dr import DRWorkflow
from conformal_pathways.workflows.glaucoma import GlaucomaWorkflow


def test_enumerate_all_pathways_dr_count() -> None:
    paths = enumerate_all_pathways(DRWorkflow())

    assert len(paths) == 18


def test_enumerate_all_pathways_glaucoma_count() -> None:
    paths = enumerate_all_pathways(GlaucomaWorkflow())

    assert len(paths) == 18


def test_oracle_pathway_returns_strict_safe_pathway() -> None:
    wf = DRWorkflow()
    sample_meta = {
        "dr_severity": "moderate",
        "dme_label_available": True,
        "dme_positive": True,
    }

    pathway = oracle_pathway(wf, sample_meta, safety_mode="strict")
    final_state = wf.rollout(sample_meta, pathway)

    assert is_safe(wf.name, sample_meta, final_state, pathway) is True


def test_oracle_pathway_is_deterministic() -> None:
    wf = DRWorkflow()
    sample_meta = {
        "dr_severity": "moderate",
        "dme_label_available": True,
        "dme_positive": True,
    }

    p1 = oracle_pathway(wf, sample_meta, safety_mode="strict")
    p2 = oracle_pathway(wf, sample_meta, safety_mode="strict")

    assert p1.to_names() == p2.to_names()
