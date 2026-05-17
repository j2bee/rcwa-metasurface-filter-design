#!/usr/bin/env python3
"""Geometry sensitivity sweep for the Figure 2 unit-cell simulation.

Each study varies one geometry parameter at a time while keeping the remaining
parameters at their Figure 2 defaults. For each case, the script runs a
wavelength sweep and records the wavelength and value of minimum transmission.
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
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "results" / "fig2" / "sensitivity"

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
    "parameter",
    "parameter_value_nm",
    "period_nm",
    "pillar_diameter_nm",
    "pillar_radius_nm",
    "height_nm",
    "runtime_seconds",
    "resonance_wavelength_nm",
    "delta_resonance_from_nominal_nm",
    "transmission_min",
    "delta_transmission_min_from_nominal",
    "resonance_index",
)


def _default_wavelength_bounds() -> tuple[float, float]:
    wavelength_range = fig2_spec.WAVELENGTHS["chromatic_characterization_range"]
    return float(wavelength_range["minimum"]), float(wavelength_range["maximum"])


def _nominal_period_nm() -> float:
    return float(fig2_spec.UNIT_CELL["lattice"]["period"])


def _nominal_height_nm() -> float:
    return float(fig2_spec.UNIT_CELL["pillar"]["height"])


def parse_values(raw_values: str | None, nominal: float, span_fraction: float, count: int) -> tuple[float, ...]:
    if span_fraction < 0:
        raise ValueError("span_fraction must be non-negative")
    if raw_values:
        values = tuple(float(value.strip()) for value in raw_values.split(",") if value.strip())
        if not values:
            raise ValueError("Explicit value list must contain at least one value")
        return tuple(sorted(values))
    if count < 2:
        raise ValueError("Generated sweeps require at least two values")
    start = nominal * (1.0 - span_fraction)
    stop = nominal * (1.0 + span_fraction)
    return tuple(float(value) for value in np.linspace(start, stop, count))


def _case_geometry(
    parameter: str,
    value_nm: float,
    nominal_period_nm: float,
    nominal_diameter_nm: float,
    nominal_height_nm: float,
) -> dict[str, float]:
    period_nm = nominal_period_nm
    diameter_nm = nominal_diameter_nm
    height_nm = nominal_height_nm

    if parameter == "period_nm":
        period_nm = value_nm
    elif parameter == "pillar_radius_nm":
        diameter_nm = 2.0 * value_nm
    elif parameter == "height_nm":
        height_nm = value_nm
    else:
        raise ValueError(f"Unsupported sensitivity parameter: {parameter}")

    return {
        "period_nm": period_nm,
        "pillar_diameter_nm": diameter_nm,
        "pillar_radius_nm": diameter_nm / 2.0,
        "height_nm": height_nm,
    }


def run_sensitivity_study(
    period_values_nm: tuple[float, ...],
    radius_values_nm: tuple[float, ...],
    height_values_nm: tuple[float, ...],
    grid_shape: tuple[int, int],
    wavelength_start_nm: float,
    wavelength_stop_nm: float,
    num_wavelengths: int,
    nG: int,
    q_ref: float,
) -> tuple[list[dict[str, float | str]], np.ndarray]:
    nominal_period_nm = _nominal_period_nm()
    nominal_diameter_nm = default_diameter_nm()
    nominal_height_nm = _nominal_height_nm()
    cases = (
        [("period_nm", value) for value in period_values_nm]
        + [("pillar_radius_nm", value) for value in radius_values_nm]
        + [("height_nm", value) for value in height_values_nm]
    )
    summary_rows: list[dict[str, float | str]] = []
    spectra = []

    for parameter, value_nm in cases:
        geometry = _case_geometry(
            parameter,
            value_nm,
            nominal_period_nm=nominal_period_nm,
            nominal_diameter_nm=nominal_diameter_nm,
            nominal_height_nm=nominal_height_nm,
        )
        start = perf_counter()
        spectrum = run_sweep(
            diameter_nm=geometry["pillar_diameter_nm"],
            period_nm=geometry["period_nm"],
            height_nm=geometry["height_nm"],
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
                "parameter": parameter,
                "parameter_value_nm": float(value_nm),
                "period_nm": float(geometry["period_nm"]),
                "pillar_diameter_nm": float(geometry["pillar_diameter_nm"]),
                "pillar_radius_nm": float(geometry["pillar_radius_nm"]),
                "height_nm": float(geometry["height_nm"]),
                "runtime_seconds": float(runtime_seconds),
                "resonance_wavelength_nm": float(spectrum[min_index, 0]),
                "delta_resonance_from_nominal_nm": 0.0,
                "transmission_min": float(transmission[min_index]),
                "delta_transmission_min_from_nominal": 0.0,
                "resonance_index": min_index,
            }
        )
        spectra.append(spectrum)

    _add_nominal_shifts(summary_rows)
    return summary_rows, np.asarray(spectra, dtype=float)


def _add_nominal_shifts(summary_rows: list[dict[str, float | str]]) -> None:
    nominal_values = {
        "period_nm": _nominal_period_nm(),
        "pillar_radius_nm": default_diameter_nm() / 2.0,
        "height_nm": _nominal_height_nm(),
    }
    for parameter, nominal_value in nominal_values.items():
        parameter_rows = [row for row in summary_rows if row["parameter"] == parameter]
        if not parameter_rows:
            continue
        reference = min(parameter_rows, key=lambda row: abs(float(row["parameter_value_nm"]) - nominal_value))
        reference_resonance = float(reference["resonance_wavelength_nm"])
        reference_tmin = float(reference["transmission_min"])
        for row in parameter_rows:
            row["delta_resonance_from_nominal_nm"] = float(row["resonance_wavelength_nm"]) - reference_resonance
            row["delta_transmission_min_from_nominal"] = float(row["transmission_min"]) - reference_tmin


def save_results(output_dir: Path, summary_rows: list[dict[str, float | str]], spectra: np.ndarray) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "summary_csv": output_dir / "sensitivity_summary.csv",
        "summary_npy": output_dir / "sensitivity_summary.npy",
        "spectra_csv": output_dir / "sensitivity_spectra.csv",
        "spectra_npz": output_dir / "sensitivity_spectra.npz",
    }

    numeric_summary = np.asarray(
        [
            [
                float(row["parameter_value_nm"]),
                float(row["period_nm"]),
                float(row["pillar_diameter_nm"]),
                float(row["pillar_radius_nm"]),
                float(row["height_nm"]),
                float(row["runtime_seconds"]),
                float(row["resonance_wavelength_nm"]),
                float(row["delta_resonance_from_nominal_nm"]),
                float(row["transmission_min"]),
                float(row["delta_transmission_min_from_nominal"]),
                float(row["resonance_index"]),
            ]
            for row in summary_rows
        ],
        dtype=float,
    )
    np.save(paths["summary_npy"], numeric_summary)
    np.savez(
        paths["spectra_npz"],
        parameter_names=np.asarray([row["parameter"] for row in summary_rows]),
        parameter_values_nm=np.asarray([float(row["parameter_value_nm"]) for row in summary_rows]),
        spectra=spectra,
        spectrum_columns=np.asarray(SPECTRUM_COLUMNS),
        summary=numeric_summary,
        summary_columns=np.asarray(SUMMARY_COLUMNS[1:]),
    )

    with paths["summary_csv"].open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_COLUMNS)
        writer.writeheader()
        writer.writerows(summary_rows)

    with paths["spectra_csv"].open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("parameter", "parameter_value_nm") + SPECTRUM_COLUMNS)
        for row, spectrum in zip(summary_rows, spectra):
            for spectrum_row in spectrum:
                writer.writerow(
                    (row["parameter"], row["parameter_value_nm"])
                    + tuple(float(value) for value in spectrum_row)
                )

    return paths


def plot_results(output_dir: Path, summary_rows: list[dict[str, float | str]]) -> dict[str, Path]:
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError("Plotting sensitivity results requires matplotlib.") from exc

    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "resonance": output_dir / "resonance_wavelength_vs_geometry_parameter.png",
        "transmission_min": output_dir / "transmission_min_vs_geometry_parameter.png",
    }
    parameters = ("period_nm", "pillar_radius_nm", "height_nm")
    labels = {
        "period_nm": "Period (nm)",
        "pillar_radius_nm": "Pillar radius (nm)",
        "height_nm": "Pillar height (nm)",
    }

    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.0), constrained_layout=True)
    for ax, parameter in zip(axes, parameters):
        rows = sorted(
            [row for row in summary_rows if row["parameter"] == parameter],
            key=lambda row: float(row["parameter_value_nm"]),
        )
        ax.plot(
            [float(row["parameter_value_nm"]) for row in rows],
            [float(row["resonance_wavelength_nm"]) for row in rows],
            marker="o",
        )
        ax.set_xlabel(labels[parameter])
        ax.set_ylabel("Resonance wavelength (nm)")
        ax.grid(True, color="0.85")
    fig.suptitle("Figure 2 resonance wavelength sensitivity")
    fig.savefig(paths["resonance"], dpi=300)
    plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.0), constrained_layout=True)
    for ax, parameter in zip(axes, parameters):
        rows = sorted(
            [row for row in summary_rows if row["parameter"] == parameter],
            key=lambda row: float(row["parameter_value_nm"]),
        )
        ax.plot(
            [float(row["parameter_value_nm"]) for row in rows],
            [float(row["transmission_min"]) for row in rows],
            marker="o",
            color="tab:orange",
        )
        ax.set_xlabel(labels[parameter])
        ax.set_ylabel("Minimum transmission")
        ax.set_ylim(0.0, 1.05)
        ax.grid(True, color="0.85")
    fig.suptitle("Figure 2 transmission minimum sensitivity")
    fig.savefig(paths["transmission_min"], dpi=300)
    plt.close(fig)

    return paths


def parse_args() -> argparse.Namespace:
    start_nm, stop_nm = _default_wavelength_bounds()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--period-values-nm", default=None, help="Comma-separated period values.")
    parser.add_argument("--radius-values-nm", default=None, help="Comma-separated pillar radius values.")
    parser.add_argument("--height-values-nm", default=None, help="Comma-separated pillar height values.")
    parser.add_argument("--span-fraction", type=float, default=0.05)
    parser.add_argument("--values-per-parameter", type=int, default=5)
    parser.add_argument("--grid-nx", type=int, default=128)
    parser.add_argument("--grid-ny", type=int, default=128)
    parser.add_argument("--wavelength-start-nm", type=float, default=start_nm)
    parser.add_argument("--wavelength-stop-nm", type=float, default=stop_nm)
    parser.add_argument("--num-wavelengths", type=int, default=171)
    parser.add_argument("--nG", type=int, default=101)
    parser.add_argument("--q-ref", type=float, default=1e10)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--skip-plots", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    os.environ.setdefault("MPLBACKEND", "Agg")
    period_values_nm = parse_values(
        args.period_values_nm,
        nominal=_nominal_period_nm(),
        span_fraction=args.span_fraction,
        count=args.values_per_parameter,
    )
    radius_values_nm = parse_values(
        args.radius_values_nm,
        nominal=default_diameter_nm() / 2.0,
        span_fraction=args.span_fraction,
        count=args.values_per_parameter,
    )
    height_values_nm = parse_values(
        args.height_values_nm,
        nominal=_nominal_height_nm(),
        span_fraction=args.span_fraction,
        count=args.values_per_parameter,
    )
    summary_rows, spectra = run_sensitivity_study(
        period_values_nm=period_values_nm,
        radius_values_nm=radius_values_nm,
        height_values_nm=height_values_nm,
        grid_shape=(args.grid_nx, args.grid_ny),
        wavelength_start_nm=args.wavelength_start_nm,
        wavelength_stop_nm=args.wavelength_stop_nm,
        num_wavelengths=args.num_wavelengths,
        nG=args.nG,
        q_ref=args.q_ref,
    )
    result_paths = save_results(args.output_dir, summary_rows, spectra)
    print("Saved sensitivity results:")
    for path in result_paths.values():
        print(f"  {path}")

    if not args.skip_plots:
        plot_paths = plot_results(args.output_dir, summary_rows)
        print("Saved sensitivity plots:")
        for path in plot_paths.values():
            print(f"  {path}")


if __name__ == "__main__":
    main()
