#!/usr/bin/env python3
"""Run an iterative Figure 2 RCWA experiment from param_control.py."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_ROOT = PROJECT_ROOT / "results" / "fig2"
FIGURES_ROOT = PROJECT_ROOT / "figures" / "fig2"
ITERATION_LOG = PROJECT_ROOT / "notes" / "fig2_iteration_log.md"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from analysis.fig2_metrics import compute_metrics, save_metrics  # noqa: E402
from figures.fig2.plot_fig2 import plot_transmission  # noqa: E402
from geometry.fig2 import param_control  # noqa: E402
from scripts.run_fig2 import run_sweep, save_spectrum  # noqa: E402


def _existing_experiment_dirs() -> list[Path]:
    if not RESULTS_ROOT.exists():
        return []
    return sorted(
        path for path in RESULTS_ROOT.glob("exp_[0-9][0-9][0-9]") if path.is_dir()
    )


def _next_experiment_id() -> str:
    existing = _existing_experiment_dirs()
    if not existing:
        return "exp_001"
    last_number = max(int(path.name.split("_")[1]) for path in existing)
    return f"exp_{last_number + 1:03d}"


def _load_previous_parameters() -> dict[str, Any] | None:
    existing = _existing_experiment_dirs()
    if not existing:
        return None
    parameter_path = existing[-1] / "parameters.json"
    if not parameter_path.exists():
        return None
    with parameter_path.open() as handle:
        return json.load(handle)


def _changed_parameters(current: dict[str, Any], previous: dict[str, Any] | None) -> list[str]:
    if previous is None:
        return []
    current_flat = param_control.flatten_parameter_set(current)
    previous_flat = param_control.flatten_parameter_set(previous)
    changed = []
    for key, value in current_flat.items():
        if previous_flat.get(key) != value:
            changed.append(key)
    return changed


def _enforce_one_parameter_change(current: dict[str, Any], previous: dict[str, Any] | None) -> list[str]:
    changed = _changed_parameters(current, previous)
    allow_multiple = bool(current["safety"]["allow_multiple_parameter_changes"])
    reason = str(current["safety"]["multiple_parameter_change_reason"]).strip()
    if len(changed) > 1 and not allow_multiple:
        raise RuntimeError(
            "Safety rule violated: only ONE parameter change is allowed per experiment iteration. "
            f"Changed parameters: {changed}. Set ALLOW_MULTIPLE_PARAMETER_CHANGES=True in "
            "geometry/fig2/param_control.py and document the reason if this is intentional."
        )
    if len(changed) > 1 and allow_multiple and not reason:
        raise RuntimeError("Multiple parameter changes require MULTIPLE_PARAMETER_CHANGE_REASON.")
    return changed


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    with path.open("w") as handle:
        json.dump(payload, handle, indent=2, allow_nan=True)
        handle.write("\n")


def _format_changed_parameters(changed: list[str]) -> str:
    if not changed:
        return "None (baseline/reference state)."
    return ", ".join(changed)


def append_iteration_log(
    experiment_id: str,
    timestamp_utc: str,
    parameters: dict[str, Any],
    metrics: dict[str, Any],
    changed: list[str],
    results_dir: Path,
    figure_path: Path,
) -> None:
    ITERATION_LOG.parent.mkdir(parents=True, exist_ok=True)
    if not ITERATION_LOG.exists():
        ITERATION_LOG.write_text(
            "# Figure 2 iterative refinement log\n\n"
            "Safety rule: only ONE parameter change per experiment iteration unless explicitly stated.\n\n"
        )

    notes = parameters["experiment_notes"]
    entry = f"""## {experiment_id} - {timestamp_utc}

- Label: {notes["label"]}
- Changed parameters: {_format_changed_parameters(changed)}
- Safety rule status: {"explicit multi-parameter change" if len(changed) > 1 else "compliant"}
- Results folder: `{results_dir.relative_to(PROJECT_ROOT)}`
- Figure: `{figure_path.relative_to(PROJECT_ROOT)}`

### Parameter set

| Section | Parameter | Value |
| --- | --- | ---: |
"""
    for section in ("geometry", "materials", "wavelengths", "rcwa"):
        for key, value in parameters[section].items():
            entry += f"| {section} | {key} | {value} |\n"

    entry += f"""
### Observed metrics

| Metric | Value |
| --- | ---: |
| resonance_wavelength_nm | {metrics["resonance_wavelength_nm"]} |
| minimum_transmission | {metrics["minimum_transmission"]} |
| bandwidth_fwhm_nm | {metrics["bandwidth_fwhm_nm"]} |
| resonance_shift_vs_reference_nm | {metrics["resonance_shift_vs_reference_nm"]} |
| minimum_transmission_delta_vs_reference | {metrics["minimum_transmission_delta_vs_reference"]} |

### Qualitative comparison to paper

{notes["qualitative_comparison_to_paper"]}

### Hypotheses for next change

{notes["hypotheses_for_next_change"]}

"""
    with ITERATION_LOG.open("a") as handle:
        handle.write(entry)


def run_experiment(experiment_id: str | None = None) -> dict[str, Path]:
    parameters = param_control.get_parameter_set()
    previous_parameters = _load_previous_parameters()
    changed = _enforce_one_parameter_change(parameters, previous_parameters)
    if experiment_id is None:
        experiment_id = _next_experiment_id()

    timestamp_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    result_dir = RESULTS_ROOT / experiment_id
    result_dir.mkdir(parents=True, exist_ok=False)
    FIGURES_ROOT.mkdir(parents=True, exist_ok=True)
    figure_path = FIGURES_ROOT / f"{experiment_id}.png"

    geometry = parameters["geometry"]
    materials = parameters["materials"]
    wavelengths = parameters["wavelengths"]
    rcwa = parameters["rcwa"]
    spectrum = run_sweep(
        diameter_nm=float(geometry["d"]),
        period_nm=float(geometry["p"]),
        height_nm=float(geometry["h"]),
        n_superstrate=float(materials["n_superstrate"]),
        n_pillar=float(materials["n_pillar"]),
        n_substrate=float(materials["n_substrate"]),
        grid_shape=(int(rcwa["grid_nx"]), int(rcwa["grid_ny"])),
        wavelength_start_nm=float(wavelengths["start_nm"]),
        wavelength_stop_nm=float(wavelengths["stop_nm"]),
        num_wavelengths=int(wavelengths["num_points"]),
        nG=int(rcwa["harmonic_order"]),
        q_ref=float(rcwa["q_ref"]),
    )
    npy_path, csv_path = save_spectrum(spectrum, result_dir, "transmission_spectrum")
    metrics = compute_metrics(spectrum)
    metrics_json, metrics_csv = save_metrics(metrics, result_dir)
    plot_transmission(spectrum, figure_path)

    parameter_snapshot = {
        **parameters,
        "experiment_id": experiment_id,
        "timestamp_utc": timestamp_utc,
        "changed_parameters_from_previous": changed,
    }
    parameter_path = result_dir / "parameters.json"
    _write_json(parameter_path, parameter_snapshot)
    append_iteration_log(experiment_id, timestamp_utc, parameters, metrics, changed, result_dir, figure_path)

    return {
        "result_dir": result_dir,
        "spectrum_npy": npy_path,
        "spectrum_csv": csv_path,
        "metrics_json": metrics_json,
        "metrics_csv": metrics_csv,
        "parameters_json": parameter_path,
        "figure": figure_path,
        "iteration_log": ITERATION_LOG,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-id", default=None, help="Optional explicit ID such as exp_001.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = run_experiment(args.experiment_id)
    print("Figure 2 experiment complete:")
    for key, path in paths.items():
        print(f"  {key}: {path}")


if __name__ == "__main__":
    main()
