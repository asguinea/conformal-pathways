from __future__ import annotations

import argparse
from pathlib import Path

from conformal_pathways.plots.plot_curves import plot_dataset_bundle, plot_overlay_existential_safe


DEFAULT_RESULTS = {
    "idrid": "artifacts/results/idrid_grid.csv",
    "messidor": "artifacts/results/messidor_grid.csv",
    "eyepacs_5k": "artifacts/results/eyepacs_5k_grid.csv",
    "refuge": "artifacts/results/refuge_grid.csv",
    "rimone": "artifacts/results/rimone_grid.csv",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate alpha-curve plots from grid CSVs")
    parser.add_argument("--out_dir", default="artifacts/plots")
    parser.add_argument("--variant", default="main")
    parser.add_argument("--dataset", action="append", default=[])
    parser.add_argument("--csv", action="append", default=[])
    parser.add_argument("--overlay_existential_safe", action="store_true")
    parser.add_argument(
        "--overlay_out",
        default="artifacts/plots/existential_safe_overlay.png",
    )
    return parser


def _pairs_from_args(datasets: list[str], csvs: list[str]) -> list[tuple[str, str]]:
    if not datasets and not csvs:
        pairs: list[tuple[str, str]] = []
        for dataset, csv_path in DEFAULT_RESULTS.items():
            if Path(csv_path).exists():
                pairs.append((dataset, csv_path))
        return pairs

    if len(datasets) != len(csvs):
        raise ValueError("--dataset and --csv must be provided the same number of times")
    return list(zip(datasets, csvs))


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    pairs = _pairs_from_args(args.dataset, args.csv)
    if not pairs:
        print("No CSV files found/provided; nothing to plot.")
        return 0

    for dataset, csv_path in pairs:
        plot_dataset_bundle(
            dataset_name=dataset,
            csv_path=csv_path,
            out_dir=args.out_dir,
            variant=args.variant,
        )
        print(f"plotted {dataset} from {csv_path}")

    if args.overlay_existential_safe:
        dataset_to_csv = {dataset: csv_path for dataset, csv_path in pairs}
        plot_overlay_existential_safe(
            dataset_to_csv=dataset_to_csv,
            out_path=args.overlay_out,
            variant=args.variant,
        )
        print(f"plotted overlay to {args.overlay_out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
