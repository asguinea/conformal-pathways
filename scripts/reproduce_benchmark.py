"""Reproduce a frozen suite from a clean snapshot and installed wheel.

Use a new output directory under artifacts/. Requires git and uv. Installation
can use the network; experiment execution blocks Python network audit events.
The environment and checkout remain local for inspection. No data is downloaded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--revision", default="HEAD")
    parser.add_argument("--config", type=Path, default=Path("experiments/batch3-v1.json"))
    parser.add_argument("--suite", choices=["synthetic", "real"], default="synthetic")
    parser.add_argument("--data-root", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    config = (root / args.config).resolve().relative_to(root)
    if args.suite == "real" and args.data_root is None:
        parser.error("--data-root is required for real reproduction")
    data_args = ["--data-root", str(args.data_root.resolve())] if args.data_root else []
    out = args.out.resolve()
    wheel = args.wheel.resolve(strict=True)
    if out.exists() and any(out.iterdir()):
        parser.error("use a new empty directory; earlier attempts are preserved")
    out.mkdir(parents=True, exist_ok=True)
    saved_wheel = out / wheel.name
    shutil.copy2(wheel, saved_wheel)
    wheel = saved_wheel
    uv = shutil.which("uv")
    if not uv:
        parser.error("uv is required")
    env = os.environ.copy()
    for key in ("PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT"):
        env.pop(key, None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    def run(command, cwd=out, capture=False):
        return subprocess.run(
            command, cwd=cwd, env=env, check=True, text=True, capture_output=capture
        ).stdout

    revision = run(["git", "rev-parse", args.revision], root, True).strip()
    archive = out / "source.tar"
    run(["git", "archive", "--format=tar", "-o", str(archive), revision], root)
    checkout = out / "checkout"
    with tarfile.open(archive) as source:
        source.extractall(checkout, filter="data")
    requirements = out / "requirements.txt"
    run(
        [
            uv,
            "export",
            "--locked",
            "--no-dev",
            "--no-emit-project",
            *(["--extra", "imaging"] if args.suite == "real" else []),
            "--output-file",
            str(requirements),
        ],
        checkout,
        True,
    )
    run([uv, "venv", "--python", sys.executable, str(out / "venv")])
    bindir = out / "venv" / ("Scripts" if os.name == "nt" else "bin")
    python = str(bindir / ("python.exe" if os.name == "nt" else "python"))
    run([uv, "pip", "install", "--python", python, "--require-hashes", "-r", str(requirements)])
    run([uv, "pip", "install", "--python", python, "--no-deps", str(wheel)])
    working = out / "outside-checkout"
    working.mkdir()
    probe = """
import sys
import pathlib
import importlib.util
import conformal_pathways
assert pathlib.Path(conformal_pathways.__file__).is_relative_to(pathlib.Path(sys.prefix))
assert importlib.util.find_spec('src') is None
suite = sys.argv[sys.argv.index('--suite') + 1]
for name in ('matplotlib', 'pytest'):
    assert importlib.util.find_spec(name) is None, name
for name in ('torch', 'torchvision', 'sklearn', 'PIL'):
    assert (importlib.util.find_spec(name) is not None) == (suite == 'real'), name
def block_network(event, args):
    if (suite == 'synthetic' and event.startswith('socket.')) or event in {
        'socket.connect', 'socket.getaddrinfo', 'socket.gethostbyname',
        'socket.gethostbyaddr', 'socket.bind', 'socket.sendto', 'socket.sendmsg',
    }:
        raise RuntimeError('network blocked during reproduction: ' + event)
sys.addaudithook(block_network)
from conformal_pathways.benchmarks.__main__ import main
main(sys.argv[1:])
"""
    run(
        [
            python,
            "-I",
            "-c",
            probe,
            "run",
            "--config",
            str(checkout / config),
            "--suite",
            args.suite,
            "--out",
            str(out / args.suite),
            *data_args,
        ],
        working,
    )
    record = {
        "status": "completed_independent_run; comparison_required",
        "checkout_revision": revision,
        "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
        "requirements_sha256": hashlib.sha256(requirements.read_bytes()).hexdigest(),
        "execution": "installed_wheel_isolated_python_outside_clean_checkout",
        "suite": args.suite,
        "configuration": str(config),
        "socket_operations": "all_python_socket_events_blocked"
        if args.suite == "synthetic"
        else "python_connect_resolution_bind_send_events_blocked",
        "optional_dependencies": "absent" if args.suite == "synthetic" else "imaging_only",
    }
    (out / "reproduction.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
