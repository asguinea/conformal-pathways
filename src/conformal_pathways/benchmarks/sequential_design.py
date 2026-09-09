"""Prospectively frozen design for result-aware experiments and matched controls."""

from __future__ import annotations

import json
import random
import subprocess
from pathlib import Path

from conformal_pathways.sequential import DiagnosticScenario

from .provenance import digest, verify_files, write_json
from .runner import settings, trial_specs


def load_config(path):
    config = json.loads(Path(path).read_text())
    if (
        config.get("schema_version") != 1
        or config.get("algorithm_version") != "result-aware-pathways-v1"
        or config.get("entry_baseline_version") != "entry-pathways-v2"
        or config.get("rule_version") != "toy-rules-v2"
    ):
        raise ValueError("unsupported sequential protocol")
    if config["variants"] != ["main", "model_only", "rules_only", "no_conformal"]:
        raise ValueError("all four fixed variants are required")
    if config["selection_policies"] != ["min_stage_score", "observed_rules_first"]:
        raise ValueError("unsupported stage selectors")
    if config["entry_selection_policies"] != ["min_total_score", "observed_rules_first"]:
        raise ValueError("unsupported entry selectors")
    if config["alpha_allocation"] != "uniform" or config["primary_alpha"] != 0.1:
        raise ValueError("this experiment uses uniform allocation and primary alpha .1")
    for mechanism in config["mechanisms"].values():
        if any(not 0 <= v <= 1 for v in mechanism.values()):
            raise ValueError("invalid diagnostic error/missingness probability")
    for scenario in config["synthetic"]["scenarios"]:
        if (
            scenario["test_groups"] != 1
            or scenario["alphas"] != [0.1]
            or min(scenario[k] for k in ("train_groups", "cal_groups", "repetitions")) < 1
        ):
            raise ValueError("invalid synthetic repetition design")
        if not 0 <= scenario["missing_probability"] < 1:
            raise ValueError("invalid truth-label missingness")
    for specification in [*config["synthetic"]["scenarios"], config["real"]]:
        if (
            not {"perfect", "unavailable"}
            <= set(specification["mechanisms"])
            <= set(config["mechanisms"])
        ):
            raise ValueError("perfect and unavailable controls are required")
    return config


def expected_contexts(config, suite):
    result = []
    for trial, specification in trial_specs(config, suite):
        for model in specification["models"]:
            for mechanism in [*specification["mechanisms"], "entry_only"]:
                for variant, alpha in settings(config, specification["alphas"]):
                    result.append(
                        {
                            **trial,
                            "model": model,
                            "mechanism": mechanism,
                            "variant": variant,
                            "alpha": alpha,
                        }
                    )
    if len({digest(c) for c in result}) != len(result):
        raise ValueError("duplicate experimental settings")
    return result


def source_files(config_path):
    path = Path(config_path).resolve()
    root, config = path.parent.parent, load_config(path)
    files = list((root / "src/conformal_pathways").rglob("*.py"))
    files += [path, root / "pyproject.toml", root / "uv.lock"]
    for relative in [
        *config["protocol_documents"],
        config["reused_input_lock"],
        "scripts/reproduce_benchmark.py",
        "scripts/run_monitored.py",
    ]:
        target = (root / relative).resolve()
        if not target.is_relative_to(root):
            raise ValueError("frozen inputs must be inside the repository")
        files.append(target)
    from conformal_pathways.features.cache import sha256_file

    return {str(p.relative_to(root)): sha256_file(p) for p in sorted(files)}


def freeze(config_path):
    path = Path(config_path).resolve()
    lock_path = path.with_suffix(".lock.json")
    if lock_path.exists():
        raise ValueError("freeze exists; use a new prospective protocol amendment")
    files = source_files(path)
    root = path.parent.parent
    changes = subprocess.check_output(["git", "status", "--porcelain", "--", *files], cwd=root)
    if changes.strip():
        raise ValueError("commit implementation and protocol before freezing")
    record = {
        "schema_version": 1,
        "files": files,
        "source_sha256": digest(files),
        "source_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True
        ).strip(),
    }
    write_json(lock_path, record)
    return record


def verify_protocol(config_path):
    path = Path(config_path).resolve()
    config = load_config(path)
    record = json.loads(path.with_suffix(".lock.json").read_text())
    if source_files(path) != record["files"] or digest(record["files"]) != record["source_sha256"]:
        raise ValueError("frozen sequential source, protocol, or input seal changed")
    import conformal_pathways

    installed = Path(conformal_pathways.__file__).parent
    verify_files(
        installed,
        {
            k.removeprefix("src/conformal_pathways/"): v
            for k, v in record["files"].items()
            if k.startswith("src/conformal_pathways/")
        },
    )
    return config, record


def diagnostic_scenarios(workflow, latent_samples, seed, name, specification):
    """Group-shared independent error/missingness draws, common across paired arms.

    Latent truth is retained even when evaluation labels are masked. The same
    group result is reused across all actions, models, and variants in a trial.
    The session/selector never receives these scenarios directly.
    """
    values = {}
    for sample in latent_samples:
        rng = random.Random(f"result-aware-v1:{seed}:{sample.group_id()}")
        missing, wrong = rng.random(), rng.random()
        value = sample.labels["dme_positive" if workflow.name == "dr_workflow" else "glaucoma_risk"]
        if missing < specification["unavailable_probability"]:
            value = None
        elif wrong < specification["flip_probability"]:
            value = not value if isinstance(value, bool) else "low" if value == "high" else "high"
        values[sample.sample_id] = DiagnosticScenario(
            workflow.name, value, "simulated_retrospective_proxy", f"sequential-v1:{name}"
        )
    return values
