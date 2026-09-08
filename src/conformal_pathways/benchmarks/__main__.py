"""Commands for freezing, running, comparing, and regenerating evidence."""

from __future__ import annotations

import argparse
import json
import os


def main(argv=None):
    # Set before importing NumPy/BLAS. These affect this process only.
    for name in (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS",
    ):
        os.environ[name] = "1"
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    freeze = commands.add_parser("freeze")
    freeze.add_argument("--config", required=True)
    audit = commands.add_parser("audit-data")
    audit.add_argument("--config", required=True)
    audit.add_argument("--data-root", required=True)
    run = commands.add_parser("run")
    run.add_argument("--config", required=True)
    run.add_argument("--suite", choices=["synthetic", "real"], required=True)
    run.add_argument("--out", required=True)
    run.add_argument("--data-root")
    publish = commands.add_parser(
        "publish-local", help="Generate local evidence files; does not upload anything"
    )
    publish.add_argument("--runs", nargs="+", required=True)
    publish.add_argument("--allow-pending-real", action="store_true")
    publish.add_argument("--out", required=True)
    verify = commands.add_parser("verify-evidence")
    verify.add_argument("path")
    compare = commands.add_parser("compare")
    compare.add_argument("first")
    compare.add_argument("second")
    args = parser.parse_args(argv)
    if args.command == "freeze":
        from .provenance import freeze_protocol

        result = freeze_protocol(args.config)
    elif args.command == "audit-data":
        from .datasets import audit_input_lock

        result = audit_input_lock(args.config, args.data_root)
    elif args.command == "run":
        from .runner import run_suite

        result = run_suite(args.config, args.suite, args.out, args.data_root)
        result = {k: result[k] for k in ("status", "suite", "actual_records", "elapsed_seconds")}
    else:
        from .reporting import compare_bundles, publish_bundles, verify_public_evidence

        if args.command == "publish-local":
            result = publish_bundles(args.runs, args.out, args.allow_pending_real)
        elif args.command == "verify-evidence":
            result = verify_public_evidence(args.path)
        else:
            result = compare_bundles(args.first, args.second)
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
