#!/usr/bin/env python3
"""Plot Figure 2 transmission spectra from saved simulation results."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RESULTS_PATH = PROJECT_ROOT / "results" / "fig2" / "fig2_transmission_spectrum.npy"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "figures" / "fig2" / "fig2_transmission.png"

COLUMN_NAMES = (
    "wavelength_nm",
    "frequency_normalized",
    "reflection",
    "transmission",
    "residual",
)


def load_spectrum(path: Path) -> np.ndarray:
    """Load a spectrum saved by scripts/run_fig2.py."""
    if not path.exists():
        raise FileNotFoundError(
            f"Simulation results not found: {path}. "
            "Run scripts/run_fig2.py first, or pass --input to an existing .npy/.csv file."
        )

    if path.suffix == ".npy":
        spectrum = np.load(path)
    elif path.suffix == ".csv":
        with path.open(newline="") as handle:
            reader = csv.DictReader(handle)
            spectrum = np.asarray(
                [[float(row[column]) for column in COLUMN_NAMES] for row in reader],
                dtype=float,
            )
    else:
        raise ValueError(f"Unsupported spectrum format: {path.suffix}. Use .npy or .csv.")

    if spectrum.ndim != 2 or spectrum.shape[1] < 4:
        raise ValueError("Spectrum must be a 2D array with at least four columns.")

    return spectrum


def load_paper_overlay(path: Path | None) -> np.ndarray | None:
    """Load optional digitized paper data with columns wavelength_nm, transmission."""
    if path is None:
        return None
    if not path.exists():
        raise FileNotFoundError(f"Paper overlay data not found: {path}")

    if path.suffix == ".npy":
        overlay = np.load(path)
    elif path.suffix == ".csv":
        overlay = np.loadtxt(path, delimiter=",", skiprows=1)
    else:
        raise ValueError(f"Unsupported paper overlay format: {path.suffix}. Use .npy or .csv.")

    if overlay.ndim != 2 or overlay.shape[1] < 2:
        raise ValueError("Paper overlay must have at least wavelength and transmission columns.")

    return overlay[:, :2]


def plot_transmission(
    spectrum: np.ndarray,
    output_path: Path,
    paper_overlay: np.ndarray | None = None,
    show: bool = False,
) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError("Plotting requires matplotlib. Install matplotlib and rerun this script.") from exc

    wavelength_nm = spectrum[:, 0]
    transmission = spectrum[:, 3]

    fig, ax = plt.subplots(figsize=(7.0, 4.5), constrained_layout=True)
    ax.plot(
        wavelength_nm,
        transmission,
        color="tab:blue",
        linewidth=2.0,
        label="RCWA simulation",
    )

    if paper_overlay is not None:
        ax.plot(
            paper_overlay[:, 0],
            paper_overlay[:, 1],
            color="black",
            linestyle="--",
            linewidth=1.6,
            label="Paper curve overlay",
        )
    else:
        ax.plot([], [], color="black", linestyle="--", linewidth=1.6, label="Paper curve overlay (placeholder)")
        ax.text(
            0.98,
            0.08,
            "Paper curve overlay placeholder",
            transform=ax.transAxes,
            ha="right",
            va="bottom",
            fontsize=9,
            color="0.35",
        )

    ax.set_title("ACS Photonics 2016 Figure 2 unit-cell transmission")
    ax.set_xlabel("Wavelength (nm)")
    ax.set_ylabel("Transmission")
    ax.set_xlim(float(np.min(wavelength_nm)), float(np.max(wavelength_nm)))
    ax.set_ylim(0.0, 1.05)
    ax.grid(True, which="major", color="0.85", linewidth=0.8)
    ax.legend(loc="best", frameon=True)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300)
    if show:
        plt.show()
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_RESULTS_PATH, help="Input spectrum .npy or .csv file.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH, help="Output figure path.")
    parser.add_argument(
        "--paper-overlay",
        type=Path,
        default=None,
        help="Optional digitized paper curve as .npy/.csv with wavelength_nm, transmission columns.",
    )
    parser.add_argument("--show", action="store_true", help="Display the plot interactively after saving.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    spectrum = load_spectrum(args.input)
    paper_overlay = load_paper_overlay(args.paper_overlay)
    plot_transmission(spectrum, args.output, paper_overlay=paper_overlay, show=args.show)
    print(f"Saved Figure 2 transmission plot: {args.output}")


if __name__ == "__main__":
    main()
