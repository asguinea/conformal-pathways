"""Execute every predeclared comparison and preserve case-level evidence."""

from __future__ import annotations

import itertools
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from conformal_pathways.data.splits import make_splits
from conformal_pathways.eval.experiment import evaluate_experiment
from conformal_pathways.features.cache import ids_path_for, sha256_file
from conformal_pathways.models import TrivialLabelPredictor
from conformal_pathways.workflows import DRWorkflow, GlaucomaWorkflow

from .provenance import digest, environment, verify_protocol, write_json
from .synthetic import FrozenPredictor, KnownSignalPredictor, generate_trial

METRICS = (
    "group_oracle_retained",
    "set_size",
    "empty_set_rate",
    "unsafe_exposure",
    "chosen_unsafe_rate__observed_rules_first",
    "chosen_empty_rate__observed_rules_first",
    "chosen_unsafe_rate__min_total_score",
    "chosen_empty_rate__min_total_score",
)


def settings(config, alphas):
    return [
        (variant, alpha)
        for variant in config["variants"]
        for alpha in ([None] if variant == "no_conformal" else alphas)
    ]


def trial_specs(config, suite):
    if suite == "synthetic":
        for scenario_index, scenario in enumerate(config["synthetic"]["scenarios"]):
            for workflow_index, workflow in enumerate(config["workflows"]):
                for repetition in range(scenario["repetitions"]):
                    seed = (
                        config["synthetic"]["seed_base"]
                        + scenario_index * 1_000_000
                        + workflow_index * 100_000
                        + repetition
                    )
                    yield (
                        {
                            "suite": suite,
                            "cohort": scenario["name"],
                            "workflow": workflow,
                            "repeat": repetition,
                            "seed": seed,
                        },
                        scenario,
                    )
    elif suite == "real":
        for name, seed in itertools.product(config["real"]["datasets"], config["real"]["seeds"]):
            yield (
                {
                    "suite": suite,
                    "cohort": name,
                    "workflow": "dr_workflow" if name == "idrid" else "glaucoma_workflow",
                    "repeat": seed,
                    "seed": seed,
                },
                config["real"],
            )
    else:
        raise ValueError("unknown benchmark suite")


def expected_contexts(config, suite):
    contexts = []
    for trial, specification in trial_specs(config, suite):
        for model in specification["models"]:
            for variant, alpha in settings(config, specification["alphas"]):
                contexts.append({**trial, "model": model, "variant": variant, "alpha": alpha})
    if len({digest(c) for c in contexts}) != len(contexts):
        raise ValueError("duplicate benchmark settings")
    return contexts


def _evaluate_trial(config, output, context, specification, samples, splits, models):
    workflow = DRWorkflow() if context["workflow"] == "dr_workflow" else GlaucomaWorkflow()
    trial_key = digest(context)[:20]
    write_json(
        output / "inputs" / f"{trial_key}.json",
        {"samples": [asdict(s) for s in samples], "splits": splits},
    )
    training = [s for s in samples if s.sample_id in set(splits["train"])]
    records = []
    for model_name in specification["models"]:
        predictor = FrozenPredictor(models(model_name), training, samples)
        provenance = predictor.provenance()
        write_json(output / "models" / f"{trial_key}__{model_name}.json", provenance)
        write_json(
            output / "predictions" / f"{trial_key}__{model_name}.json",
            predictor.prediction_records(),
        )
        for variant, alpha in settings(config, specification["alphas"]):
            setting = {**context, "model": model_name, "variant": variant, "alpha": alpha}
            key = digest(setting)[:20]
            case_path = output / "cases" / f"{key}.csv"
            metrics = evaluate_experiment(
                workflow,
                samples,
                splits,
                predictor,
                alpha=alpha,
                alpha_allocation=config["alpha_allocation"],
                variant=variant,
                seed=context["seed"],
                selection_policies=config["selection_policies"],
                emit_per_sample_csv=True,
                per_sample_csv_path=str(case_path),
                audit_paths=True,
                split_protocol="official_partition"
                if context["suite"] == "real"
                else "random_groups",
            )
            metrics.pop("per_sample_csv")
            record = {
                "key": key,
                "context": setting,
                "metrics": metrics,
                "model_sha256": digest(provenance),
                "cases_path": str(case_path.relative_to(output)),
                "cases_sha256": sha256_file(case_path),
            }
            write_json(output / "runs" / f"{key}.json", record)
            records.append(key)
    return records


def _synthetic(config, output):
    for index, (context, scenario) in enumerate(trial_specs(config, "synthetic")):
        samples, splits = generate_trial(
            context["workflow"], config["synthetic"], scenario, context["seed"]
        )

        def model(name):
            if name == "known_signal":
                return KnownSignalPredictor(context["workflow"], config["synthetic"])
            if name == "class_prior":
                label, classes = (
                    ("dr_severity", list(range(5)))
                    if context["workflow"] == "dr_workflow"
                    else ("glaucoma_risk", ["low", "high"])
                )
                return TrivialLabelPredictor(label, classes)
            raise ValueError("unknown synthetic model")

        _evaluate_trial(config, output, context, scenario, samples, splits, model)
        if index % 16 == 0:
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
        if audit["images_sha256"] != input_lock["images_sha256"][name]:
            raise ValueError("image input identity differs from frozen protocol")
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
        prepared[name] = (samples, label, classes, path)
        audits[name] = audit
    for context, _ in trial_specs(config, "real"):
        name = context["cohort"]
        samples, label, classes, path = prepared[name]
        splits = make_splits(samples, context["seed"], tuple(cfg["ratios"]))
        train_ids = set(splits["train"])

        def model(model_name):
            if model_name == "class_prior":
                return TrivialLabelPredictor(label, classes)
            if model_name == "resnet50_logreg":
                return EmbeddingLogRegPredictor(
                    str(path),
                    str(ids_path_for(path)),
                    {s.sample_id: s.get_label(label) for s in samples if s.sample_id in train_ids},
                    classes,
                    C=cfg["logreg_C"],
                )
            raise ValueError("unknown real-data model")

        _evaluate_trial(config, output, context, cfg, samples, splits, model)
        print(
            json.dumps({"progress": "evaluated", "dataset": name, "seed": context["seed"]}),
            flush=True,
        )
    return {"dataset_audits": audits, "checkpoint": checkpoint}


def run_suite(config_path, suite, output, data_root=None):
    config, lock = verify_protocol(config_path)
    expected = expected_contexts(config, suite)
    output = Path(output).resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError("use a new empty output directory; previous attempts are preserved")
    output.mkdir(parents=True, exist_ok=True)
    started = perf_counter()
    run = {
        "schema_version": 1,
        "status": "running",
        "suite": suite,
        "protocol": config,
        "freeze": lock,
        "environment": environment(),
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "expected_records": len(expected),
    }
    write_json(output / "execution.json", run)
    try:
        if suite == "real" and data_root is None:
            raise ValueError("real suite requires --data-root")
        if suite == "real":
            from .datasets import load_input_lock

            run["input_lock"] = load_input_lock(config_path, config, lock)
        detail = (
            _synthetic(config, output)
            if suite == "synthetic"
            else _real(config, output, data_root, run["input_lock"])
        )
        actual = [json.loads(p.read_text())["context"] for p in (output / "runs").glob("*.json")]
        if sorted(map(digest, actual)) != sorted(map(digest, expected)):
            raise ValueError("incomplete or unexpected comparison records")
        files = {
            str(p.relative_to(output)): sha256_file(p)
            for p in sorted(output.rglob("*"))
            if p.is_file() and p.name != "execution.json"
        }
        run.update(status="complete", actual_records=len(actual), files=files, detail=detail)
    except Exception as exc:
        run.update(status="failed", error_type=type(exc).__name__, error=str(exc))
        raise
    finally:
        run.update(
            elapsed_seconds=perf_counter() - started,
            finished_utc=datetime.now(timezone.utc).isoformat(),
        )
        write_json(output / "execution.json", run)
    print(
        json.dumps(
            {
                "status": "complete",
                "suite": suite,
                "records": len(expected),
                "elapsed_seconds": run["elapsed_seconds"],
            }
        ),
        flush=True,
    )
    return run
