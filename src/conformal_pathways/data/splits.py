from __future__ import annotations

import random
from collections import defaultdict

from conformal_pathways.data.schema import Sample


def _check_no_group_leakage(samples: list[Sample], splits: dict[str, list[str]]) -> bool:
    sample_by_id = {sample.sample_id: sample for sample in samples}
    group_to_split: dict[str, str] = {}

    for split_name, sample_ids in splits.items():
        for sample_id in sample_ids:
            sample = sample_by_id[sample_id]
            group_id = sample.group_id()
            previous_split = group_to_split.get(group_id)
            if previous_split is None:
                group_to_split[group_id] = split_name
            elif previous_split != split_name:
                return False
    return True


def _split_group_ids(
    group_ids: list[str],
    rng: random.Random,
    ratios: tuple[float, float, float],
) -> dict[str, list[str]]:
    shuffled = sorted(group_ids)
    rng.shuffle(shuffled)

    n_groups = len(shuffled)
    n_train = int(ratios[0] * n_groups)
    n_cal = int((ratios[0] + ratios[1]) * n_groups) - n_train

    train_ids = shuffled[:n_train]
    cal_ids = shuffled[n_train : n_train + n_cal]
    test_ids = shuffled[n_train + n_cal :]

    return {"train": train_ids, "cal": cal_ids, "test": test_ids}


def make_splits(
    samples: list[Sample],
    seed: int,
    ratios: tuple[float, float, float] = (0.6, 0.2, 0.2),
    stratify_by_source: bool = True,
) -> dict[str, list[str]]:
    if len(ratios) != 3:
        raise ValueError("ratios must have exactly three values: (train, cal, test)")
    if abs(sum(ratios) - 1.0) > 1e-6:
        raise ValueError("ratios must sum to 1.0")

    rng = random.Random(seed)

    group_to_sample_ids: dict[str, list[str]] = defaultdict(list)
    group_to_source: dict[str, str] = {}
    source_to_group_ids: dict[str, set[str]] = defaultdict(set)
    all_sample_ids = set()

    for sample in samples:
        group_id = sample.group_id()
        group_to_sample_ids[group_id].append(sample.sample_id)
        source_to_group_ids[sample.dataset_source].add(group_id)
        all_sample_ids.add(sample.sample_id)

        previous_source = group_to_source.get(group_id)
        if previous_source is None:
            group_to_source[group_id] = sample.dataset_source
        elif previous_source != sample.dataset_source:
            raise ValueError(
                f"group '{group_id}' spans multiple dataset_source values: "
                f"'{previous_source}' and '{sample.dataset_source}'"
            )

    split_group_ids: dict[str, list[str]] = {"train": [], "cal": [], "test": []}

    if stratify_by_source:
        for source in sorted(source_to_group_ids):
            partial = _split_group_ids(list(source_to_group_ids[source]), rng, ratios)
            for split_name in ("train", "cal", "test"):
                split_group_ids[split_name].extend(partial[split_name])
    else:
        partial = _split_group_ids(list(group_to_sample_ids.keys()), rng, ratios)
        for split_name in ("train", "cal", "test"):
            split_group_ids[split_name].extend(partial[split_name])

    splits: dict[str, list[str]] = {"train": [], "cal": [], "test": []}
    for split_name in ("train", "cal", "test"):
        for group_id in split_group_ids[split_name]:
            splits[split_name].extend(sorted(group_to_sample_ids[group_id]))

    train_set = set(splits["train"])
    cal_set = set(splits["cal"])
    test_set = set(splits["test"])
    if train_set & cal_set or train_set & test_set or cal_set & test_set:
        raise AssertionError("split overlap detected")

    assigned_ids = train_set | cal_set | test_set
    if assigned_ids != all_sample_ids:
        raise AssertionError("not all samples were assigned exactly once")

    if not _check_no_group_leakage(samples, splits):
        raise AssertionError("group leakage detected across splits")

    return splits
