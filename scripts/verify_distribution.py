"""Install a built wheel with locked core dependencies and exercise it in isolation.

Run from the checkout after building:
    uv run --locked python scripts/verify_distribution.py dist/<wheel>.whl

Requires uv on PATH and package-registry access for installation. The demo is
also run with Python socket operations blocked. No dataset or model is fetched.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


def run(command: list[str], *, cwd: Path, env: dict[str, str]) -> str:
    result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError(f"Command failed: {command[0]}\n{result.stdout}\n{result.stderr}")
    return result.stdout


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    args = parser.parse_args()
    wheel = args.wheel.resolve(strict=True)
    uv = shutil.which("uv")
    if uv is None:
        parser.error("uv must be installed and available on PATH")
    root = Path(__file__).resolve().parents[1]
    with zipfile.ZipFile(wheel) as archive:
        members = archive.namelist()
        unexpected = [
            name
            for name in members
            if not name.startswith("conformal_pathways/")
            and not name.split("/", 1)[0].endswith(".dist-info")
        ]
        if unexpected:
            raise RuntimeError(f"Unexpected wheel contents: {unexpected}")

    env = os.environ.copy()
    for key in ("PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT"):
        env.pop(key, None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    with tempfile.TemporaryDirectory(prefix="conformal-pathways-install-") as temporary:
        scratch = Path(temporary)
        working = scratch / "unrelated-working-directory"
        working.mkdir()
        requirements = scratch / "requirements.txt"
        run(
            [
                uv,
                "export",
                "--locked",
                "--no-dev",
                "--no-emit-project",
                "--format",
                "requirements-txt",
                "--output-file",
                str(requirements),
            ],
            cwd=root,
            env=env,
        )
        venv = scratch / "venv"
        run([uv, "venv", "--python", sys.executable, str(venv)], cwd=working, env=env)
        bindir = venv / ("Scripts" if os.name == "nt" else "bin")
        python = bindir / ("python.exe" if os.name == "nt" else "python")
        cli = bindir / ("conformal-pathways.exe" if os.name == "nt" else "conformal-pathways")
        ingest = bindir / (
            "conformal-pathways-ingest.exe" if os.name == "nt" else "conformal-pathways-ingest"
        )
        run(
            [
                uv,
                "pip",
                "install",
                "--python",
                str(python),
                "--require-hashes",
                "-r",
                str(requirements),
            ],
            cwd=working,
            env=env,
        )
        run(
            [uv, "pip", "install", "--python", str(python), "--no-deps", str(wheel)],
            cwd=working,
            env=env,
        )
        isolation_probe = """
import importlib.util
import pathlib
import sys
import conformal_pathways
assert pathlib.Path(conformal_pathways.__file__).is_relative_to(pathlib.Path(sys.prefix))
assert importlib.util.find_spec("src") is None
for module in ("torch", "torchvision", "sklearn", "matplotlib", "PIL", "pytest"):
    assert importlib.util.find_spec(module) is None, module
"""
        run([str(python), "-I", "-c", isolation_probe], cwd=working, env=env)
        run([str(cli), "--help"], cwd=working, env=env)
        run([str(ingest), "--help"], cwd=working, env=env)
        for command, workflow in (
            (command, workflow)
            for command in ("demo", "sequential-demo")
            for workflow in ("dr", "glaucoma")
        ):
            arguments = [command, "--workflow", workflow, "--n", "100", "--seed", "0"]
            output = run([str(cli), *arguments], cwd=working, env=env)
            module_output = run(
                [str(python), "-I", "-m", "conformal_pathways", *arguments],
                cwd=working,
                env=env,
            )
            assert output == module_output
            payload = json.loads(output)
            assert payload["scientific_validation"] == "see_claim_register"
            assert payload["verification_scope"] == "installation_smoke_only"
            assert payload["config"]["workflow"] == workflow
            offline_probe = """
import sys
def prevent_network(event, args):
    if event.startswith("socket."):
        raise RuntimeError("Network is disabled for the demo")
sys.addaudithook(prevent_network)
from conformal_pathways.cli import main
main(sys.argv[1:])
"""
            offline_output = run(
                [str(python), "-I", "-c", offline_probe, *arguments],
                cwd=working,
                env=env,
            )
            assert output == offline_output
        assert list(working.iterdir()) == []
        print(
            json.dumps(
                {
                    "status": "passed",
                    "wheel": wheel.name,
                    "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
                    "python": platform.python_version(),
                    "platform": f"{platform.system()} {platform.machine()}",
                    "checks": [
                        "wheel contains package and metadata only",
                        "locked core dependencies installed with hashes",
                        "package imported from isolated environment outside checkout",
                        "optional dependencies and original import namespace absent",
                        "both CLI entry points provide help",
                        "entry and sequential demos for both workflows match console, module, and socket-blocked runs",
                        "demo working directory remains empty",
                    ],
                },
                indent=2,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
