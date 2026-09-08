from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def _get_pyplot():
    try:
        import matplotlib

        matplotlib.use("Agg", force=True)
        import matplotlib.pyplot as plt
    except ModuleNotFoundError as exc:  # pragma: no cover - depends on environment
        raise ImportError("matplotlib is required for plotting") from exc
    return plt


def load_grid_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


def summarize_by_alpha(
    df: pd.DataFrame,
    metric: str,
    variant: str = "main",
) -> pd.DataFrame:
    if "variant" not in df.columns:
        raise ValueError("input dataframe must contain 'variant' column")
    if "alpha" not in df.columns:
        raise ValueError("input dataframe must contain 'alpha' column")
    if metric not in df.columns:
        raise ValueError(f"input dataframe must contain metric column '{metric}'")

    filtered = df.loc[df["variant"] == variant, ["alpha", metric]].copy()
    if filtered.empty:
        return pd.DataFrame(columns=["alpha", "mean", "ci95"])

    grouped = (
        filtered.groupby("alpha", as_index=False)[metric]
        .agg(mean="mean", std="std", n="count")
        .sort_values("alpha")
    )

    grouped["std"] = grouped["std"].fillna(0.0)
    grouped["ci95"] = 1.96 * grouped["std"] / np.sqrt(grouped["n"])
    return grouped[["alpha", "mean", "ci95"]]


def plot_metric_vs_alpha(
    df: pd.DataFrame,
    metric: str,
    out_path: str,
    title: str,
    variant: str = "main",
    show_nominal: bool = False,
) -> None:
    plt = _get_pyplot()

    summary = summarize_by_alpha(df=df, metric=metric, variant=variant)
    if summary.empty:
        raise ValueError(f"no rows available for variant='{variant}'")

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.errorbar(
        summary["alpha"].to_numpy(),
        summary["mean"].to_numpy(),
        yerr=summary["ci95"].to_numpy(),
        marker="o",
        capsize=3,
    )

    if show_nominal and metric == "existential_safe":
        alphas = summary["alpha"].to_numpy(dtype=float)
        ax.plot(alphas, 1.0 - alphas, linestyle="--")

    ax.set_xlabel("alpha")
    ax.set_ylabel(metric)
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)


def plot_dataset_bundle(
    dataset_name: str,
    csv_path: str,
    out_dir: str = "artifacts/plots",
    variant: str = "main",
) -> None:
    df = load_grid_csv(csv_path)
    out_base = Path(out_dir)
    out_base.mkdir(parents=True, exist_ok=True)

    plots = [
        ("existential_safe", True),
        ("oracle_retained", False),
        ("set_size", False),
        ("unsafe_exposure", False),
    ]
    for metric, show_nominal in plots:
        out_path = out_base / f"{dataset_name}_{metric}.png"
        title = f"{dataset_name}: {metric} vs alpha ({variant})"
        plot_metric_vs_alpha(
            df=df,
            metric=metric,
            out_path=str(out_path),
            title=title,
            variant=variant,
            show_nominal=show_nominal,
        )


def plot_overlay_existential_safe(
    dataset_to_csv: dict[str, str],
    out_path: str = "artifacts/plots/existential_safe_overlay.png",
    variant: str = "main",
    title: str = "Existential safety vs. $\\alpha$ (overlay)",
    show_nominal: bool = True,
) -> None:
    plt = _get_pyplot()

    if not dataset_to_csv:
        raise ValueError("dataset_to_csv must be non-empty")

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    all_alphas: list[float] = []

    for dataset_name, csv_path in dataset_to_csv.items():
        df = load_grid_csv(csv_path)
        summary = summarize_by_alpha(df=df, metric="existential_safe", variant=variant)
        if summary.empty:
            continue

        alphas = summary["alpha"].to_numpy(dtype=float)
        means = summary["mean"].to_numpy(dtype=float)
        ci95 = summary["ci95"].to_numpy(dtype=float)
        all_alphas.extend(alphas.tolist())

        ax.errorbar(
            alphas,
            means,
            yerr=ci95,
            marker="o",
            capsize=3,
            label=dataset_name,
        )

    if show_nominal and all_alphas:
        nominal_x = np.array(sorted(set(all_alphas)), dtype=float)
        ax.plot(nominal_x, 1.0 - nominal_x, linestyle="--", label="nominal (1 - alpha)")

    ax.set_xlabel("alpha")
    ax.set_ylabel("existential_safe")
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)
