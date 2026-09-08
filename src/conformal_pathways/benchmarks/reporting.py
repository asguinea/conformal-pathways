"""Regenerate public aggregates from complete, integrity-checked run records."""

from __future__ import annotations

import csv
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
    aggregate_topk_safety_metrics,
)
from conformal_pathways.features.cache import sha256_file

from .provenance import digest, verify_files, write_json
from .runner import METRICS, expected_contexts
from .statistics import paired_summary, summarize_values


def read_bundle(path, reaggregate=True):
    root = Path(path)
    execution = json.loads((root / "execution.json").read_text())
    if execution["status"] != "complete":
        raise ValueError("only complete experiments may be reported")
    verify_files(root, execution["files"])
    records = [json.loads(p.read_text()) for p in sorted((root / "runs").glob("*.json"))]
    expected = expected_contexts(execution["protocol"], execution["suite"])
    if sorted(digest(r["context"]) for r in records) != sorted(map(digest, expected)):
        raise ValueError("missing, duplicated, or unexpected comparison")
    for record in records:
        if (
            record["key"] != digest(record["context"])[:20]
            or record["cases_path"] not in execution["files"]
            or sha256_file(root / record["cases_path"]) != record["cases_sha256"]
        ):
            raise ValueError("run or case identity mismatch")
        if reaggregate:
            frame = pd.read_csv(
                root / record["cases_path"], dtype={"sample_id": str, "group_id": str}
            )
            rows = frame.astype(object).where(frame.notna(), None).to_dict("records")
            calculated = {
                **aggregate_metrics(rows),
                **aggregate_chosen_path_metrics(rows),
                **aggregate_topk_safety_metrics(rows, execution["protocol"]["selection_policies"]),
            }
            groups = defaultdict(list)
            for row in rows:
                groups[row["group_id"]].append(row["oracle_retained"])
            outcomes = [all(v) if all(x is not None for x in v) else None for v in groups.values()]
            calculated.update(_mean_record(outcomes, "group_oracle_retained"))
            for key, value in calculated.items():
                saved = record["metrics"][key]
                if isinstance(value, (int, float)):
                    if saved is None or not math.isclose(value, saved, rel_tol=0, abs_tol=1e-12):
                        raise ValueError(f"aggregate disagrees with case export: {key}")
                elif value != saved:
                    raise ValueError(f"aggregate disagrees with case export: {key}")
    return execution, records


def compact_record(record):
    metrics = record["metrics"]
    row = {
        "key": record["key"],
        **record["context"],
        "run_id": metrics["run_id"],
        "input_sha256": metrics["input_sha256"],
        "model_sha256": record["model_sha256"],
        "cases_sha256": record["cases_sha256"],
        "n_test": metrics["n_test"],
        "n_rule_evaluable": metrics["n_rule_evaluable"],
        "n_cal_groups_evaluable": metrics["n_cal_groups_evaluable"],
        "n_cal_groups_excluded": metrics["n_cal_groups_excluded"],
        "thresholds": metrics["calibration"]["thresholds"],
    }
    for metric in METRICS:
        row[metric] = metrics[metric]
        for suffix in ("__numerator", "__denominator", "__unavailable"):
            row[metric + suffix] = metrics[metric + suffix]
    return row


def aggregate_records(records, confidence=0.95):
    grouped = defaultdict(list)
    for row in records:
        key = tuple(row[k] for k in ("suite", "cohort", "workflow", "model", "variant", "alpha"))
        grouped[key].append(row)
    summaries = []
    for key, rows in sorted(grouped.items(), key=lambda item: str(item[0])):
        if len({r["repeat"] for r in rows}) != len(rows):
            raise ValueError("duplicate repetition in summary")
        context = dict(
            zip(("suite", "cohort", "workflow", "model", "variant", "alpha"), key, strict=True)
        )
        independent = context["suite"] == "synthetic"
        for metric in METRICS:
            bounds = (0.0, 18.0) if metric == "set_size" else (0.0, 1.0)
            statistic = summarize_values(
                [r[metric] for r in rows],
                confidence,
                bounds,
                binary=metric == "group_oracle_retained",
                independent=independent,
            )
            summaries.append(
                {
                    **context,
                    "metric": metric,
                    **statistic,
                    "estimand": "mean_of_independent_repetition_metrics"
                    if independent
                    else "mean_across_fixed_test_split_sensitivity_runs",
                }
            )
    paired = []
    for key, rows in sorted(grouped.items(), key=lambda item: str(item[0])):
        suite, cohort, workflow, model, variant, alpha = key
        if variant != "main":
            continue
        for comparator in ("model_only", "rules_only", "no_conformal"):
            other_key = (
                suite,
                cohort,
                workflow,
                model,
                comparator,
                None if comparator == "no_conformal" else alpha,
            )
            if other_key not in grouped:
                raise ValueError("missing paired baseline")
            other = grouped[other_key]
            if any(
                r["input_sha256"]
                != {q["repeat"]: q["input_sha256"] for q in other}.get(r["repeat"])
                or r["model_sha256"]
                != {q["repeat"]: q["model_sha256"] for q in other}.get(r["repeat"])
                for r in rows
            ):
                raise ValueError("paired variants do not share inputs and fitted model")
            for metric in METRICS:
                bounds = (0.0, 18.0) if metric == "set_size" else (0.0, 1.0)
                statistic = paired_summary(
                    {r["repeat"]: r[metric] for r in rows},
                    {r["repeat"]: r[metric] for r in other},
                    confidence,
                    bounds,
                    independent=suite == "synthetic",
                )
                paired.append(
                    {
                        "suite": suite,
                        "cohort": cohort,
                        "workflow": workflow,
                        "model": model,
                        "alpha": alpha,
                        "contrast": f"main - {comparator}",
                        "metric": metric,
                        **statistic,
                    }
                )
    return summaries, paired


def write_csv(path, rows):
    if not rows:
        raise ValueError("cannot export empty records")
    with Path(path).open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    k: json.dumps(v, sort_keys=True) if isinstance(v, (dict, list)) else v
                    for k, v in row.items()
                }
            )


def make_figure(summary, out_path):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "svg.hashsalt": "conformal-pathways-batch3-v1",
        }
    )
    figure, axes = plt.subplots(2, 2, figsize=(10, 7), layout="constrained")
    colors = {"main": "#0072B2", "model_only": "#D55E00", "rules_only": "#009E73"}
    for column, workflow in enumerate(("dr_workflow", "glaucoma_workflow")):
        for variant, color in colors.items():
            for row_index, metric in enumerate(("group_oracle_retained", "set_size")):
                rows = sorted(
                    [
                        r
                        for r in summary
                        if r["suite"] == "synthetic"
                        and r["cohort"] == "iid"
                        and r["model"] == "known_signal"
                        and r["workflow"] == workflow
                        and r["variant"] == variant
                        and r["metric"] == metric
                    ],
                    key=lambda r: r["alpha"],
                )
                x = [r["alpha"] for r in rows]
                y = [r["mean"] for r in rows]
                errors = [
                    [max(0.0, r["mean"] - r["interval_low"]) for r in rows],
                    [max(0.0, r["interval_high"] - r["mean"]) for r in rows],
                ]
                axes[row_index, column].errorbar(
                    x,
                    y,
                    yerr=errors,
                    label=variant,
                    color=color,
                    marker="o",
                    capsize=3,
                    linewidth=1.5,
                )
        axes[0, column].plot(
            [0.05, 0.1, 0.2], [0.95, 0.9, 0.8], color="#444444", linestyle="--", label="1 − alpha"
        )
        axes[0, column].set_ylim(0, 1.025)
        axes[0, column].set_title(
            "DR-style toy workflow" if column == 0 else "Glaucoma-style toy workflow"
        )
        axes[1, column].axhline(18, color="#777777", linestyle=":", label="unpruned (18)")
        axes[1, column].set_ylim(0, 19)
        for ax in axes[:, column]:
            ax.set_xticks([0.05, 0.1, 0.2])
            ax.set_xlabel("Total alpha")
            ax.grid(alpha=0.2)
    axes[0, 0].set_ylabel("Group reference-path inclusion")
    axes[1, 0].set_ylabel("Mean retained paths per case")
    axes[0, 1].legend(loc="lower left", frameon=False, fontsize=8)
    figure.suptitle("Independent synthetic repetitions • known signal model", fontsize=13)
    figure.savefig(out_path, metadata={"Date": None})
    figure.savefig(Path(out_path).with_suffix(".png"), dpi=150)
    plt.close(figure)


def render_report(summary, paired, destination):
    lines = [
        "# Recorded experiment results",
        "",
        "Generated from the complete records in `trials.jsonl`. All outcomes refer to toy rules.",
        "Synthetic intervals use independent repetitions. Real-data ranges describe five training/calibration splits with a fixed official test set; they are not confidence intervals.",
        "",
        "## Primary synthetic setting (alpha = 0.1, known signal model)",
        "",
        "| Workflow | Variant | Group reference inclusion [95% Wilson interval] | Mean paths |",
        "| --- | --- | --- | --- |",
    ]

    def lookup(suite, cohort, workflow, model, variant, alpha, metric):
        return next(
            r
            for r in summary
            if all(
                r[k] == v
                for k, v in locals_filter(
                    suite, cohort, workflow, model, variant, alpha, metric
                ).items()
            )
        )

    for workflow in ("dr_workflow", "glaucoma_workflow"):
        for variant in ("main", "model_only", "rules_only", "no_conformal"):
            alpha = None if variant == "no_conformal" else 0.1
            coverage = lookup(
                "synthetic",
                "iid",
                workflow,
                "known_signal",
                variant,
                alpha,
                "group_oracle_retained",
            )
            size = lookup("synthetic", "iid", workflow, "known_signal", variant, alpha, "set_size")
            lines.append(
                f"| {workflow.removesuffix('_workflow')} | {variant} | {coverage['mean']:.3f} [{coverage['interval_low']:.3f}, {coverage['interval_high']:.3f}] | {size['mean']:.2f} |"
            )
    lines.extend(
        [
            "",
            "![Synthetic coverage and set size](synthetic.svg)",
            "",
            "The complete tables also contain class-prior controls, missing-label and tiny-calibration scenarios, paired differences, selection violation rates, abstentions, and unavailable counts. Mean and paired-difference intervals use conservative Hoeffding bounds over independent repetitions. Intervals are pointwise; there is no multiplicity-adjusted superiority claim.",
            "",
            "## Real-data descriptive checks (alpha = 0.1, frozen ResNet-50 features)",
            "",
            "| Dataset | Variant | Reference inclusion mean (seed range) | Mean paths | Selected toy violation, observed-rules-first |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    if any(r["suite"] == "real" for r in summary):
        for cohort, workflow in (("idrid", "dr_workflow"), ("rimone", "glaucoma_workflow")):
            for variant in ("main", "model_only", "rules_only", "no_conformal"):
                alpha = None if variant == "no_conformal" else 0.1
                c = lookup(
                    "real",
                    cohort,
                    workflow,
                    "resnet50_logreg",
                    variant,
                    alpha,
                    "group_oracle_retained",
                )
                size = lookup(
                    "real", cohort, workflow, "resnet50_logreg", variant, alpha, "set_size"
                )
                risk = lookup(
                    "real",
                    cohort,
                    workflow,
                    "resnet50_logreg",
                    variant,
                    alpha,
                    "chosen_unsafe_rate__observed_rules_first",
                )
                value = "unavailable" if risk["mean"] is None else f"{risk['mean']:.3f}"
                lines.append(
                    f"| {cohort} | {variant} | {c['mean']:.3f} ({c['observed_min']:.3f}–{c['observed_max']:.3f}) | {size['mean']:.2f} | {value} |"
                )
    else:
        lines.append("| Pending: external images must be available offline | — | — | — | — |")
    lines.extend(
        [
            "",
            "Patient linkage and dataset exchangeability are unverified. These image-level descriptive results do not establish a patient-level coverage guarantee, treatment benefit, or clinical safety. The reference target uses retrospective proxies; no diagnostic response is observed.",
            "",
            "Reproduction instructions, input provenance, exclusions, and dataset acknowledgments are in [the protocol](../../docs/experiment-protocol.md) and [dataset evidence](../../docs/dataset-evidence.md).",
        ]
    )
    Path(destination).write_text("\n".join(lines) + "\n")


def locals_filter(suite, cohort, workflow, model, variant, alpha, metric):
    return {
        "suite": suite,
        "cohort": cohort,
        "workflow": workflow,
        "model": model,
        "variant": variant,
        "alpha": alpha,
        "metric": metric,
    }


def publish_bundles(paths, destination, allow_pending_real=False):
    executions = []
    compact = []
    for path in paths:
        execution, records = read_bundle(path)
        executions.append(execution)
        compact.extend(map(compact_record, records))
    suites = sorted(e["suite"] for e in executions)
    if suites != ["real", "synthetic"] and not (allow_pending_real and suites == ["synthetic"]):
        raise ValueError(
            "report requires complete suites; explicitly allow pending real data for a synthetic-only report"
        )
    if len({e["freeze"]["source_sha256"] for e in executions}) != 1:
        raise ValueError("suites use different frozen implementations")
    compact.sort(key=lambda r: r["key"])
    summary, paired = aggregate_records(
        compact, executions[0]["protocol"]["statistics"]["confidence"]
    )
    out = Path(destination)
    if out.exists() and any(out.iterdir()):
        raise ValueError("use a new empty evidence directory")
    out.mkdir(parents=True, exist_ok=True)
    (out / "trials.jsonl").write_text(
        "".join(
            json.dumps(r, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
            for r in compact
        )
    )
    write_json(out / "summary.json", summary)
    write_csv(out / "summary.csv", summary)
    write_csv(out / "paired.csv", paired)
    make_figure(summary, out / "synthetic.svg")
    render_report(summary, paired, out / "README.md")
    record = {
        "schema_version": 1,
        "freeze": executions[0]["freeze"],
        "protocol": executions[0]["protocol"],
        "pending_suites": ["real"] if suites == ["synthetic"] else [],
        "suites": [
            {
                "suite": e["suite"],
                "records": e["actual_records"],
                "environment": e["environment"],
                "elapsed_seconds": e["elapsed_seconds"],
                "detail": e["detail"],
                "input_lock": e.get("input_lock"),
            }
            for e in executions
        ],
        "files": {p.name: sha256_file(p) for p in sorted(out.iterdir()) if p.is_file()},
    }
    write_json(out / "evidence.json", record)
    return {"records": len(compact), "summary_rows": len(summary), "paired_rows": len(paired)}


def verify_public_evidence(path):
    root = Path(path)
    evidence = json.loads((root / "evidence.json").read_text())
    verify_files(root, evidence["files"])
    rows = [json.loads(line) for line in (root / "trials.jsonl").read_text().splitlines()]
    suites = sorted(s["suite"] for s in evidence["suites"])
    if suites not in (["synthetic"], ["real", "synthetic"]) or evidence["pending_suites"] != (
        ["real"] if suites == ["synthetic"] else []
    ):
        raise ValueError("invalid completed/pending suite declaration")
    expected = [c for suite in suites for c in expected_contexts(evidence["protocol"], suite)]
    context_keys = ("suite", "cohort", "workflow", "model", "repeat", "seed", "variant", "alpha")
    if sorted(digest({k: r[k] for k in context_keys}) for r in rows) != sorted(
        map(digest, expected)
    ):
        raise ValueError("public evidence does not contain the complete design")
    summary, paired = aggregate_records(rows, evidence["protocol"]["statistics"]["confidence"])
    if summary != json.loads((root / "summary.json").read_text()):
        raise ValueError("public summary cannot be regenerated")
    # CSV exports are regenerated in memory so stale paired results cannot pass.
    import io

    for name, records in [("summary.csv", summary), ("paired.csv", paired)]:
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
        if stream.getvalue().encode() != (root / name).read_bytes():
            raise ValueError(f"public table cannot be regenerated: {name}")
    return {
        "status": "passed",
        "trial_records": len(rows),
        "summary_rows": len(summary),
        "paired_rows": len(paired),
    }


def compare_bundles(first, second):
    a, records_a = read_bundle(first)
    b, records_b = read_bundle(second)
    if a["suite"] != b["suite"] or a["freeze"] != b["freeze"]:
        raise ValueError("reproduction uses a different frozen protocol")
    if a.get("input_lock") != b.get("input_lock"):
        raise ValueError("reproduction uses different sealed data inputs")
    lookup = {r["key"]: r for r in records_b}
    exact = True
    for left in records_a:
        right = lookup[left["key"]]
        exact = exact and left == right
        ma, mb = dict(left["metrics"]), dict(right["metrics"])
        for value in (ma, mb):
            value.pop("run_id")
            value.pop("calibration")
        if ma != mb:
            raise ValueError("reproduced metrics or splits differ")
        ta, tb = left["metrics"]["calibration"], right["metrics"]["calibration"]
        for t, value in ta["thresholds"].items():
            other = tb["thresholds"][t]
            if isinstance(value, str):
                if other != value:
                    raise ValueError("reproduced threshold differs")
            elif not math.isclose(
                value, other, rel_tol=0, abs_tol=a["protocol"]["reproduction"]["threshold_atol"]
            ):
                raise ValueError("reproduced threshold differs")
        for key in ("stage_budgets", "score_weights", "group_ids"):
            if ta[key] != tb[key]:
                raise ValueError("reproduced calibration differs")
        # Membership/outcomes must agree per case, not merely in aggregate.
        ca = pd.read_csv(
            Path(first) / left["cases_path"], dtype={"sample_id": str, "group_id": str}
        ).drop(columns="run_id")
        cb = pd.read_csv(
            Path(second) / right["cases_path"], dtype={"sample_id": str, "group_id": str}
        ).drop(columns="run_id")
        pd.testing.assert_frame_equal(ca, cb, check_exact=True)
    for path in sorted((Path(first) / "predictions").glob("*.json")):
        left = json.loads(path.read_text())
        right = json.loads((Path(second) / "predictions" / path.name).read_text())
        if left.keys() != right.keys() or any(left[k].keys() != right[k].keys() for k in left):
            raise ValueError("reproduced prediction IDs or classes differ")
        for key in left:
            np.testing.assert_allclose(
                list(left[key].values()),
                list(right[key].values()),
                rtol=0,
                atol=a["protocol"]["reproduction"]["probability_atol"],
            )
    feature_comparison = []
    for path in sorted((Path(first) / "embeddings").glob("*.npy")):
        other = Path(second) / "embeddings" / path.name
        x, y = np.load(path, allow_pickle=False), np.load(other, allow_pickle=False)
        np.testing.assert_allclose(
            x,
            y,
            atol=a["protocol"]["reproduction"]["feature_atol"],
            rtol=a["protocol"]["reproduction"]["feature_rtol"],
        )
        feature_comparison.append(
            {
                "dataset": path.stem,
                "exact": bool(np.array_equal(x, y)),
                "max_abs_difference": float(np.max(np.abs(x - y))),
            }
        )
    return {
        "status": "passed",
        "suite": a["suite"],
        "records": len(records_a),
        "metrics_and_cases": "exact",
        "probabilities": "within_declared_tolerance",
        "all_scientific_records_exact": exact,
        "features": feature_comparison,
    }
