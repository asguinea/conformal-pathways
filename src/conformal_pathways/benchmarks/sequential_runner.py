"""Serial sequential/entry benchmark with complete designs and compressed local reports."""

from __future__ import annotations

import gzip
import json
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from conformal_pathways.data.splits import make_splits
from conformal_pathways.eval.experiment import evaluate_experiment
from conformal_pathways.features.cache import ids_path_for, sha256_file
from conformal_pathways.models import TrivialLabelPredictor
from conformal_pathways.sequential import evaluate_sequential
from conformal_pathways.workflows import DRWorkflow, GlaucomaWorkflow

from .provenance import digest, environment, write_json
from .runner import settings, trial_specs
from .sequential_design import diagnostic_scenarios, expected_contexts, verify_protocol
from .synthetic import FrozenPredictor, KnownSignalPredictor, generate_trial

METRICS = (
    "reference_retained",
    "group_reference_retained",
    "existential_toy_acceptable",
    "realized_set_size",
    "violation_score",
    "abstention_score",
    "diagnostic_score",
    "result_unavailable_score",
    "violation_rules",
    "abstention_rules",
    "diagnostic_rules",
    "result_unavailable_rules",
)
ENTRY_METRICS = {
    "reference_retained": "oracle_retained",
    "group_reference_retained": "group_oracle_retained",
    "existential_toy_acceptable": "existential_safe",
    "realized_set_size": "set_size",
}


def flatten_metrics(report, entry=False):
    if entry:
        mapping = dict(ENTRY_METRICS)
        for short, policy in (("score", "min_total_score"), ("rules", "observed_rules_first")):
            mapping[f"violation_{short}"] = f"chosen_unsafe_rate__{policy}"
            mapping[f"abstention_{short}"] = f"chosen_empty_rate__{policy}"
        metrics = {
            name: {
                "value": report[key],
                **{
                    suffix: report[f"{key}__{suffix}"]
                    for suffix in ("numerator", "denominator", "unavailable")
                },
            }
            for name, key in mapping.items()
        }
        for name in set(METRICS) - set(metrics):
            metrics[name] = {
                "value": None,
                "numerator": 0,
                "denominator": 0,
                "unavailable": report["n_test"],
            }
        return metrics
    metrics = {name: report["metrics"][name] for name in ENTRY_METRICS}
    for short, policy in (("score", "min_stage_score"), ("rules", "observed_rules_first")):
        for name, key in (
            ("violation", "chosen_toy_violation"),
            ("abstention", "abstained"),
            ("diagnostic", "diagnostic_ordered"),
            ("result_unavailable", "result_unavailable"),
        ):
            metrics[f"{name}_{short}"] = report["metrics"]["policies"][policy][key]
    return metrics


def scientific_report(report, entry=False):
    result = deepcopy(report)
    if not entry:
        result.pop("report_sha256")
        result["provenance"].pop("environment")
    return result


def write_report(path, report):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    path.write_bytes(gzip.compress(payload, mtime=0))


def _trial(config, output, context, specification, samples, latent, splits, models):
    workflow = DRWorkflow() if context["workflow"] == "dr_workflow" else GlaucomaWorkflow()
    key = digest(context)[:20]
    inputs = {
        "samples": [asdict(s) for s in samples],
        "latent_samples": [asdict(s) for s in latent],
        "splits": splits,
    }
    write_report(output / "inputs" / f"{key}.json.gz", inputs)
    evaluation_ids = set(splits["cal"] + splits["test"])
    potential = {
        name: diagnostic_scenarios(
            workflow,
            [s for s in latent if s.sample_id in evaluation_ids],
            context["seed"],
            name,
            config["mechanisms"][name],
        )
        for name in specification["mechanisms"]
    }
    training = [s for s in samples if s.sample_id in set(splits["train"])]
    for model_name in specification["models"]:
        predictor = FrozenPredictor(models(model_name), training, samples)
        provenance = predictor.provenance()
        write_json(output / "models" / f"{key}__{model_name}.json", provenance)
        # Evaluate entry-only first so its existing set construction can also
        # serve as a numerical equivalence check of the unavailable-result arm.
        entry_metrics = {}
        for mechanism in ["entry_only", *specification["mechanisms"]]:
            for variant, alpha in settings(config, specification["alphas"]):
                setting = {
                    **context,
                    "model": model_name,
                    "mechanism": mechanism,
                    "variant": variant,
                    "alpha": alpha,
                }
                run_key = digest(setting)[:20]
                entry = mechanism == "entry_only"
                if entry:
                    case = output / "entry_cases" / f"{run_key}.csv"
                    report = evaluate_experiment(
                        workflow,
                        samples,
                        splits,
                        predictor,
                        alpha=alpha if alpha is not None else config["primary_alpha"],
                        variant=variant,
                        seed=context["seed"],
                        selection_policies=config["entry_selection_policies"],
                        emit_per_sample_csv=True,
                        per_sample_csv_path=str(case),
                        audit_paths=True,
                        split_protocol="official_partition"
                        if context["suite"] == "real"
                        else "random_groups",
                    )
                    report.pop("per_sample_csv")
                    entry_metrics[variant] = report
                else:
                    report = evaluate_sequential(
                        workflow,
                        samples,
                        splits,
                        predictor,
                        potential[mechanism],
                        alpha=alpha if alpha is not None else config["primary_alpha"],
                        variant=variant,
                        policies=config["selection_policies"],
                        model_spec=provenance,
                        split_protocol="official_partition"
                        if context["suite"] == "real"
                        else "random_groups",
                    )
                metrics = flatten_metrics(report, entry)
                if mechanism == "unavailable":
                    for name, old_name in ENTRY_METRICS.items():
                        if metrics[name]["value"] != entry_metrics[variant][old_name]:
                            raise ValueError(
                                "unavailable-result reference/set metrics differ from entry baseline"
                            )
                report_path = output / "reports" / f"{run_key}.json.gz"
                write_report(report_path, report)
                calibration = report["calibration"]
                record = {
                    "key": run_key,
                    "context": setting,
                    "metrics": metrics,
                    "input_sha256": digest(inputs),
                    "model_sha256": digest(provenance),
                    "report_path": str(report_path.relative_to(output)),
                    "scientific_sha256": digest(scientific_report(report, entry)),
                    "scenario_sha256": None if entry else report["provenance"]["scenario_sha256"],
                    "n_test": len(splits["test"]),
                    "n_cal_groups_evaluable": (
                        report["n_cal_groups_evaluable"]
                        if entry
                        else len(calibration["group_ids"])
                        if calibration
                        else None
                    ),
                    "n_cal_groups_excluded": (
                        report["n_cal_groups_excluded"]
                        if entry
                        else len(calibration["excluded_group_ids"])
                        if calibration
                        else None
                    ),
                    "thresholds": report["calibration"]["thresholds"]
                    if entry
                    else report["filter"]["thresholds"],
                }
                write_json(output / "runs" / f"{run_key}.json", record)


def _synthetic(config, output):
    for index, (context, scenario) in enumerate(trial_specs(config, "synthetic")):
        samples, splits = generate_trial(
            context["workflow"], config["synthetic"], scenario, context["seed"]
        )
        latent, latent_splits = generate_trial(
            context["workflow"],
            config["synthetic"],
            {**scenario, "missing_probability": 0.0},
            context["seed"],
        )
        if latent_splits != splits or any(
            a.prediction_input() != b.prediction_input()
            for a, b in zip(samples, latent, strict=True)
        ):
            raise ValueError("masking truth labels changed entry evidence or splits")

        def model(name):
            if name == "known_signal":
                return KnownSignalPredictor(context["workflow"], config["synthetic"])
            label, classes = (
                ("dr_severity", list(range(5)))
                if context["workflow"] == "dr_workflow"
                else ("glaucoma_risk", ["low", "high"])
            )
            if name != "class_prior":
                raise ValueError("unknown model")
            return TrivialLabelPredictor(label, classes)

        _trial(config, output, context, scenario, samples, latent, splits, model)
        if index % 8 == 0:
            print(
                json.dumps(
                    {
                        "progress": "synthetic",
                        "trial": index + 1,
                        "cohort": context["cohort"],
                        "workflow": context["workflow"],
                    }
                ),
                flush=True,
            )
    return {}


def _real(config, output, data_root, input_lock):
    import torch

    from conformal_pathways.features.extract_embeddings import extract_embeddings_from_manifest
    from conformal_pathways.models.embedding_predictor import EmbeddingLogRegPredictor

    from .datasets import prepare_dataset, verify_checkpoint

    cfg = config["real"]
    torch.set_num_threads(cfg["torch_threads"])
    torch.use_deterministic_algorithms(True)
    checkpoint = verify_checkpoint(cfg)
    prepared, audits = {}, {}
    for name in cfg["datasets"]:
        samples, manifest, root, workflow, label, classes, audit = prepare_dataset(
            name, data_root, output / "data", cfg
        )
        if audit != input_lock["dataset_audits"][name]:
            raise ValueError("raw inputs or exclusions differ from the reused input seal")
        path = output / "embeddings" / f"{name}.npy"
        print(
            json.dumps({"progress": "extracting", "dataset": name, "n_images": len(samples)}),
            flush=True,
        )
        extract_embeddings_from_manifest(
            str(manifest),
            str(root),
            str(path),
            batch_size=cfg["batch_size"],
            num_workers=cfg["num_workers"],
            weights=cfg["weights"],
            device=cfg["device"],
        )
        prepared[name] = samples, label, classes, path
        audits[name] = audit
    for context, specification in trial_specs(config, "real"):
        samples, label, classes, path = prepared[context["cohort"]]
        splits = make_splits(samples, context["seed"], tuple(cfg["ratios"]))

        def model(name):
            if name == "class_prior":
                return TrivialLabelPredictor(label, classes)
            if name != "resnet50_logreg":
                raise ValueError("unknown model")
            return EmbeddingLogRegPredictor(
                str(path),
                str(ids_path_for(path)),
                {
                    s.sample_id: s.get_label(label)
                    for s in samples
                    if s.sample_id in splits["train"]
                },
                classes,
                C=cfg["logreg_C"],
            )

        _trial(config, output, context, specification, samples, samples, splits, model)
        print(
            json.dumps(
                {"progress": "evaluated", "dataset": context["cohort"], "seed": context["seed"]}
            ),
            flush=True,
        )
    return {"dataset_audits": audits, "checkpoint": checkpoint}


def run_suite(config_path, suite, output, data_root=None):
    config, frozen = verify_protocol(config_path)
    expected = expected_contexts(config, suite)
    output = Path(output).resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError("use a new empty output directory; preserve earlier attempts")
    output.mkdir(parents=True, exist_ok=True)
    started = perf_counter()
    execution = {
        "status": "running",
        "suite": suite,
        "protocol": config,
        "freeze": frozen,
        "environment": environment(),
        "expected_records": len(expected),
        "started_utc": datetime.now(timezone.utc).isoformat(),
    }
    write_json(output / "execution.json", execution)
    try:
        if suite == "real":
            if data_root is None:
                raise ValueError("real suite requires --data-root")
            seal = json.loads(
                (
                    Path(config_path).resolve().parent.parent / config["reused_input_lock"]
                ).read_text()
            )
            execution["input_lock"] = seal
            detail = _real(config, output, data_root, seal)
        else:
            detail = _synthetic(config, output)
        actual = [json.loads(p.read_text())["context"] for p in (output / "runs").glob("*.json")]
        if sorted(map(digest, actual)) != sorted(map(digest, expected)):
            raise ValueError("incomplete or unexpected comparison records")
        files = {
            str(p.relative_to(output)): sha256_file(p)
            for p in sorted(output.rglob("*"))
            if p.is_file() and p.name != "execution.json"
        }
        execution.update(status="complete", actual_records=len(actual), detail=detail, files=files)
    except Exception as exc:
        execution.update(status="failed", error_type=type(exc).__name__, error=str(exc))
        raise
    finally:
        execution.update(
            elapsed_seconds=perf_counter() - started,
            finished_utc=datetime.now(timezone.utc).isoformat(),
        )
        write_json(output / "execution.json", execution)
    return {k: execution[k] for k in ("status", "suite", "actual_records", "elapsed_seconds")}
