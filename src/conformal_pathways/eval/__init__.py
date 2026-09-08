"""Experimental evaluation APIs, loaded on demand to isolate optional dependencies."""

from importlib import import_module

_EXPORTS = {
    "run_ablation": "ablation_alpha_allocation",
    "run_method_variant": "baselines",
    "run_synthetic_comparison": "baselines",
    "export_case_trace": "case_traces",
    "parse_case_trace_ids": "case_traces",
    "compute_group_metrics": "group_metrics",
    "describe_prediction_set": "introspection",
    "aggregate_chosen_path_metrics": "metrics",
    "aggregate_metrics": "metrics",
    "aggregate_topk_safety_metrics": "metrics",
    "compute_chosen_path_metrics": "metrics",
    "compute_sample_metrics": "metrics",
    "compute_topk_safety_metrics": "metrics",
    "build_per_sample_rows": "per_sample_export",
    "write_per_sample_csv": "per_sample_export",
    "run_evaluation_from_csv": "run_from_manifest",
    "run_evaluation_with_embeddings": "run_with_embeddings",
    "summarize_runtime_ms": "runtime",
    "run_synthetic_experiment": "runner",
    "iter_pathways": "selection_policies",
    "rank_pathways": "selection_policies",
    "render_pathway": "selection_policies",
    "select_pathway": "selection_policies",
}

__all__ = list(_EXPORTS)


def __getattr__(name: str):
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(f".{_EXPORTS[name]}", __name__), name)
    globals()[name] = value
    return value
