"""Audit local traces, compare fresh runs, and regenerate compact public evidence."""

from __future__ import annotations

import csv
import gzip
import io
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

from conformal_pathways.eval.metrics import (
    _mean_record,
    aggregate_chosen_path_metrics,
    aggregate_metrics,
)
from conformal_pathways.features.cache import sha256_file
from conformal_pathways.sequential.evaluation import aggregate_cases

from .provenance import digest, verify_files, write_json
from .sequential_design import expected_contexts
from .sequential_runner import METRICS, flatten_metrics, scientific_report
from .statistics import paired_summary, summarize_values

CONTEXT = (
    "suite",
    "cohort",
    "workflow",
    "repeat",
    "seed",
    "model",
    "mechanism",
    "variant",
    "alpha",
)
GROUP = ("suite", "cohort", "workflow", "model", "mechanism", "variant", "alpha")


def read_bundle(path):
    root = Path(path)
    execution = json.loads((root / "execution.json").read_text())
    if execution["status"] != "complete":
        raise ValueError("only complete suites may be reported")
    verify_files(root, execution["files"])
    records = [json.loads(p.read_text()) for p in sorted((root / "runs").glob("*.json"))]
    expected = expected_contexts(execution["protocol"], execution["suite"])
    if sorted(digest(r["context"]) for r in records) != sorted(map(digest, expected)):
        raise ValueError("missing, duplicate, or unexpected experiment records")
    for record in records:
        if (
            record["key"] != digest(record["context"])[:20]
            or record["report_path"] not in execution["files"]
        ):
            raise ValueError("invalid run identity")
        report = json.loads(gzip.decompress((root / record["report_path"]).read_bytes()))
        entry = record["context"]["mechanism"] == "entry_only"
        if not entry:
            if (
                digest({k: v for k, v in report.items() if k != "report_sha256"})
                != report["report_sha256"]
            ):
                raise ValueError("report digest mismatch")
            if (
                aggregate_cases(report["cases"], execution["protocol"]["selection_policies"])
                != report["metrics"]
            ):
                raise ValueError("sequential metrics disagree with case export")
        else:
            case = root / "entry_cases" / f"{record['key']}.csv"
            if str(case.relative_to(root)) not in execution["files"]:
                raise ValueError("entry case export is absent from file inventory")
            frame = pd.read_csv(case, dtype={"sample_id": str, "group_id": str})
            rows = frame.astype(object).where(frame.notna(), None).to_dict("records")
            calculated = {**aggregate_metrics(rows), **aggregate_chosen_path_metrics(rows)}
            groups = defaultdict(list)
            for row in rows:
                groups[row["group_id"]].append(row["oracle_retained"])
            calculated.update(
                _mean_record(
                    [all(v) if all(x is not None for x in v) else None for v in groups.values()],
                    "group_oracle_retained",
                )
            )
            for key, value in calculated.items():
                if isinstance(value, (int, float)):
                    if report[key] is None or not math.isclose(
                        value, report[key], rel_tol=0, abs_tol=1e-12
                    ):
                        raise ValueError("entry metrics disagree with case export")
                elif value != report[key]:
                    raise ValueError("entry metrics disagree with case export")
        if (
            flatten_metrics(report, entry) != record["metrics"]
            or digest(scientific_report(report, entry)) != record["scientific_sha256"]
        ):
            raise ValueError("run disagrees with its scientific report")
    return execution, records


def compare(first, second):
    a, left = read_bundle(first)
    b, right = read_bundle(second)
    if (
        a["suite"] != b["suite"]
        or a["freeze"] != b["freeze"]
        or a.get("input_lock") != b.get("input_lock")
    ):
        raise ValueError("frozen protocol or sealed inputs differ")
    if left != right:
        raise ValueError("scientific records, predictions, calibration, cases, or traces differ")
    features = []
    for path in sorted((Path(first) / "embeddings").glob("*.npy")):
        x = np.load(path, allow_pickle=False)
        y = np.load(Path(second) / "embeddings" / path.name, allow_pickle=False)
        if not np.array_equal(x, y):
            raise ValueError("fresh features are not bit-for-bit identical")
        features.append({"dataset": path.stem, "exact": True, "max_abs_difference": 0.0})
    return {
        "status": "passed",
        "suite": a["suite"],
        "records": len(left),
        "scientific_records": "exact",
        "cases_traces_calibration_predictions": "exact",
        "excluded_fields": a["protocol"]["reproduction"]["excluded_report_fields"],
        "features": features,
    }


def compact(record):
    result = {"key": record["key"], **record["context"]}
    for key in (
        "input_sha256",
        "model_sha256",
        "scientific_sha256",
        "scenario_sha256",
        "n_test",
        "n_cal_groups_evaluable",
        "n_cal_groups_excluded",
        "thresholds",
    ):
        result[key] = record[key]
    for metric in METRICS:
        for field, value in record["metrics"][metric].items():
            result[metric if field == "value" else f"{metric}__{field}"] = value
    return result


def aggregate(records, confidence=0.95):
    grouped = defaultdict(list)
    for row in records:
        grouped[tuple(row[k] for k in GROUP)].append(row)
    summary, paired = [], []
    for key, rows in sorted(grouped.items(), key=lambda item: str(item[0])):
        if len({r["repeat"] for r in rows}) != len(rows):
            raise ValueError("duplicate repetition")
        context = dict(zip(GROUP, key, strict=True))
        for metric in METRICS:
            statistic = summarize_values(
                [r[metric] for r in rows],
                confidence,
                (0.0, 18.0) if metric == "realized_set_size" else (0.0, 1.0),
                binary=metric == "group_reference_retained",
                independent=context["suite"] == "synthetic",
            )
            summary.append({**context, "metric": metric, **statistic})
        if context["variant"] != "main":
            continue
        comparators = [
            (context["mechanism"], variant)
            for variant in ("model_only", "rules_only", "no_conformal")
        ]
        if context["mechanism"] == "perfect":
            comparators += [
                (name, "main")
                for name in ("unavailable", "missing20", "error20", "entry_only")
                if (*key[:4], name, "main", key[-1]) in grouped
            ]
        for mechanism, variant in comparators:
            other_key = (
                *key[:4],
                mechanism,
                variant,
                None if variant == "no_conformal" else key[-1],
            )
            if other_key not in grouped:
                raise ValueError("missing paired comparator")
            others = {r["repeat"]: r for r in grouped[other_key]}
            if set(others) != {r["repeat"] for r in rows}:
                raise ValueError("paired repetitions differ")
            for row in rows:
                if any(
                    row[k] != others[row["repeat"]][k] for k in ("input_sha256", "model_sha256")
                ):
                    raise ValueError("paired arms do not share inputs and fitted predictions")
                if (
                    mechanism == context["mechanism"]
                    and row["scenario_sha256"] != others[row["repeat"]]["scenario_sha256"]
                ):
                    raise ValueError("paired filter variants use different diagnostic results")
            for metric in METRICS:
                statistic = paired_summary(
                    {r["repeat"]: r[metric] for r in rows},
                    {r: value[metric] for r, value in others.items()},
                    confidence,
                    (0.0, 18.0) if metric == "realized_set_size" else (0.0, 1.0),
                    independent=context["suite"] == "synthetic",
                )
                paired.append(
                    {
                        **context,
                        "comparator_mechanism": mechanism,
                        "comparator_variant": variant,
                        "metric": metric,
                        **statistic,
                    }
                )
    return summary, paired


def csv_bytes(rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode()


def figure(summary, destination):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    names = ["perfect", "missing20", "error20", "unavailable", "entry_only"]
    labels = [
        "Perfect\nproxy",
        "20%\nunavailable",
        "20%\nincorrect",
        "No\nresults",
        "Entry-only\nbaseline",
    ]
    fig, axes = plt.subplots(2, 2, figsize=(12, 7), layout="constrained")
    for row, cohort in enumerate(("idrid", "rimone")):
        for col, metric in enumerate(("reference_retained", "violation_score")):
            ax = axes[row, col]
            for variant, offset, color in (
                ("main", -0.08, "#0072B2"),
                ("model_only", 0.08, "#D55E00"),
            ):
                selected = [
                    next(
                        s
                        for s in summary
                        if s["suite"] == "real"
                        and s["cohort"] == cohort
                        and s["model"] == "resnet50_logreg"
                        and s["variant"] == variant
                        and s["mechanism"] == name
                        and s["metric"] == metric
                    )
                    for name in names
                ]
                ax.errorbar(
                    np.arange(5) + offset,
                    [s["mean"] for s in selected],
                    yerr=[
                        [s["mean"] - s["observed_min"] for s in selected],
                        [s["observed_max"] - s["mean"] for s in selected],
                    ],
                    fmt="o",
                    capsize=3,
                    color=color,
                    label=variant,
                )
            ax.set_xticks(range(5), labels)
            ax.set_ylim(-0.03, 1.03)
            ax.set_title(
                f"{cohort.upper()} · "
                + ("reference retention" if col == 0 else "selected toy violation")
            )
            ax.grid(axis="y", alpha=0.2)
            if col == 0:
                ax.axhline(0.9, color="gray", linestyle=":", label="nominal reference level")
            ax.spines[["top", "right"]].set_visible(False)
    axes[0, 1].legend(frameon=False)
    fig.suptitle(
        "Simulated diagnostic information · fixed test images\nMeans and seed ranges, not confidence intervals",
        fontsize=13,
    )
    fig.savefig(destination, dpi=160)
    plt.close(fig)


def render(summary, destination):
    lines = [
        "# Result-aware experiment evidence",
        "",
        "Results use simulated diagnostic proxy responses and illustrative toy predicates. They are not clinical safety or treatment-outcome measurements.",
        "",
        "## Primary synthetic setting",
        "",
        "Known-signal model, main filter, alpha 0.1. Each repetition has one new independent two-member test group. Intervals are pointwise 95% Wilson intervals for group retention.",
        "",
        "| Workflow | Diagnostic information | Group retention [interval] | Mean realized sequences | Selected violation: score / rules | Abstention: score / rules |",
        "| --- | --- | --- | --- | --- | --- |",
    ]

    def get(suite, cohort, model, mechanism, metric):
        return next(
            s
            for s in summary
            if s["suite"] == suite
            and s["cohort"] == cohort[0]
            and s["workflow"] == cohort[1]
            and s["model"] == model
            and s["mechanism"] == mechanism
            and s["variant"] == "main"
            and s["metric"] == metric
        )

    def fmt(value):
        return "unavailable" if value is None else f"{value:.3f}"

    for workflow in ("dr_workflow", "glaucoma_workflow"):
        for name in ("perfect", "missing20", "error20", "unavailable", "entry_only"):

            def at(metric):
                return get("synthetic", ("iid", workflow), "known_signal", name, metric)

            retention = at("group_reference_retained")
            lines.append(
                f"| {workflow.removesuffix('_workflow')} | {name} | {retention['mean']:.3f} [{retention['interval_low']:.3f}, {retention['interval_high']:.3f}] | {at('realized_set_size')['mean']:.2f} | {fmt(at('violation_score')['mean'])} / {fmt(at('violation_rules')['mean'])} | {fmt(at('abstention_score')['mean'])} / {fmt(at('abstention_rules')['mean'])} |"
            )
    lines += [
        "",
        "## Real-image descriptive simulation",
        "",
        "Frozen ResNet-50 features and logistic regression, main filter, alpha 0.1. Values are means across five training/calibration splits sharing the same held-out images; seed ranges in the figure are not confidence intervals.",
        "",
        "| Dataset | Diagnostic information | Reference retention | Mean realized sequences | Selected violation: score / rules | Abstention: score / rules | Test ordered: score / rules |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for cohort, workflow in (("idrid", "dr_workflow"), ("rimone", "glaucoma_workflow")):
        for name in ("perfect", "missing20", "error20", "unavailable", "entry_only"):

            def at(metric):
                return get("real", (cohort, workflow), "resnet50_logreg", name, metric)["mean"]

            lines.append(
                f"| {cohort} | {name} | {fmt(at('reference_retained'))} | {at('realized_set_size'):.2f} | {fmt(at('violation_score'))} / {fmt(at('violation_rules'))} | {fmt(at('abstention_score'))} / {fmt(at('abstention_rules'))} | {fmt(at('diagnostic_score'))} / {fmt(at('diagnostic_rules'))} |"
            )
    lines += [
        "",
        "![Real-image descriptive simulation](real-results.png)",
        "",
        "`score` means the stage-local min-stage-score selector for sequential arms and the complete-path min-total-score selector for entry-only. `rules` also operates at different decision levels. Comparisons to entry-only therefore change more than diagnostic information. The unavailable-result sequential control isolates information availability while preserving the stage-local selector.",
        "",
        "Selected violation rates condition on evaluable completed selections. Always read them alongside abstention and test-use rates. They are not an overall harm rate. Realized sequence counts are retrospective projections, not numbers of deployable policies.",
        "",
        "Full tables include all variants, class-prior controls, truth-label missingness, tiny calibration, denominators, unavailable counts, and paired differences. Synthetic mean/difference intervals use conservative independent-repetition Hoeffding bounds; there is no multiplicity-adjusted superiority claim. Real uncertainty is descriptive only.",
        "",
        "See [the prospective protocol](../../docs/sequential-experiment-protocol.md), [method](../../docs/sequential-method.md), and [dataset provenance](../../docs/dataset-evidence.md). Public files exclude raw real-image cases, labels, images, and model artifacts.",
    ]
    Path(destination).write_text("\n".join(lines) + "\n")


def publish(paths, destination):
    executions, rows = [], []
    for path in paths:
        execution, records = read_bundle(path)
        executions.append(execution)
        rows.extend(compact(r) for r in records)
    if (
        sorted(e["suite"] for e in executions) != ["real", "synthetic"]
        or len({e["freeze"]["source_sha256"] for e in executions}) != 1
    ):
        raise ValueError("one complete matching suite of each kind is required")
    rows.sort(key=lambda r: r["key"])
    summary, paired = aggregate(rows, executions[0]["protocol"]["statistics"]["confidence"])
    out = Path(destination)
    if out.exists() and any(out.iterdir()):
        raise ValueError("use a new empty evidence directory")
    out.mkdir(parents=True, exist_ok=True)
    (out / "trials.jsonl").write_text(
        "".join(json.dumps(r, sort_keys=True, allow_nan=False) + "\n" for r in rows)
    )
    write_json(out / "summary.json", summary)
    (out / "summary.csv").write_bytes(csv_bytes(summary))
    (out / "paired.csv").write_bytes(csv_bytes(paired))
    figure(summary, out / "real-results.png")
    render(summary, out / "README.md")
    write_json(
        out / "evidence.json",
        {
            "protocol": executions[0]["protocol"],
            "freeze": executions[0]["freeze"],
            "suites": [
                {
                    k: e[k]
                    for k in ("suite", "actual_records", "environment", "elapsed_seconds", "detail")
                }
                for e in executions
            ],
            "files": {p.name: sha256_file(p) for p in sorted(out.iterdir()) if p.is_file()},
        },
    )
    return {"records": len(rows), "summary_rows": len(summary), "paired_rows": len(paired)}


def verify_public(path):
    root = Path(path)
    evidence = json.loads((root / "evidence.json").read_text())
    verify_files(root, evidence["files"])
    if sorted(e["suite"] for e in evidence["suites"]) != ["real", "synthetic"]:
        raise ValueError("both completed suites are required")
    rows = [json.loads(line) for line in (root / "trials.jsonl").read_text().splitlines()]
    expected = [
        c for suite in ("synthetic", "real") for c in expected_contexts(evidence["protocol"], suite)
    ]
    if sorted(digest({k: r[k] for k in CONTEXT}) for r in rows) != sorted(map(digest, expected)):
        raise ValueError("incomplete public design")
    summary, paired = aggregate(rows, evidence["protocol"]["statistics"]["confidence"])
    if summary != json.loads((root / "summary.json").read_text()):
        raise ValueError("summary does not regenerate")
    for name, values in (("summary.csv", summary), ("paired.csv", paired)):
        if csv_bytes(values) != (root / name).read_bytes():
            raise ValueError("table does not regenerate")
    return {
        "status": "passed",
        "records": len(rows),
        "summary_rows": len(summary),
        "paired_rows": len(paired),
    }
