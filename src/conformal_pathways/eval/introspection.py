from __future__ import annotations

import inspect
from dataclasses import fields, is_dataclass
from typing import Any

from conformal_pathways.eval.metrics import aggregate_metrics, compute_sample_metrics
from conformal_pathways.safety.oracle import is_safe


def _safe_len(value: Any) -> int | None:
    try:
        return len(value)  # type: ignore[arg-type]
    except Exception:
        return None


def _safe_preview(value: Any, max_chars: int = 180) -> str:
    try:
        text = repr(value)
    except Exception as exc:  # pragma: no cover - defensive
        text = f"<repr_error: {exc}>"
    if len(text) > max_chars:
        return f"{text[: max_chars - 3]}..."
    return text


def _describe_object(name: str, value: Any) -> list[str]:
    lines = [f"{name}:"]
    value_type = type(value)
    lines.append(f"  type: {value_type.__module__}.{value_type.__qualname__}")

    length = _safe_len(value)
    if length is not None:
        lines.append(f"  len: {length}")

    if isinstance(value, dict):
        keys = list(value.keys())
        keys_preview = keys[:8]
        suffix = " ..." if len(keys) > len(keys_preview) else ""
        lines.append(f"  keys: {keys_preview}{suffix}")

    if is_dataclass(value):
        dataclass_fields = [field.name for field in fields(value)]
        lines.append(f"  dataclass_fields: {dataclass_fields}")
    elif hasattr(value, "__dict__"):
        attrs = list(vars(value).keys())
        attrs_preview = attrs[:8]
        suffix = " ..." if len(attrs) > len(attrs_preview) else ""
        lines.append(f"  attrs: {attrs_preview}{suffix}")

    lines.append(f"  preview: {_safe_preview(value)}")
    return lines


def _extract_actions(pathway: Any) -> list[Any]:
    actions = getattr(pathway, "actions", None)
    if isinstance(actions, (list, tuple)):
        return list(actions)
    if isinstance(pathway, dict):
        dict_actions = pathway.get("actions")
        if isinstance(dict_actions, (list, tuple)):
            return list(dict_actions)
    return []


def _format_stage_action(stage: int, action: Any) -> str:
    name = getattr(action, "name", None)
    params = getattr(action, "params", None)
    if isinstance(action, dict):
        name = action.get("name", name)
        params = action.get("params", params)

    if isinstance(params, dict) and params:
        params_text = ", ".join(f"{key}={value!r}" for key, value in sorted(params.items()))
        return f"  stage {stage}: {name}({params_text}) [id={hex(id(action))}]"
    return f"  stage {stage}: {name} [id={hex(id(action))}]"


def describe_prediction_set(
    pi: Any,
    workflow: Any,
    sample: Any,
    extra_context: dict[str, Any] | None = None,
) -> str:
    lines: list[str] = ["=== Evaluation Introspection ==="]
    lines.append(f"workflow_name: {getattr(workflow, 'name', '<unknown>')}")
    lines.append(f"sample_id: {getattr(sample, 'sample_id', '<unknown>')}")
    lines.extend(_describe_object("prediction_set Pi(X0)", pi))

    if isinstance(pi, (list, tuple)) and pi:
        first_pathway = pi[0]
        lines.extend(_describe_object("prediction_set[0]", first_pathway))
        actions = _extract_actions(first_pathway)
        lines.append(f"prediction_set[0] per-stage actions ({len(actions)}):")
        if actions:
            for stage, action in enumerate(actions, start=1):
                lines.append(_format_stage_action(stage, action))
        else:
            lines.append("  <unable to detect actions list>")
    else:
        lines.append("prediction_set[0]: <not available>")

    lines.append("safety_oracle:")
    try:
        signature = inspect.signature(is_safe)
        lines.append(f"  function: {is_safe.__module__}.{is_safe.__qualname__}{signature}")
        lines.append("  required_inputs: workflow_name, sample_meta, final_state, pathway")
    except Exception as exc:  # pragma: no cover - defensive
        lines.append(f"  <unable to introspect oracle: {exc}>")

    lines.append("metrics_pipeline:")
    for fn in (compute_sample_metrics, aggregate_metrics):
        try:
            signature = inspect.signature(fn)
            source_file = inspect.getsourcefile(fn) or "<unknown>"
            lines.append(f"  {fn.__module__}.{fn.__qualname__}{signature} @ {source_file}")
        except Exception as exc:  # pragma: no cover - defensive
            lines.append(f"  <unable to introspect {fn}: {exc}>")

    if extra_context:
        lines.extend(_describe_object("extra_context", extra_context))

    return "\n".join(lines)
