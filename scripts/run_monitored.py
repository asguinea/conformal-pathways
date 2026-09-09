"""Run one command, record peak process-group RSS, and stop on memory pressure.

Example: python scripts/run_monitored.py --record artifacts/run-memory.json
--log artifacts/run.log -- python -m conformal_pathways.benchmarks ...
Only the newly created command's process group can be terminated by this guard.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import signal
import subprocess
import time
from pathlib import Path


def group_rss_kib(pgid):
    result = subprocess.run(
        ["ps", "-axo", "pgid=,rss="], capture_output=True, text=True, check=True
    )
    return sum(
        int(rss)
        for group, rss in (line.split() for line in result.stdout.splitlines())
        if int(group) == pgid
    )


def pressure_level():
    if platform.system() != "Darwin":
        return None
    result = subprocess.run(
        ["sysctl", "-n", "kern.memorystatus_vm_pressure_level"],
        capture_output=True,
        text=True,
        check=False,
    )
    return int(result.stdout.strip()) if result.returncode == 0 else None


def stop_group(process):
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--max-rss-gib", type=float, default=8.0)
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command or args.max_rss_gib <= 0 or args.interval <= 0:
        parser.error("provide a command and positive resource limits")
    if args.record.exists() or args.log.exists():
        parser.error("use new record and log paths; earlier attempts are preserved")
    args.record.parent.mkdir(parents=True, exist_ok=True)
    args.log.parent.mkdir(parents=True, exist_ok=True)
    start, peak, highest_pressure, reason = time.monotonic(), 0, None, None
    with args.log.open("x") as log:
        process = subprocess.Popen(
            command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True
        )

        def interrupted(signum, frame):
            raise KeyboardInterrupt

        signal.signal(signal.SIGTERM, interrupted)
        try:
            while process.poll() is None:
                peak = max(peak, group_rss_kib(process.pid))
                pressure = pressure_level()
                if pressure is not None:
                    highest_pressure = max(highest_pressure or 0, pressure)
                if peak > args.max_rss_gib * 1024**2:
                    reason = "process_group_rss_limit"
                elif pressure is not None and pressure >= 4:
                    reason = "critical_system_memory_pressure"
                if reason:
                    stop_group(process)
                    break
                time.sleep(args.interval)
        except BaseException as exc:
            reason = type(exc).__name__
            stop_group(process)
        finally:
            code = process.wait()
            record = {
                "exit_code": code,
                "status": "completed" if code == 0 and reason is None else "failed",
                "stop_reason": reason,
                "peak_process_group_rss_kib": peak,
                "max_rss_gib": args.max_rss_gib,
                "highest_macos_pressure_level": highest_pressure,
                "poll_interval_seconds": args.interval,
                "elapsed_seconds": time.monotonic() - start,
            }
            args.record.write_text(json.dumps(record, indent=2) + "\n")
            print(json.dumps(record, indent=2), flush=True)
    return 1 if reason else code


if __name__ == "__main__":
    raise SystemExit(main())
