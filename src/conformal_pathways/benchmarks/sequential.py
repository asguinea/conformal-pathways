"""Freeze, execute, reproduce and report the result-aware experiment protocol."""

import argparse
import json
import os


def main(argv=None):
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
    run = commands.add_parser("run")
    run.add_argument("--config", required=True)
    run.add_argument("--suite", choices=("synthetic", "real"), required=True)
    run.add_argument("--out", required=True)
    run.add_argument("--data-root")
    compare = commands.add_parser("compare")
    compare.add_argument("first")
    compare.add_argument("second")
    publish = commands.add_parser("publish-local")
    publish.add_argument("--runs", nargs="+", required=True)
    publish.add_argument("--out", required=True)
    verify = commands.add_parser("verify-evidence")
    verify.add_argument("path")
    args = parser.parse_args(argv)
    if args.command == "freeze":
        from .sequential_design import freeze

        result = freeze(args.config)
    elif args.command == "run":
        from .sequential_runner import run_suite

        result = run_suite(args.config, args.suite, args.out, args.data_root)
    else:
        from .sequential_reporting import compare, publish, verify_public

        if args.command == "compare":
            result = compare(args.first, args.second)
        elif args.command == "publish-local":
            result = publish(args.runs, args.out)
        else:
            result = verify_public(args.path)
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
