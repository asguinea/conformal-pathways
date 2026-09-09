"""Offline result-aware evaluation. No real-data benchmark protocol is implied."""

from __future__ import annotations

import hashlib
import json
import platform
from collections import defaultdict
from copy import deepcopy
from dataclasses import asdict
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from conformal_pathways.data.splits import validate_splits
from conformal_pathways.safety.oracle import (
    RULE_VERSION,
    is_safe,
    label_unavailability,
    required_labels,
)
from conformal_pathways.safety.oracle_policy import oracle_pathway
from conformal_pathways.workflows.core import Pathway

from .calibration import calibrate
from .engine import ALGORITHM_VERSION, POLICIES, ScoreConfig, StageFilter, action_key, stage_scores
from .simulation import execute_policy, realized_prediction_set, validate_scenarios


def _digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, allow_nan=False, separators=(",", ":")).encode()
    ).hexdigest()


def _mean(values):
    available = [v for v in values if v is not None]
    return {
        "value": sum(available) / len(available) if available else None,
        "numerator": sum(available),
        "denominator": len(available),
        "unavailable": len(values) - len(available),
    }


def aggregate_cases(cases, policies):
    """Reconstruct every reported mean/rate solely from the case export."""
    result = {
        key: _mean([c[key] for c in cases])
        for key in (
            "reference_retained",
            "existential_toy_acceptable",
            "realized_set_size",
        )
    }
    groups = defaultdict(list)
    for case in cases:
        groups[case["group_id"]].append(case["reference_retained"])
    result["group_reference_retained"] = _mean(
        [None if any(v is None for v in values) else all(values) for values in groups.values()]
    )
    result["policies"] = {
        policy: {
            key: _mean([c["executions"][policy][key] for c in cases])
            for key in (
                "abstained",
                "completed",
                "diagnostic_ordered",
                "result_unavailable",
                "chosen_toy_violation",
                "label_unavailable",
            )
        }
        for policy in policies
    }
    return result


def _split_protocol(samples, splits, protocol):
    validate_splits(samples, splits)
    if protocol not in {"random_groups", "official_partition", "explicit_repartition"}:
        raise ValueError("unsupported split_protocol")
    if any(not ids for ids in splits.values()):
        raise ValueError("nonempty train/cal/test splits are required")
    has_hints = any(s.meta.get("split_hint") for s in samples)
    if protocol == "official_partition" and not has_hints:
        raise ValueError("official_partition requires source split hints")
    if has_hints and protocol != "explicit_repartition":
        assigned = {sid: name for name, ids in splits.items() for sid in ids}
        has_cal = any(s.meta.get("split_hint") == "cal" for s in samples)
        for sample in samples:
            hint = sample.meta.get("split_hint")
            allowed = {"train", "cal"} if hint == "train" and not has_cal else {hint}
            if hint not in {"train", "cal", "test"} or assigned[sample.sample_id] not in allowed:
                raise ValueError("supplied splits violate official partition")
        return "official_partition"
    return protocol


def evaluate_sequential(
    workflow,
    samples,
    splits,
    predictor,
    scenarios,
    *,
    alpha=0.1,
    allocation="uniform",
    variant="main",
    policies=POLICIES,
    split_protocol="random_groups",
    model_spec=None,
):
    """Fit once on training groups; calibrate and execute with fixed entry predictions.

    scenarios must cover calibration and test cases, never training cases. Each
    is a pre-specified potential result, delivered only after test commitment.
    policies are fixed built-ins, not callbacks with access to evaluator labels.
    Model fitting/configuration and scenario generation must be fixed without
    examining calibration scores or test outcomes. This function cannot establish
    those scientific assumptions or real patient identities from supplied IDs.
    """
    split_protocol = _split_protocol(samples, splits, split_protocol)
    policies = tuple(policies)
    if not policies or len(set(policies)) != len(policies) or not set(policies) <= set(POLICIES):
        raise ValueError("policies must be distinct supported sequential selectors")
    weights = {"main": (1, 1), "model_only": (1, 0), "rules_only": (0, 1), "no_conformal": (1, 1)}
    if variant not in weights:
        raise ValueError("unsupported sequential variant")
    config = ScoreConfig(*weights[variant])
    # Validate alpha/allocation even for the unpruned baseline, before fitting.
    from conformal_pathways.conformal.thresholds import allocate_alpha

    allocate_alpha(alpha, workflow.num_stages, allocation)
    lookup = {s.sample_id: s for s in samples}
    train, calibration, test = [
        [lookup[sid] for sid in splits[name]] for name in ("train", "cal", "test")
    ]
    mechanism = validate_scenarios(workflow, calibration + test, scenarios)
    reasons = {s.sample_id: label_unavailability(workflow.name, s.labels) for s in samples}
    input_digest = _digest([asdict(s) for s in sorted(samples, key=lambda s: s.sample_id)])
    predictor.fit(deepcopy(train))
    declared_training = {s.group_id() for s in train}
    if set(getattr(predictor, "training_groups", declared_training)) != declared_training:
        raise ValueError("fitted predictor training groups do not match the training split")
    # Predict once per entry, not once per branch or policy. Keep inference
    # batches at one case; image runners can supply a previously frozen cache.
    distributions = {}
    for sample in calibration + test:
        outputs = predictor.predict_proba([sample.prediction_input()])
        if len(outputs) != 1:
            raise ValueError("predictor must return one distribution per input")
        distribution = deepcopy(outputs[0])
        stage_scores(
            workflow, 1, workflow.initial_state(sample.observed_values()), distribution, config
        )
        distributions[sample.sample_id] = distribution
    if variant == "no_conformal":
        fitted = None
        stage_filter = StageFilter(workflow.name, (float("inf"),) * 3, config)
    else:
        fitted = calibrate(
            workflow,
            calibration,
            {s.sample_id: distributions[s.sample_id] for s in calibration},
            {s.sample_id: scenarios[s.sample_id] for s in calibration},
            alpha=alpha,
            allocation=allocation,
            score=config,
            training_groups={s.group_id() for s in train},
        )
        stage_filter = fitted.stage_filter
    cases = []
    for sample in test:
        entry = sample.prediction_input()
        distribution = distributions[sample.sample_id]
        scenario = scenarios[sample.sample_id]
        reason = reasons[sample.sample_id]
        # Execute with a restricted decision context FIRST. Retrospective tree
        # inspection below cannot influence these selections.
        executions = {}
        for policy in policies:
            session = execute_policy(workflow, entry, distribution, stage_filter, scenario, policy)
            complete = session.status == "complete"
            results = [t for t in session.trace if t["event"] == "result"]
            executions[policy] = {
                "completed": complete,
                "abstained": session.status == "abstained",
                "diagnostic_ordered": bool(results),
                "result_unavailable": (
                    results[0]["result"]["observation"]["value"] is None if results else None
                ),
                "label_unavailable": reason is not None,
                "chosen_toy_violation": (
                    not is_safe(workflow.name, sample.labels, None, Pathway(session.actions))
                    if complete and reason is None
                    else None
                ),
                "actions": [asdict(a) for a in session.actions],
                "trace": session.trace,
            }
        paths = realized_prediction_set(workflow, entry, distribution, stage_filter, scenario)
        reference = oracle_pathway(workflow, sample.labels) if reason is None else None
        retained_keys = {tuple(action_key(a) for a in p.actions) for p in paths}
        acceptable = (
            [is_safe(workflow.name, sample.labels, None, p) for p in paths]
            if reason is None
            else None
        )
        cases.append(
            {
                "sample_id": sample.sample_id,
                "group_id": sample.group_id(),
                "dataset_source": sample.dataset_source,
                "entry_observations": {
                    key: asdict(value) for key, value in entry.observations.items()
                },
                "label_unavailability_reason": reason,
                "reference_retained": (
                    tuple(action_key(a) for a in reference.actions) in retained_keys
                    if reference is not None
                    else None
                ),
                "existential_toy_acceptable": any(acceptable) if acceptable is not None else None,
                "realized_set_size": len(paths),
                "executions": executions,
                "evaluation_only": {
                    "truth_labels": {
                        key: sample.labels.get(key) for key in required_labels(workflow.name)
                    },
                    "potential_result": asdict(scenario),
                    "reference": [asdict(a) for a in reference.actions] if reference else None,
                    "realized_paths": [[asdict(a) for a in p.actions] for p in paths],
                    "path_toy_acceptable": acceptable,
                },
            }
        )
    package_root = Path(__file__).resolve().parents[1]
    sources = {
        str(p.relative_to(package_root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(package_root.rglob("*.py"))
    }
    environment = {"python": platform.python_version(), "platform": platform.platform()}
    for name in ("conformal-pathways", "numpy", "pandas", "scikit-learn", "torch", "torchvision"):
        try:
            environment[name] = version(name)
        except PackageNotFoundError:
            pass
    report = {
        "schema_version": 1,
        "algorithm_version": ALGORITHM_VERSION,
        "rule_version": RULE_VERSION,
        "config": {
            "workflow": workflow.name,
            "variant": variant,
            "alpha": alpha,
            "allocation": allocation,
            "policies": list(policies),
            "selector_score": asdict(ScoreConfig()),
            "split_protocol": split_protocol,
            "mechanism": mechanism,
        },
        "splits": deepcopy(splits),
        "calibration": fitted.to_dict() if fitted else None,
        "filter": stage_filter.to_dict(),
        "metrics": aggregate_cases(cases, policies),
        "cases": cases,
        "provenance": {
            "input_manifest_sha256": input_digest,
            "scenario_sha256": _digest({sid: asdict(s) for sid, s in scenarios.items()}),
            "entry_predictions": distributions,
            "prediction_sha256": _digest(distributions),
            "predictor_class": f"{type(predictor).__module__}.{type(predictor).__qualname__}",
            "model_spec": deepcopy(model_spec),
            "source_sha256": _digest(sources),
            "environment": environment,
        },
        "scope": "simulated diagnostic results; toy predicates; no clinical or empirical claim",
    }
    report["report_sha256"] = _digest(report)
    return report
