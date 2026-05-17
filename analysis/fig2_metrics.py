"""Metrics for Figure 2 transmission spectra."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import numpy as np


SPECTRUM_COLUMNS = (
    "wavelength_nm",
    "frequency_normalized",
    "reflection",
    "transmission",
    "residual",
)


def load_spectrum(path: Path) -> np.ndarray:
    """Load a Figure 2 spectrum from `.npy` or `.csv`."""
    if path.suffix == ".npy":
        spectrum = np.load(path)
    elif path.suffix == ".csv":
        with path.open(newline="") as handle:
            reader = csv.DictReader(handle)
            spectrum = np.asarray(
                [[float(row[column]) for column in SPECTRUM_COLUMNS] for row in reader],
                dtype=float,
            )
    else:
        raise ValueError(f"Unsupported spectrum format: {path.suffix}")

    if spectrum.ndim != 2 or spectrum.shape[1] < 4:
        raise ValueError("Spectrum must have columns wavelength, frequency, reflection, transmission")
    return spectrum


def _interpolated_crossing(x0: float, y0: float, x1: float, y1: float, target: float) -> float:
    if y1 == y0:
        return float((x0 + x1) / 2.0)
    return float(x0 + (target - y0) * (x1 - x0) / (y1 - y0))


def estimate_fwhm_bandwidth_nm(wavelength_nm: np.ndarray, transmission: np.ndarray) -> dict[str, float]:
    """Estimate FWHM-like bandwidth for a transmission dip.

    The half-depth level is defined as `T_min + (T_max - T_min) / 2`. The
    returned width is the wavelength span over which transmission is below this
    level, using linear interpolation at the crossings when possible.
    """
    if wavelength_nm.size < 2:
        return {
            "bandwidth_fwhm_nm": float("nan"),
            "half_depth_transmission": float("nan"),
            "left_half_depth_nm": float("nan"),
            "right_half_depth_nm": float("nan"),
        }

    min_index = int(np.argmin(transmission))
    t_min = float(transmission[min_index])
    t_max = float(np.max(transmission))
    half_depth = t_min + 0.5 * (t_max - t_min)

    left = float("nan")
    for idx in range(min_index, 0, -1):
        y0 = float(transmission[idx - 1])
        y1 = float(transmission[idx])
        if (y0 - half_depth) * (y1 - half_depth) <= 0 and y0 != y1:
            left = _interpolated_crossing(
                float(wavelength_nm[idx - 1]),
                y0,
                float(wavelength_nm[idx]),
                y1,
                half_depth,
            )
            break

    right = float("nan")
    for idx in range(min_index, transmission.size - 1):
        y0 = float(transmission[idx])
        y1 = float(transmission[idx + 1])
        if (y0 - half_depth) * (y1 - half_depth) <= 0 and y0 != y1:
            right = _interpolated_crossing(
                float(wavelength_nm[idx]),
                y0,
                float(wavelength_nm[idx + 1]),
                y1,
                half_depth,
            )
            break

    bandwidth = right - left if np.isfinite(left) and np.isfinite(right) else float("nan")
    return {
        "bandwidth_fwhm_nm": float(bandwidth),
        "half_depth_transmission": float(half_depth),
        "left_half_depth_nm": float(left),
        "right_half_depth_nm": float(right),
    }


def compute_metrics(spectrum: np.ndarray, reference_curve: np.ndarray | None = None) -> dict[str, Any]:
    """Compute resonance, minimum transmission, and bandwidth metrics."""
    wavelength_nm = spectrum[:, 0]
    transmission = spectrum[:, 3]
    min_index = int(np.argmin(transmission))
    metrics: dict[str, Any] = {
        "resonance_wavelength_nm": float(wavelength_nm[min_index]),
        "minimum_transmission": float(transmission[min_index]),
        "resonance_index": min_index,
        "reference_curve_present": reference_curve is not None,
    }
    metrics.update(estimate_fwhm_bandwidth_nm(wavelength_nm, transmission))

    if reference_curve is not None:
        ref_min_index = int(np.argmin(reference_curve[:, 1]))
        metrics["reference_resonance_wavelength_nm"] = float(reference_curve[ref_min_index, 0])
        metrics["reference_minimum_transmission"] = float(reference_curve[ref_min_index, 1])
        metrics["resonance_shift_vs_reference_nm"] = (
            metrics["resonance_wavelength_nm"] - metrics["reference_resonance_wavelength_nm"]
        )
        metrics["minimum_transmission_delta_vs_reference"] = (
            metrics["minimum_transmission"] - metrics["reference_minimum_transmission"]
        )
    else:
        metrics["reference_resonance_wavelength_nm"] = None
        metrics["reference_minimum_transmission"] = None
        metrics["resonance_shift_vs_reference_nm"] = None
        metrics["minimum_transmission_delta_vs_reference"] = None

    return metrics


def save_metrics(metrics: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    """Save metrics as JSON and one-row CSV."""
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "metrics_summary.json"
    csv_path = output_dir / "metrics_summary.csv"
    with json_path.open("w") as handle:
        json.dump(metrics, handle, indent=2, allow_nan=True)
        handle.write("\n")
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(metrics.keys()))
        writer.writeheader()
        writer.writerow(metrics)
    return json_path, csv_path
