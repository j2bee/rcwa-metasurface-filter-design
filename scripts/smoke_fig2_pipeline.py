#!/usr/bin/env python3
"""Minimal end-to-end sanity check for the Figure 2 pipeline.

This smoke test uses one geometry instance and a tiny wavelength sweep. It is
not a parameter sweep and does not perform optimization.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "results" / "fig2" / "smoke"
DEFAULT_FIGURE_PATH = PROJECT_ROOT / "figures" / "fig2" / "smoke_fig2_transmission.png"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from figures.fig2.plot_fig2 import load_spectrum, plot_transmission  # noqa: E402
from geometry.fig2.geometry import default_diameter_nm  # noqa: E402
from scripts.run_fig2 import run_sweep, save_spectrum  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--figure-path", type=Path, default=DEFAULT_FIGURE_PATH)
    parser.add_argument("--output-stem", default="smoke_fig2_spectrum")
    parser.add_argument("--diameter-nm", type=float, default=default_diameter_nm())
    parser.add_argument("--grid-nx", type=int, default=8)
    parser.add_argument("--grid-ny", type=int, default=8)
    parser.add_argument("--wavelength-start-nm", type=float, default=620.0)
    parser.add_argument("--wavelength-stop-nm", type=float, default=625.0)
    parser.add_argument("--num-wavelengths", type=int, default=2)
    parser.add_argument("--nG", type=int, default=5)
    parser.add_argument("--q-ref", type=float, default=1e10)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    os.environ.setdefault("MPLBACKEND", "Agg")

    spectrum = run_sweep(
        diameter_nm=args.diameter_nm,
        grid_shape=(args.grid_nx, args.grid_ny),
        wavelength_start_nm=args.wavelength_start_nm,
        wavelength_stop_nm=args.wavelength_stop_nm,
        num_wavelengths=args.num_wavelengths,
        nG=args.nG,
        q_ref=args.q_ref,
    )
    npy_path, csv_path = save_spectrum(spectrum, args.output_dir, args.output_stem)

    loaded = load_spectrum(npy_path)
    if loaded.shape != (args.num_wavelengths, 5):
        raise AssertionError(f"Unexpected spectrum shape: {loaded.shape}")
    if not np.all(np.isfinite(loaded)):
        raise AssertionError("Spectrum contains non-finite values")

    plot_transmission(loaded, args.figure_path)
    for path in (npy_path, csv_path, args.figure_path):
        if not path.exists() or path.stat().st_size == 0:
            raise AssertionError(f"Expected non-empty output file: {path}")

    print("Figure 2 smoke pipeline completed")
    print(f"  spectrum_npy: {npy_path}")
    print(f"  spectrum_csv: {csv_path}")
    print(f"  figure: {args.figure_path}")


if __name__ == "__main__":
    main()
