"""Content identities and fail-closed experiment records, without local path disclosure."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import subprocess
from pathlib import Path

from conformal_pathways.features.cache import sha256_file


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def load_config(path):
    config = json.loads(Path(path).read_text())
    if (
        config.get("schema_version") != 1
        or config.get("algorithm_version") != "entry-pathways-v2"
        or config.get("rule_version") != "toy-rules-v2"
    ):
        raise ValueError("unsupported experiment schema or algorithm")
    if config["variants"] != ["main", "model_only", "rules_only", "no_conformal"]:
        raise ValueError("protocol requires all four paired variants")
    if (
        config["workflows"] != ["dr_workflow", "glaucoma_workflow"]
        or config["alpha_allocation"] != "uniform"
    ):
        raise ValueError("unsupported benchmark protocol")
    synthetic = config["synthetic"]
    if synthetic["members_per_group"] < 1:
        raise ValueError("invalid group size")
    for scenario in synthetic["scenarios"]:
        if (
            scenario["test_groups"] != 1
            or min(scenario[k] for k in ("train_groups", "cal_groups", "repetitions")) < 1
        ):
            raise ValueError("coverage experiments require one new test group per repetition")
        if not 0 <= scenario["missing_probability"] < 1:
            raise ValueError("invalid missingness probability")
        if any(not 0 < a < 1 for a in scenario["alphas"]):
            raise ValueError("invalid alpha")
    return config


def source_files(root, config_path):
    files = list((root / "src/conformal_pathways").rglob("*.py"))
    files += [
        root / "pyproject.toml",
        root / "uv.lock",
        config_path,
    ]
    documents = load_config(config_path).get("protocol_documents", ["docs/experiment-protocol.md"])
    for relative in documents:
        document = (root / relative).resolve()
        if not document.is_relative_to((root / "docs").resolve()) or document.suffix != ".md":
            raise ValueError("protocol documents must be Markdown files inside docs")
        files.append(document)
    return {str(p.relative_to(root)): sha256_file(p) for p in sorted(files)}


def verify_files(root, files):
    root = Path(root).resolve()
    for relative, expected in files.items():
        path = (root / relative).resolve()
        if not path.is_relative_to(root) or not path.is_file() or sha256_file(path) != expected:
            raise ValueError(f"artifact missing, changed, or outside root: {relative}")


def freeze_protocol(config_path):
    path = Path(config_path).resolve()
    root = path.parent.parent
    load_config(path)
    lock_path = path.with_suffix(".lock.json")
    if lock_path.exists():
        raise ValueError("freeze already exists; use a new protocol version for an amendment")
    files = source_files(root, path)
    check = subprocess.run(
        [
            "git",
            "status",
            "--porcelain",
            "--",
            "src",
            *files,
        ],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    if check.stdout.strip():
        raise ValueError("commit implementation and protocol before freezing")
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()
    value = {
        "schema_version": 1,
        "protocol_sha256": sha256_file(path),
        "source_revision": revision,
        "files": files,
        "source_sha256": digest(files),
    }
    write_json(lock_path, value)
    return value


def verify_protocol(config_path):
    path = Path(config_path).resolve()
    config = load_config(path)
    lock = json.loads(path.with_suffix(".lock.json").read_text())
    files = source_files(path.parent.parent, path)
    if (
        files != lock["files"]
        or digest(files) != lock["source_sha256"]
        or sha256_file(path) != lock["protocol_sha256"]
    ):
        raise ValueError("frozen protocol or implementation changed")
    # Also verify the imported package when reproducing from an installed wheel.
    import conformal_pathways

    installed = Path(conformal_pathways.__file__).parent
    for relative, expected in files.items():
        if relative.startswith("src/conformal_pathways/"):
            target = installed / relative.removeprefix("src/conformal_pathways/")
            if not target.is_file() or sha256_file(target) != expected:
                raise ValueError("installed package differs from frozen source")
    return config, lock


def environment():
    names = [
        "conformal-pathways",
        "numpy",
        "pandas",
        "scikit-learn",
        "torch",
        "torchvision",
        "pillow",
        "matplotlib",
    ]
    versions = {}
    for name in names:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    return {
        "python": platform.python_version(),
        "system": platform.system(),
        "machine": platform.machine(),
        "packages": versions,
    }
