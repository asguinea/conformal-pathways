from __future__ import annotations

import math
import random
from collections import defaultdict

from .schema import Sample, validate_samples


def validate_splits(samples: list[Sample], splits: dict[str, list[str]]) -> None:
    validate_samples(samples)
    if set(splits) != {"train", "cal", "test"}:
        raise ValueError("splits must have train, cal, test keys")
    assigned = [sid for ids in splits.values() for sid in ids]
    if len(assigned) != len(set(assigned)) or set(assigned) != {s.sample_id for s in samples}:
        raise ValueError("split overlap, duplicate, missing, or unknown sample IDs")
    if not _check_no_group_leakage(samples, splits):
        raise ValueError("group leakage across splits")


def _check_no_group_leakage(samples: list[Sample], splits: dict[str, list[str]]) -> bool:
    lookup = {s.sample_id: s for s in samples}
    assigned = {}
    for name, ids in splits.items():
        for sid in ids:
            gid = lookup[sid].group_id()
            if gid in assigned and assigned[gid] != name:
                return False
            assigned[gid] = name
    return True


def _split_group_ids(group_ids, rng, ratios):
    ids = sorted(group_ids)
    rng.shuffle(ids)
    a = int(ratios[0] * len(ids))
    b = int((ratios[0] + ratios[1]) * len(ids))
    return {"train": ids[:a], "cal": ids[a:b], "test": ids[b:]}


def make_splits(
    samples: list[Sample],
    seed: int,
    ratios: tuple[float, float, float] = (0.6, 0.2, 0.2),
    stratify_by_source: bool = False,
    allow_repartition: bool = False,
) -> dict[str, list[str]]:
    validate_samples(samples)
    if (
        len(ratios) != 3
        or any(not math.isfinite(r) or r <= 0 for r in ratios)
        or not math.isclose(sum(ratios), 1, abs_tol=1e-12)
    ):
        raise ValueError("ratios must be three finite positive values summing to 1")
    groups = defaultdict(list)
    for sample in samples:
        groups[sample.group_id()].append(sample)
    rng = random.Random(seed)
    by_split = {"train": [], "cal": [], "test": []}
    any_hint = any(s.meta.get("split_hint") for s in samples)
    if any_hint and not allow_repartition:
        for gid, members in sorted(groups.items()):
            hints = {s.meta.get("split_hint") for s in members}
            if len(hints) != 1 or next(iter(hints)) not in by_split:
                raise ValueError(
                    "official split hints must be complete, valid, and consistent within groups"
                )
            by_split[next(iter(hints))].append(gid)
        # Official test membership stays fixed. If calibration is not supplied,
        # carve it exclusively from the official training groups.
        if not by_split["cal"]:
            train_groups = sorted(by_split["train"])
            rng.shuffle(train_groups)
            n_train = int(len(train_groups) * ratios[0] / (ratios[0] + ratios[1]))
            by_split["train"], by_split["cal"] = train_groups[:n_train], train_groups[n_train:]
    elif stratify_by_source:
        strata = defaultdict(list)
        for gid, members in groups.items():
            sources = {s.dataset_source for s in members}
            if len(sources) != 1:
                raise ValueError("cross-source groups cannot be stratified by source")
            strata[next(iter(sources))].append(gid)
        for source in sorted(strata):
            partial = _split_group_ids(strata[source], rng, ratios)
            for name in by_split:
                by_split[name].extend(partial[name])
    else:
        by_split = _split_group_ids(list(groups), rng, ratios)
    splits = {
        name: [s.sample_id for gid in gids for s in sorted(groups[gid], key=lambda s: s.sample_id)]
        for name, gids in by_split.items()
    }
    validate_splits(samples, splits)
    return splits
