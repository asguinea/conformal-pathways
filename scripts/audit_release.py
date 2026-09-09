"""Check tracked release assets, local documentation links, and frozen sources.

Run from a Git checkout with the benchmark tags fetched. This does not access
external datasets, install packages, or certify scientific or legal claims.
Secret scanning is a separate release check.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tomllib
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_SUFFIXES = {
    "",
    ".py",
    ".md",
    ".toml",
    ".lock",
    ".json",
    ".jsonl",
    ".csv",
    ".svg",
    ".png",
    ".yml",
    ".yaml",
    ".cff",
}
FORBIDDEN_ROOTS = {".venv", "artifacts", "data", "datasets", "results", "dist", "build"}


def git(*arguments: str) -> bytes:
    return subprocess.check_output(["git", *arguments], cwd=ROOT)


def main() -> None:
    paths = [Path(p.decode()) for p in git("ls-files", "-z").split(b"\0") if p]
    errors: list[str] = []
    total_bytes = 0
    links_checked = 0
    for relative in paths:
        path = ROOT / relative
        if (
            relative.parts[0] in FORBIDDEN_ROOTS
            or (relative.suffix not in ALLOWED_SUFFIXES and relative.name != "MANIFEST.in")
            or path.is_symlink()
            or relative.name.startswith(".env")
        ):
            errors.append(f"Unexpected release asset: {relative}")
            continue
        data = path.read_bytes()
        total_bytes += len(data)
        if len(data) > 40_000_000:
            errors.append(f"Oversized release asset: {relative}")
        if relative.suffix == ".png":
            if relative.parts[0] != "evidence" or not data.startswith(b"\x89PNG\r\n\x1a\n"):
                errors.append(f"Unexpected image: {relative}")
            continue
        try:
            content = data.decode("utf-8")
        except UnicodeDecodeError:
            errors.append(f"Unexpected binary asset: {relative}")
            continue
        # Reject accidental machine-specific paths without printing their contents.
        private_roots = ["/" + name + "/" for name in ("Users", "Volumes", "home")]
        if any(prefix in content for prefix in private_roots):
            errors.append(f"Machine-specific path in {relative}")
        if relative.suffix == ".md":
            for match in re.finditer(r"\[[^\]]*\]\(([^)]+)\)", content):
                target = match.group(1).strip("<>")
                parsed = urlsplit(target)
                if parsed.scheme or parsed.netloc or not parsed.path:
                    continue
                local = (path.parent / unquote(parsed.path)).resolve()
                links_checked += 1
                if not local.is_relative_to(ROOT) or not local.exists():
                    errors.append(f"Broken local link in {relative}: {target}")

    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    if metadata["license"] != "Apache-2.0" or metadata["version"] != "0.4.0":
        errors.append("Unexpected release license or version")
    if "Private :: Do Not Upload" in metadata.get("classifiers", []):
        errors.append("Development-only classifier remains")
    for required in ("LICENSE", "NOTICE", "CITATION.cff", "CONTRIBUTING.md", "SECURITY.md"):
        if Path(required) not in paths:
            errors.append(f"Required release file is not tracked: {required}")

    package_files_checked = 0
    frozen_files_checked = 0
    for tag, lock_name in (
        ("baseline-entry-v2", "batch3-v2"),
        ("sequential-benchmark-v1", "batch3-sequential-v1"),
    ):
        lock_path = f"experiments/{lock_name}.lock.json"
        lock = json.loads(git("show", f"{tag}:{lock_path}"))
        for name, expected in lock["files"].items():
            actual = hashlib.sha256(git("show", f"{tag}:{name}")).hexdigest()
            frozen_files_checked += 1
            if actual != expected:
                errors.append(f"Frozen source mismatch: {tag}:{name}")
            if tag == "sequential-benchmark-v1" and name.startswith("src/conformal_pathways/"):
                package_files_checked += 1
                if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
                    errors.append(f"Release scientific source differs from benchmark: {name}")

    for workflow in (ROOT / ".github/workflows").glob("*.yml"):
        content = workflow.read_text()
        for action in re.findall(r"uses:\s+(\S+)", content):
            if not re.fullmatch(r"[\w.-]+/[\w./-]+@[0-9a-f]{40}", action):
                errors.append(f"Unpinned action in {workflow.name}: {action}")
        if "pull_request_target" in content:
            errors.append(f"Privileged pull-request trigger in {workflow.name}")

    if errors:
        raise SystemExit("\n".join(errors))
    print(
        json.dumps(
            {
                "status": "passed",
                "tracked_files": len(paths),
                "tracked_bytes": total_bytes,
                "local_links_checked": links_checked,
                "frozen_files_checked": frozen_files_checked,
                "unchanged_scientific_package_files": package_files_checked,
                "scope": "tracked asset boundaries, local links, metadata, frozen source bytes, action pins",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
