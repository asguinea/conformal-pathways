from __future__ import annotations

from conformal_pathways.data import Sample
from conformal_pathways.models import TrivialLabelPredictor


def _sample(sample_id: str, dr_severity: str) -> Sample:
    return Sample(
        sample_id=sample_id,
        dataset_source="synthetic",
        image_path=None,
        labels={"dr_severity": dr_severity},
        meta={},
    )


def test_trivial_predict_proba_sums_to_one() -> None:
    train_samples = [
        _sample("s1", "mild"),
        _sample("s2", "mild"),
        _sample("s3", "moderate"),
    ]
    predictor = TrivialLabelPredictor(
        label_key="dr_severity",
        class_values=["mild", "moderate", "severe"],
    )
    predictor.fit(train_samples)

    probs = predictor.predict_proba([_sample("t1", "mild"), _sample("t2", "severe")])

    assert len(probs) == 2
    for dist in probs:
        assert set(dist.keys()) == {"mild", "moderate", "severe"}
        assert abs(sum(dist.values()) - 1.0) < 1e-12


def test_trivial_uncertainty_matches_one_minus_max_prob() -> None:
    train_samples = [
        _sample("s1", "mild"),
        _sample("s2", "mild"),
        _sample("s3", "moderate"),
    ]
    predictor = TrivialLabelPredictor(
        label_key="dr_severity",
        class_values=["mild", "moderate", "severe"],
    )
    predictor.fit(train_samples)

    query_samples = [_sample("t1", "mild"), _sample("t2", "severe")]
    probs = predictor.predict_proba(query_samples)
    uncertainties = predictor.uncertainty(query_samples)

    expected = [1.0 - max(dist.values()) for dist in probs]
    assert uncertainties == expected


def test_trivial_predictions_are_deterministic() -> None:
    train_samples = [
        _sample("s1", "mild"),
        _sample("s2", "mild"),
        _sample("s3", "moderate"),
        _sample("s4", "moderate"),
    ]
    predictor = TrivialLabelPredictor(
        label_key="dr_severity",
        class_values=["mild", "moderate", "severe"],
    )
    predictor.fit(train_samples)

    query_samples = [_sample("t1", "mild"), _sample("t2", "severe")]
    probs1 = predictor.predict_proba(query_samples)
    probs2 = predictor.predict_proba(query_samples)
    unc1 = predictor.uncertainty(query_samples)
    unc2 = predictor.uncertainty(query_samples)

    assert probs1 == probs2
    assert unc1 == unc2
