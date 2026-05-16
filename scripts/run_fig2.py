#!/usr/bin/env python3
"""Run a Figure 2 unit-cell wavelength sweep with rcw_grad.

This script is a thin wrapper around the existing rcw_grad solver. It imports
the structured Figure 2 geometry payload, assembles an RCWA object for each
wavelength, and stores the resulting reflection/transmission spectrum.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Any

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RCW_GRAD_ROOT = PROJECT_ROOT / "rcw_grad"
RESULTS_DIR = PROJECT_ROOT / "results" / "fig2"


def _add_import_paths() -> None:
    for path in (
        PROJECT_ROOT,
        RCW_GRAD_ROOT,
        RCW_GRAD_ROOT / "materials",
        RCW_GRAD_ROOT / "examples",
    ):
        path_string = str(path)
        if path_string not in sys.path:
            sys.path.insert(0, path_string)


_add_import_paths()

from geometry.fig2 import fig2_spec  # noqa: E402
from geometry.fig2.geometry import build_unit_cell_geometry, default_diameter_nm  # noqa: E402


def _load_rcwa_module():
    """Import rcw_grad lazily so CLI help/dry-run do not require solver import."""
    import use_autograd

    use_autograd.use = 0
    import rcwa

    return rcwa


def _default_wavelength_bounds() -> tuple[float, float]:
    wavelength_range = fig2_spec.WAVELENGTHS["chromatic_characterization_range"]
    return float(wavelength_range["minimum"]), float(wavelength_range["maximum"])


def _frequency_for_wavelength(reference_wavelength_m: float, wavelength_nm: float, q_ref: float) -> complex:
    wavelength_m = wavelength_nm * 1e-9
    frequency = reference_wavelength_m / wavelength_m
    if np.isfinite(q_ref) and q_ref > 0:
        return frequency * (1.0 + 1j / (2.0 * q_ref))
    return complex(frequency)


def _assemble_rcwa_object(
    rcwa_module: Any,
    geometry_payload: dict[str, Any],
    wavelength_nm: float,
    nG: int,
    q_ref: float,
):
    rcwa_input = geometry_payload["rcwa_grad"]
    rcwa_obj_input = rcwa_input["rcwa_obj"]
    normal_angles = rcwa_input["incident_angles"]
    frequency = _frequency_for_wavelength(
        rcwa_input["reference_wavelength_m"],
        wavelength_nm,
        q_ref,
    )

    obj = rcwa_module.RCWA_obj(
        nG,
        rcwa_obj_input["L1"],
        rcwa_obj_input["L2"],
        frequency,
        normal_angles["theta"],
        normal_angles["phi"],
        verbose=0,
    )

    for layer in rcwa_input["assembly_sequence"]:
        method = layer["method"]
        if method == "Add_LayerUniform":
            obj.Add_LayerUniform(layer["thickness"], layer["epsilon"])
        elif method == "Add_LayerGrid":
            obj.Add_LayerGrid(
                layer["thickness"],
                layer["epsdiff"],
                layer["epsbkg"],
                layer["Nx"],
                layer["Ny"],
            )
        else:
            raise ValueError(f"Unsupported rcw_grad layer method: {method}")

    obj.Init_Setup(Gmethod=0)
    planewave = rcwa_input["planewave"]
    obj.MakeExcitationPlanewave(
        planewave["p_amp"],
        planewave["p_phase"],
        planewave["s_amp"],
        planewave["s_phase"],
        order=0,
    )
    obj.GridLayer_getDOF(np.asarray(rcwa_input["grid_layer_getdof"]["dof"], dtype=float))
    return obj, frequency


def run_sweep(
    diameter_nm: float,
    grid_shape: tuple[int, int],
    wavelength_start_nm: float,
    wavelength_stop_nm: float,
    num_wavelengths: int,
    nG: int,
    q_ref: float,
) -> np.ndarray:
    if num_wavelengths < 1:
        raise ValueError("num_wavelengths must be at least 1")

    rcwa_module = _load_rcwa_module()
    geometry_payload = build_unit_cell_geometry(diameter_nm=diameter_nm, grid_shape=grid_shape)
    wavelengths_nm = np.linspace(wavelength_start_nm, wavelength_stop_nm, num_wavelengths)
    rows = []

    for wavelength_nm in wavelengths_nm:
        obj, frequency = _assemble_rcwa_object(
            rcwa_module,
            geometry_payload,
            wavelength_nm,
            nG=nG,
            q_ref=q_ref,
        )
        reflection, transmission = obj.RT_Solve(normalize=1)
        rows.append(
            (
                float(wavelength_nm),
                float(np.real(frequency)),
                float(np.real(reflection)),
                float(np.real(transmission)),
                float(1.0 - np.real(reflection) - np.real(transmission)),
            )
        )

    return np.asarray(rows, dtype=float)


def save_spectrum(spectrum: np.ndarray, output_dir: Path, stem: str) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    npy_path = output_dir / f"{stem}.npy"
    csv_path = output_dir / f"{stem}.csv"

    np.save(npy_path, spectrum)
    with csv_path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("wavelength_nm", "frequency_normalized", "reflection", "transmission", "residual"))
        writer.writerows(spectrum.tolist())

    return npy_path, csv_path


def parse_args() -> argparse.Namespace:
    start_nm, stop_nm = _default_wavelength_bounds()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--diameter-nm", type=float, default=default_diameter_nm())
    parser.add_argument("--grid-nx", type=int, default=128)
    parser.add_argument("--grid-ny", type=int, default=128)
    parser.add_argument("--wavelength-start-nm", type=float, default=start_nm)
    parser.add_argument("--wavelength-stop-nm", type=float, default=stop_nm)
    parser.add_argument("--num-wavelengths", type=int, default=171)
    parser.add_argument("--nG", type=int, default=101)
    parser.add_argument("--q-ref", type=float, default=1e10)
    parser.add_argument("--output-dir", type=Path, default=RESULTS_DIR)
    parser.add_argument("--output-stem", default="fig2_transmission_spectrum")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build the geometry payload and print the planned sweep without importing rcw_grad.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    grid_shape = (args.grid_nx, args.grid_ny)

    if args.dry_run:
        payload = build_unit_cell_geometry(diameter_nm=args.diameter_nm, grid_shape=grid_shape)
        print("Figure 2 wavelength sweep configuration")
        print(f"  diameter_nm: {args.diameter_nm}")
        print(f"  grid_shape: {grid_shape}")
        print(f"  wavelength_nm: {args.wavelength_start_nm} to {args.wavelength_stop_nm}")
        print(f"  num_wavelengths: {args.num_wavelengths}")
        print(f"  nG: {args.nG}")
        print(f"  output_dir: {args.output_dir}")
        print(f"  dof_size: {len(payload['rcwa_grad']['grid_layer_getdof']['dof'])}")
        return

    spectrum = run_sweep(
        diameter_nm=args.diameter_nm,
        grid_shape=grid_shape,
        wavelength_start_nm=args.wavelength_start_nm,
        wavelength_stop_nm=args.wavelength_stop_nm,
        num_wavelengths=args.num_wavelengths,
        nG=args.nG,
        q_ref=args.q_ref,
    )
    npy_path, csv_path = save_spectrum(spectrum, args.output_dir, args.output_stem)
    print(f"Saved NumPy spectrum: {npy_path}")
    print(f"Saved CSV spectrum: {csv_path}")


if __name__ == "__main__":
    main()
