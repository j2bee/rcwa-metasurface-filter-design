#!/usr/bin/env python3
"""RCWA harmonic convergence study for the Figure 2 unit-cell simulation.

The study keeps one geometry fixed and sweeps only the RCWA Fourier truncation
target (`nG`). For each `nG`, it records the wavelength of minimum transmission,
the minimum transmission value, and the wall-clock runtime.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path
from time import perf_counter

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULTS_DIR = PROJECT_ROOT / "results" / "fig2" / "convergence"
DEFAULT_FIGURES_DIR = PROJECT_ROOT / "figures" / "fig2" / "convergence"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from geometry.fig2 import fig2_spec  # noqa: E402
from geometry.fig2.geometry import default_diameter_nm  # noqa: E402
from scripts.run_fig2 import run_sweep  # noqa: E402


SPECTRUM_COLUMNS = (
    "wavelength_nm",
    "frequency_normalized",
    "reflection",
    "transmission",
    "residual",
)
SUMMARY_COLUMNS = (
    "nG",
    "runtime_seconds",
    "resonance_wavelength_nm",
    "transmission_min",
    "resonance_index",
    "delta_resonance_from_max_ng_nm",
    "delta_transmission_min_from_max_ng",
)


def _default_wavelength_bounds() -> tuple[float, float]:
    wavelength_range = fig2_spec.WAVELENGTHS["chromatic_characterization_range"]
    return float(wavelength_range["minimum"]), float(wavelength_range["maximum"])


def parse_ng_values(raw_values: str) -> tuple[int, ...]:
    values = tuple(sorted({int(value.strip()) for value in raw_values.split(",") if value.strip()}))
    if not values:
        raise ValueError("At least one nG value is required")
    if any(value <= 0 for value in values):
        raise ValueError("All nG values must be positive")
    return values


def _summary_rows_with_stability(summary_rows: list[dict[str, float]]) -> list[dict[str, float]]:
    reference = summary_rows[-1]
    reference_wavelength = reference["resonance_wavelength_nm"]
    reference_tmin = reference["transmission_min"]

    for row in summary_rows:
        row["delta_resonance_from_max_ng_nm"] = row["resonance_wavelength_nm"] - reference_wavelength
        row["delta_transmission_min_from_max_ng"] = row["transmission_min"] - reference_tmin

    return summary_rows


def run_convergence_study(
    ng_values: tuple[int, ...],
    diameter_nm: float,
    grid_shape: tuple[int, int],
    wavelength_start_nm: float,
    wavelength_stop_nm: float,
    num_wavelengths: int,
    q_ref: float,
) -> tuple[list[dict[str, float]], np.ndarray]:
    summary_rows: list[dict[str, float]] = []
    spectra = []

    for nG in ng_values:
        start = perf_counter()
        spectrum = run_sweep(
            diameter_nm=diameter_nm,
            grid_shape=grid_shape,
            wavelength_start_nm=wavelength_start_nm,
            wavelength_stop_nm=wavelength_stop_nm,
            num_wavelengths=num_wavelengths,
            nG=nG,
            q_ref=q_ref,
        )
        runtime_seconds = perf_counter() - start

        transmission = spectrum[:, 3]
        min_index = int(np.argmin(transmission))
        summary_rows.append(
            {
                "nG": nG,
                "runtime_seconds": float(runtime_seconds),
                "resonance_wavelength_nm": float(spectrum[min_index, 0]),
                "transmission_min": float(transmission[min_index]),
                "resonance_index": min_index,
                "delta_resonance_from_max_ng_nm": 0.0,
                "delta_transmission_min_from_max_ng": 0.0,
            }
        )
        spectra.append(spectrum)

    return _summary_rows_with_stability(summary_rows), np.asarray(spectra, dtype=float)


def save_results(
    results_dir: Path,
    ng_values: tuple[int, ...],
    summary_rows: list[dict[str, float]],
    spectra: np.ndarray,
) -> dict[str, Path]:
    results_dir.mkdir(parents=True, exist_ok=True)
    summary_array = np.asarray([[row[column] for column in SUMMARY_COLUMNS] for row in summary_rows], dtype=float)
    paths = {
        "summary_csv": results_dir / "convergence_summary.csv",
        "summary_npy": results_dir / "convergence_summary.npy",
        "spectra_csv": results_dir / "convergence_spectra.csv",
        "spectra_npz": results_dir / "convergence_spectra.npz",
    }

    np.save(paths["summary_npy"], summary_array)
    np.savez(
        paths["spectra_npz"],
        nG_values=np.asarray(ng_values, dtype=int),
        spectra=spectra,
        spectrum_columns=np.asarray(SPECTRUM_COLUMNS),
        summary=summary_array,
        summary_columns=np.asarray(SUMMARY_COLUMNS),
    )

    with paths["summary_csv"].open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_COLUMNS)
        writer.writeheader()
        writer.writerows(summary_rows)

    with paths["spectra_csv"].open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("nG",) + SPECTRUM_COLUMNS)
        for nG, spectrum in zip(ng_values, spectra):
            for row in spectrum:
                writer.writerow((nG,) + tuple(float(value) for value in row))

    return paths


def plot_convergence(
    figures_dir: Path,
    ng_values: tuple[int, ...],
    summary_rows: list[dict[str, float]],
    spectra: np.ndarray,
) -> dict[str, Path]:
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError("Plotting convergence results requires matplotlib.") from exc

    figures_dir.mkdir(parents=True, exist_ok=True)
    nG_array = np.asarray(ng_values, dtype=float)
    resonance_wavelength = np.asarray([row["resonance_wavelength_nm"] for row in summary_rows], dtype=float)
    transmission_min = np.asarray([row["transmission_min"] for row in summary_rows], dtype=float)
    runtime_seconds = np.asarray([row["runtime_seconds"] for row in summary_rows], dtype=float)
    paths = {
        "spectra": figures_dir / "convergence_spectra_overlay.png",
        "resonance": figures_dir / "resonance_wavelength_vs_ng.png",
        "transmission_min": figures_dir / "transmission_min_vs_ng.png",
        "runtime": figures_dir / "runtime_scaling_vs_ng.png",
        "metrics": figures_dir / "convergence_metrics.png",
    }

    fig, ax = plt.subplots(figsize=(7.0, 4.5), constrained_layout=True)
    for nG, spectrum in zip(ng_values, spectra):
        ax.plot(spectrum[:, 0], spectrum[:, 3], linewidth=1.5, label=f"nG={nG}")
    ax.set_title("Figure 2 convergence spectra")
    ax.set_xlabel("Wavelength (nm)")
    ax.set_ylabel("Transmission")
    ax.set_ylim(0.0, 1.05)
    ax.grid(True, color="0.85")
    ax.legend(loc="best", fontsize=8)
    fig.savefig(paths["spectra"], dpi=300)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.0, 4.0), constrained_layout=True)
    ax.plot(nG_array, resonance_wavelength, marker="o")
    ax.set_title("Resonance wavelength stability")
    ax.set_xlabel("RCWA harmonic target nG")
    ax.set_ylabel("Wavelength at min transmission (nm)")
    ax.grid(True, color="0.85")
    fig.savefig(paths["resonance"], dpi=300)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.0, 4.0), constrained_layout=True)
    ax.plot(nG_array, transmission_min, marker="o", color="tab:orange")
    ax.set_title("Transmission minimum stability")
    ax.set_xlabel("RCWA harmonic target nG")
    ax.set_ylabel("Minimum transmission")
    ax.grid(True, color="0.85")
    fig.savefig(paths["transmission_min"], dpi=300)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.0, 4.0), constrained_layout=True)
    ax.plot(nG_array, runtime_seconds, marker="o", color="tab:green")
    ax.set_title("Runtime scaling")
    ax.set_xlabel("RCWA harmonic target nG")
    ax.set_ylabel("Runtime (s)")
    ax.grid(True, color="0.85")
    fig.savefig(paths["runtime"], dpi=300)
    plt.close(fig)

    fig, axes = plt.subplots(3, 1, figsize=(7.0, 8.0), constrained_layout=True, sharex=True)
    axes[0].plot(nG_array, resonance_wavelength, marker="o")
    axes[0].set_ylabel("Resonance nm")
    axes[0].grid(True, color="0.85")
    axes[1].plot(nG_array, transmission_min, marker="o", color="tab:orange")
    axes[1].set_ylabel("T min")
    axes[1].grid(True, color="0.85")
    axes[2].plot(nG_array, runtime_seconds, marker="o", color="tab:green")
    axes[2].set_xlabel("RCWA harmonic target nG")
    axes[2].set_ylabel("Runtime (s)")
    axes[2].grid(True, color="0.85")
    fig.suptitle("Figure 2 RCWA convergence metrics")
    fig.savefig(paths["metrics"], dpi=300)
    plt.close(fig)

    return paths


def parse_args() -> argparse.Namespace:
    start_nm, stop_nm = _default_wavelength_bounds()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ng-values", default="21,41,61,81,101", help="Comma-separated RCWA nG values.")
    parser.add_argument("--diameter-nm", type=float, default=default_diameter_nm())
    parser.add_argument("--grid-nx", type=int, default=128)
    parser.add_argument("--grid-ny", type=int, default=128)
    parser.add_argument("--wavelength-start-nm", type=float, default=start_nm)
    parser.add_argument("--wavelength-stop-nm", type=float, default=stop_nm)
    parser.add_argument("--num-wavelengths", type=int, default=171)
    parser.add_argument("--q-ref", type=float, default=1e10)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    parser.add_argument("--figures-dir", type=Path, default=DEFAULT_FIGURES_DIR)
    parser.add_argument("--skip-plots", action="store_true", help="Save numeric results without rendering plots.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    os.environ.setdefault("MPLBACKEND", "Agg")
    ng_values = parse_ng_values(args.ng_values)
    grid_shape = (args.grid_nx, args.grid_ny)

    summary_rows, spectra = run_convergence_study(
        ng_values=ng_values,
        diameter_nm=args.diameter_nm,
        grid_shape=grid_shape,
        wavelength_start_nm=args.wavelength_start_nm,
        wavelength_stop_nm=args.wavelength_stop_nm,
        num_wavelengths=args.num_wavelengths,
        q_ref=args.q_ref,
    )
    result_paths = save_results(args.results_dir, ng_values, summary_rows, spectra)
    print("Saved convergence results:")
    for path in result_paths.values():
        print(f"  {path}")

    if not args.skip_plots:
        figure_paths = plot_convergence(args.figures_dir, ng_values, summary_rows, spectra)
        print("Saved convergence figures:")
        for path in figure_paths.values():
            print(f"  {path}")


if __name__ == "__main__":
    main()
