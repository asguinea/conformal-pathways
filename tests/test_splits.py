from __future__ import annotations

from collections import Counter

from conformal_pathways.data import Sample
from conformal_pathways.data.splits import _check_no_group_leakage, make_splits


def _synthetic_samples() -> list[Sample]:
    samples: list[Sample] = []

    # dataset_a: 10 patient groups, each with 2 samples (20 samples total)
    for group_idx in range(10):
        for eye_idx in range(2):
            sample_id = f"a_g{group_idx}_s{eye_idx}"
            samples.append(
                Sample(
                    sample_id=sample_id,
                    dataset_source="dataset_a",
                    image_path=None,
                    labels={},
                    meta={"patient_id": f"a_patient_{group_idx}"},
                )
            )

    # dataset_b: 5 patient groups, each with 2 samples (10 samples total)
    for group_idx in range(5):
        for eye_idx in range(2):
            sample_id = f"b_g{group_idx}_s{eye_idx}"
            samples.append(
                Sample(
                    sample_id=sample_id,
                    dataset_source="dataset_b",
                    image_path=None,
                    labels={},
                    meta={"patient_id": f"b_patient_{group_idx}"},
                )
            )

    return samples


def test_make_splits_no_group_leakage_and_total_count_preserved() -> None:
    samples = _synthetic_samples()

    splits = make_splits(samples=samples, seed=13, stratify_by_source=True)

    assert _check_no_group_leakage(samples, splits) is True

    total = len(splits["train"]) + len(splits["cal"]) + len(splits["test"])
    assert total == len(samples)

    all_ids = splits["train"] + splits["cal"] + splits["test"]
    assert len(set(all_ids)) == len(samples)


def test_make_splits_is_deterministic_for_same_seed() -> None:
    samples = _synthetic_samples()

    splits_1 = make_splits(samples=samples, seed=42, stratify_by_source=True)
    splits_2 = make_splits(samples=samples, seed=42, stratify_by_source=True)

    assert splits_1 == splits_2


def test_make_splits_differs_for_different_seed() -> None:
    samples = _synthetic_samples()

    splits_1 = make_splits(samples=samples, seed=41, stratify_by_source=True)
    splits_2 = make_splits(samples=samples, seed=99, stratify_by_source=True)

    assert splits_1 != splits_2


def test_make_splits_stratify_by_source_is_roughly_proportional() -> None:
    samples = _synthetic_samples()
    sample_by_id = {sample.sample_id: sample for sample in samples}

    splits = make_splits(samples=samples, seed=7, stratify_by_source=True)

    overall = Counter(sample.dataset_source for sample in samples)
    overall_ratio_a = overall["dataset_a"] / len(samples)

    for split_name in ("train", "cal", "test"):
        split_ids = splits[split_name]
        split_counts = Counter(sample_by_id[sample_id].dataset_source for sample_id in split_ids)
        ratio_a = split_counts["dataset_a"] / len(split_ids)
        assert abs(ratio_a - overall_ratio_a) <= 0.15
