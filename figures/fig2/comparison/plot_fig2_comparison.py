#!/usr/bin/env python3
"""Compare current Figure 2 RCWA spectra against a paper/reference curve.

If no paper curve is supplied, the script still saves the RCWA plot plus a
placeholder CSV template for manually digitized paper data. Metrics are marked
as placeholder/NaN until a reference curve is provided.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SIMULATION_PATH = PROJECT_ROOT / "results" / "fig2" / "fig2_transmission_spectrum.npy"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "figures" / "fig2" / "comparison"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from figures.fig2.plot_fig2 import load_paper_overlay, load_spectrum  # noqa: E402


METRIC_COLUMNS = (
    "metric",
    "value",
    "units",
    "description",
)


def _curve_minimum(curve: np.ndarray) -> tuple[float, float, int]:
    if curve.ndim != 2 or curve.shape[1] < 2:
        raise ValueError("Curve must have at least wavelength and transmission columns")
    finite_mask = np.isfinite(curve[:, 0]) & np.isfinite(curve[:, 1])
    if not np.any(finite_mask):
        return float("nan"), float("nan"), -1

    finite_curve = curve[finite_mask]
    index = int(np.argmin(finite_curve[:, 1]))
    return float(finite_curve[index, 0]), float(finite_curve[index, 1]), index


def _interpolate_reference(reference_curve: np.ndarray, wavelengths_nm: np.ndarray) -> np.ndarray:
    order = np.argsort(reference_curve[:, 0])
    sorted_reference = reference_curve[order]
    return np.interp(wavelengths_nm, sorted_reference[:, 0], sorted_reference[:, 1])


def compute_comparison_metrics(
    simulation_curve: np.ndarray,
    reference_curve: np.ndarray | None,
) -> dict[str, float | bool]:
    sim_resonance_nm, sim_tmin, _ = _curve_minimum(simulation_curve)
    metrics: dict[str, float | bool] = {
        "placeholder_reference": reference_curve is None,
        "simulation_resonance_wavelength_nm": sim_resonance_nm,
        "simulation_transmission_min": sim_tmin,
        "reference_resonance_wavelength_nm": float("nan"),
        "reference_transmission_min": float("nan"),
        "resonance_wavelength_difference_nm": float("nan"),
        "minimum_transmission_difference": float("nan"),
        "normalized_resonance_difference": float("nan"),
        "normalized_minimum_transmission_difference": float("nan"),
        "normalized_rmse": float("nan"),
        "normalized_mean_absolute_error": float("nan"),
    }

    if reference_curve is None:
        return metrics

    ref_resonance_nm, ref_tmin, _ = _curve_minimum(reference_curve)
    reference_interp = _interpolate_reference(reference_curve, simulation_curve[:, 0])
    residual = simulation_curve[:, 1] - reference_interp
    wavelength_span = float(np.max(simulation_curve[:, 0]) - np.min(simulation_curve[:, 0]))
    reference_dynamic_range = float(np.max(reference_curve[:, 1]) - np.min(reference_curve[:, 1]))
    if wavelength_span == 0:
        wavelength_span = 1.0
    if reference_dynamic_range == 0:
        reference_dynamic_range = 1.0

    resonance_difference = sim_resonance_nm - ref_resonance_nm
    tmin_difference = sim_tmin - ref_tmin
    metrics.update(
        {
            "reference_resonance_wavelength_nm": ref_resonance_nm,
            "reference_transmission_min": ref_tmin,
            "resonance_wavelength_difference_nm": resonance_difference,
            "minimum_transmission_difference": tmin_difference,
            "normalized_resonance_difference": resonance_difference / wavelength_span,
            "normalized_minimum_transmission_difference": tmin_difference / reference_dynamic_range,
            "normalized_rmse": float(np.sqrt(np.mean(residual * residual)) / reference_dynamic_range),
            "normalized_mean_absolute_error": float(np.mean(np.abs(residual)) / reference_dynamic_range),
        }
    )
    return metrics


def _metric_rows(metrics: dict[str, float | bool]) -> list[dict[str, str]]:
    descriptions = {
        "placeholder_reference": "True when no digitized/reference curve was provided.",
        "simulation_resonance_wavelength_nm": "Wavelength at minimum simulated transmission.",
        "simulation_transmission_min": "Minimum simulated transmission.",
        "reference_resonance_wavelength_nm": "Wavelength at minimum reference transmission.",
        "reference_transmission_min": "Minimum reference transmission.",
        "resonance_wavelength_difference_nm": "simulation resonance wavelength minus reference resonance wavelength.",
        "minimum_transmission_difference": "simulation minimum transmission minus reference minimum transmission.",
        "normalized_resonance_difference": "resonance wavelength difference normalized by simulation wavelength span.",
        "normalized_minimum_transmission_difference": "minimum-transmission difference normalized by reference transmission range.",
        "normalized_rmse": "RMSE between simulation and interpolated reference, normalized by reference transmission range.",
        "normalized_mean_absolute_error": "Mean absolute error normalized by reference transmission range.",
    }
    units = {
        "simulation_resonance_wavelength_nm": "nm",
        "reference_resonance_wavelength_nm": "nm",
        "resonance_wavelength_difference_nm": "nm",
    }
    rows = []
    for key, value in metrics.items():
        if isinstance(value, bool):
            value_string = str(value)
        elif np.isnan(value):
            value_string = "nan"
        else:
            value_string = f"{float(value):.12g}"
        rows.append(
            {
                "metric": key,
                "value": value_string,
                "units": units.get(key, "unitless"),
                "description": descriptions[key],
            }
        )
    return rows


def save_metrics(metrics: dict[str, float | bool], output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "metrics_csv": output_dir / "comparison_metrics.csv",
        "metrics_json": output_dir / "comparison_metrics.json",
    }
    rows = _metric_rows(metrics)
    with paths["metrics_csv"].open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=METRIC_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    with paths["metrics_json"].open("w") as handle:
        json.dump(metrics, handle, indent=2, allow_nan=True)
        handle.write("\n")
    return paths


def save_placeholder_reference_template(simulation_curve: np.ndarray, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "paper_curve_placeholder.csv"
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("wavelength_nm", "transmission"))
        for wavelength_nm in simulation_curve[:, 0]:
            writer.writerow((float(wavelength_nm), ""))
    return path


def plot_comparison(
    simulation_curve: np.ndarray,
    reference_curve: np.ndarray | None,
    metrics: dict[str, float | bool],
    output_dir: Path,
) -> Path:
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError("Comparison plotting requires matplotlib.") from exc

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "fig2_rcwa_vs_paper_comparison.png"
    fig, ax = plt.subplots(figsize=(7.4, 4.8), constrained_layout=True)
    ax.plot(
        simulation_curve[:, 0],
        simulation_curve[:, 1],
        color="tab:blue",
        linewidth=2.0,
        label="Current RCWA simulation",
    )

    if reference_curve is not None:
        ax.plot(
            reference_curve[:, 0],
            reference_curve[:, 1],
            color="black",
            linestyle="--",
            linewidth=1.8,
            label="Digitized/reference paper curve",
        )
    else:
        ax.plot([], [], color="black", linestyle="--", linewidth=1.8, label="Paper curve placeholder")
        ax.text(
            0.98,
            0.08,
            "Add digitized paper curve via --paper-reference",
            transform=ax.transAxes,
            ha="right",
            va="bottom",
            fontsize=9,
            color="0.35",
        )

    sim_resonance = metrics["simulation_resonance_wavelength_nm"]
    sim_tmin = metrics["simulation_transmission_min"]
    if not np.isnan(sim_resonance):
        ax.scatter([sim_resonance], [sim_tmin], color="tab:blue", zorder=4)

    ref_resonance = metrics["reference_resonance_wavelength_nm"]
    ref_tmin = metrics["reference_transmission_min"]
    if not np.isnan(ref_resonance):
        ax.scatter([ref_resonance], [ref_tmin], color="black", zorder=4)

    metric_text = (
        f"Delta lambda_res = {metrics['resonance_wavelength_difference_nm']:.4g} nm\n"
        f"Delta T_min = {metrics['minimum_transmission_difference']:.4g}\n"
        f"norm RMSE = {metrics['normalized_rmse']:.4g}"
    )
    if metrics["placeholder_reference"]:
        metric_text = "Paper/reference curve placeholder\nmetrics pending digitized data"
    ax.text(
        0.02,
        0.04,
        metric_text,
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=9,
        bbox={"boxstyle": "round,pad=0.35", "facecolor": "white", "edgecolor": "0.75"},
    )

    ax.set_title("Figure 2 RCWA vs paper/reference comparison")
    ax.set_xlabel("Wavelength (nm)")
    ax.set_ylabel("Transmission")
    ax.set_ylim(0.0, 1.05)
    ax.grid(True, color="0.85")
    ax.legend(loc="best", frameon=True)
    fig.savefig(output_path, dpi=300)
    plt.close(fig)
    return output_path


def simulation_curve_from_spectrum(spectrum: np.ndarray) -> np.ndarray:
    return np.column_stack((spectrum[:, 0], spectrum[:, 3]))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--simulation", type=Path, default=DEFAULT_SIMULATION_PATH)
    parser.add_argument(
        "--paper-reference",
        type=Path,
        default=None,
        help="Optional .csv/.npy with wavelength_nm, transmission columns.",
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    spectrum = load_spectrum(args.simulation)
    simulation_curve = simulation_curve_from_spectrum(spectrum)
    reference_curve = load_paper_overlay(args.paper_reference)
    metrics = compute_comparison_metrics(simulation_curve, reference_curve)
    plot_path = plot_comparison(simulation_curve, reference_curve, metrics, args.output_dir)
    metric_paths = save_metrics(metrics, args.output_dir)
    print(f"Saved comparison plot: {plot_path}")
    for path in metric_paths.values():
        print(f"Saved comparison metrics: {path}")
    if reference_curve is None:
        placeholder_path = save_placeholder_reference_template(simulation_curve, args.output_dir)
        print(f"Saved paper curve placeholder template: {placeholder_path}")


if __name__ == "__main__":
    main()
