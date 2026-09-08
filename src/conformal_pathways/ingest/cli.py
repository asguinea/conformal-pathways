from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from conformal_pathways.ingest.registry import get_builder, list_builders


def _coerce_value(value: str) -> Any:
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


def parse_extra_kwargs(tokens: list[str]) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if not token.startswith("--"):
            i += 1
            continue
        token = token[2:]
        if "=" in token:
            key, value = token.split("=", 1)
            kwargs[key.replace("-", "_")] = _coerce_value(value)
            i += 1
            continue

        key = token.replace("-", "_")
        if i + 1 < len(tokens) and not tokens[i + 1].startswith("--"):
            kwargs[key] = _coerce_value(tokens[i + 1])
            i += 2
        else:
            kwargs[key] = True
            i += 1
    return kwargs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Dataset manifest ingestion")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list", help="List available dataset builders")

    build_parser = subparsers.add_parser("build", help="Build dataset manifest")
    build_parser.add_argument("--dataset", required=True)
    build_parser.add_argument("--root", required=True)
    build_parser.add_argument("--out", required=True)
    build_parser.add_argument("--dry-run", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    # Trigger default builder registration via package import side effect.
    import conformal_pathways.ingest  # noqa: F401

    parser = build_parser()
    args, unknown = parser.parse_known_args(argv)

    if args.command == "list":
        for name in list_builders():
            print(name)
        return 0

    if args.command == "build":
        builder = get_builder(args.dataset)
        kwargs = parse_extra_kwargs(unknown)
        result = builder.build_manifest(
            root=Path(args.root),
            out_csv=Path(args.out),
            dry_run=args.dry_run,
            **kwargs,
        )
        if args.dry_run:
            stats = result.get("stats", {}) if isinstance(result, dict) else {}
            print(f"dry_run rows={stats.get('n_rows', 'unknown')}")
        else:
            print(str(result))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
