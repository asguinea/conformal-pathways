from __future__ import annotations

import pandas as pd
import pytest

pytest.importorskip("matplotlib")

from conformal_pathways.plots.plot_curves import plot_overlay_existential_safe


def _make_grid_csv(path, bias: float) -> None:
    rows = []
    for alpha in (0.05, 0.1, 0.2):
        for seed in (0, 1, 2):
            rows.append(
                {
                    "alpha": alpha,
                    "seed": seed,
                    "variant": "main",
                    "existential_safe": max(0.0, 1.0 - alpha - bias + 0.01 * seed),
                    "oracle_retained": 0.9,
                    "set_size": 5.0,
                    "empty_set_rate": 0.0,
                    "unsafe_exposure": 0.1,
                }
            )
    pd.DataFrame(rows).to_csv(path, index=False)


def test_plot_overlay_existential_safe_smoke(tmp_path) -> None:
    csv_a = tmp_path / "a.csv"
    csv_b = tmp_path / "b.csv"
    _make_grid_csv(csv_a, bias=0.0)
    _make_grid_csv(csv_b, bias=0.05)

    out_path = tmp_path / "overlay.png"
    plot_overlay_existential_safe(
        dataset_to_csv={"A": str(csv_a), "B": str(csv_b)},
        out_path=str(out_path),
    )

    assert out_path.exists()
    assert out_path.stat().st_size > 0
