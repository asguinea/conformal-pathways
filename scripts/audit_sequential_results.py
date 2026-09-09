"""Post-run read-only audits; this does not modify the frozen experiment."""

import gzip
import json
from collections import defaultdict
from pathlib import Path

import pandas as pd

from conformal_pathways.benchmarks.provenance import digest
from conformal_pathways.benchmarks.sequential_runner import flatten_metrics

root = Path("artifacts/batch3-sequential-v1/primary/real")
execution = json.loads((root / "execution.json").read_text())
assert execution["status"] == "complete"
records = [json.loads(p.read_text()) for p in (root / "runs").glob("*.json")]
old_root = Path("artifacts/batch3-v2/primary/real")
old_records = {
    digest(r["context"]): r
    for r in (json.loads(p.read_text()) for p in (old_root / "runs").glob("*.json"))
}
groups = defaultdict(dict)
matched_baselines = 0
for record in records:
    context = record["context"]
    report = json.loads(gzip.decompress((root / record["report_path"]).read_bytes()))
    if context["mechanism"] == "entry_only":
        previous = old_records[digest({k: v for k, v in context.items() if k != "mechanism"})]
        assert flatten_metrics(report, True) == flatten_metrics(previous["metrics"], True)
        assert record["model_sha256"] == previous["model_sha256"]
        assert report["calibration"] == previous["metrics"]["calibration"]
        assert {k: v for k, v in report.items() if k != "run_id"} == {
            k: v for k, v in previous["metrics"].items() if k != "run_id"
        }
        before = pd.read_csv(
            old_root / previous["cases_path"], dtype={"sample_id": str, "group_id": str}
        )
        after = pd.read_csv(
            root / "entry_cases" / f"{record['key']}.csv", dtype={"sample_id": str, "group_id": str}
        )
        # The unpruned invocation now receives a harmless default alpha; the
        # exported scientific alpha is still null and thresholds are infinite.
        pd.testing.assert_frame_equal(
            before.drop(columns=["run_id", "alpha"]).sort_index(axis=1),
            after.drop(columns=["run_id", "alpha"]).sort_index(axis=1),
            check_exact=True,
        )
        matched_baselines += 1
    else:
        key = digest({k: v for k, v in context.items() if k != "mechanism"})
        groups[key][context["mechanism"]] = report
first_decisions = 0
for arms in groups.values():
    reference = arms["perfect"]
    first = {
        c["sample_id"]: {p: e["trace"][0] for p, e in c["executions"].items()}
        for c in reference["cases"]
    }
    for name, report in arms.items():
        assert report["filter"]["thresholds"][0] == reference["filter"]["thresholds"][0]
        actual = {
            c["sample_id"]: {p: e["trace"][0] for p, e in c["executions"].items()}
            for c in report["cases"]
        }
        assert actual == first
        first_decisions += sum(len(policies) for policies in actual.values())
        for case in report["cases"]:
            for execution in case["executions"].values():
                trace = execution["trace"]
                for index, event in enumerate(trace):
                    if event["event"] == "result":
                        assert index > 0 and trace[index - 1]["event"] == "decision"
                        assert trace[index - 1]["chosen"]["name"] == event["result"]["action_name"]
result = {
    "status": "passed",
    "unchanged_legacy_real_baselines": matched_baselines,
    "legacy_full_metrics_and_case_fingerprints": "exact by named columns; invocation ID and unused CSV alpha excluded",
    "initial_policy_decisions_checked": first_decisions,
    "initial_decisions_and_thresholds_identical_across_diagnostic_mechanisms": True,
    "result_delivery_follows_diagnostic_commitment": True,
}
Path("artifacts/batch3-sequential-v1/primary-audit.json").write_text(
    json.dumps(result, indent=2) + "\n"
)
print(json.dumps(result, indent=2))
