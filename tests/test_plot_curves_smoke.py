from __future__ import annotations

import pandas as pd
import pytest

pytest.importorskip("matplotlib")

from conformal_pathways.plots.plot_curves import plot_dataset_bundle


def test_plot_dataset_bundle_smoke(tmp_path) -> None:
    rows = []
    for alpha in (0.05, 0.1, 0.2):
        for seed in (0, 1, 2):
            rows.append(
                {
                    "alpha": alpha,
                    "seed": seed,
                    "variant": "main",
                    "existential_safe": max(0.0, 1.0 - alpha + 0.01 * seed),
                    "oracle_retained": max(0.0, 0.95 - 0.05 * alpha + 0.01 * seed),
                    "set_size": 6.0 + seed,
                    "empty_set_rate": 0.0,
                    "unsafe_exposure": min(1.0, 0.1 + alpha + 0.02 * seed),
                }
            )

    csv_path = tmp_path / "grid.csv"
    pd.DataFrame(rows).to_csv(csv_path, index=False)

    out_dir = tmp_path / "plots"
    plot_dataset_bundle(
        dataset_name="synthetic_ds",
        csv_path=str(csv_path),
        out_dir=str(out_dir),
        variant="main",
    )

    expected = [
        out_dir / "synthetic_ds_existential_safe.png",
        out_dir / "synthetic_ds_oracle_retained.png",
        out_dir / "synthetic_ds_set_size.png",
        out_dir / "synthetic_ds_unsafe_exposure.png",
    ]
    for path in expected:
        assert path.exists()
