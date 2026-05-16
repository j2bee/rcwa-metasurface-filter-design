"""Geometry wrapper for Figure 2 unit-cell construction.

The functions in this module translate the parameter-only specification in
``fig2_spec.py`` into a plain Python geometry object. They do not import or run
``rcw_grad``; instead they expose the normalized values and flattened design
grid expected by the ``rcwa.RCWA_obj``/``Add_LayerGrid`` workflow.
"""

from __future__ import annotations

from copy import deepcopy
from math import sqrt
from typing import Any

try:
    from . import fig2_spec as spec
except ImportError:  # Allows running this file directly from geometry/fig2.
    import fig2_spec as spec  # type: ignore


DEFAULT_GRID_SHAPE = (128, 128)
PLACEHOLDER_UNIFORM_THICKNESS = 1.0


def _epsilon(material_key: str) -> float:
    """Return fixed relative permittivity from the refractive index in the spec."""
    refractive_index = spec.MATERIALS[material_key]["refractive_index"]
    return float(refractive_index * refractive_index)


def _normalized_length(length_nm: float, reference_wavelength_nm: float) -> float:
    return float(length_nm / reference_wavelength_nm)


def _flatten_grid(grid: tuple[tuple[float, ...], ...]) -> tuple[float, ...]:
    return tuple(value for row in grid for value in row)


def _cylindrical_pillar_dof(
    diameter_nm: float,
    period_nm: float,
    grid_shape: tuple[int, int],
) -> tuple[tuple[float, ...], ...]:
    """Rasterize a centered circular pillar as a binary rcwa_grad DOF grid."""
    nx, ny = grid_shape
    radius_nm = diameter_nm / 2.0
    rows = []

    for ix in range(nx):
        x_nm = ((ix + 0.5) / nx - 0.5) * period_nm
        row = []
        for iy in range(ny):
            y_nm = ((iy + 0.5) / ny - 0.5) * period_nm
            row.append(1.0 if sqrt(x_nm * x_nm + y_nm * y_nm) <= radius_nm else 0.0)
        rows.append(tuple(row))

    return tuple(rows)


def default_diameter_nm() -> float:
    """Use the midpoint of the Figure 2 diameter sweep as a neutral placeholder."""
    diameter = spec.UNIT_CELL["pillar"]["diameter"]
    return float((diameter["minimum"] + diameter["maximum"]) / 2.0)


def diameter_sweep_nm(levels: int | None = None) -> tuple[float, ...]:
    """Return linearly spaced placeholder diameters across the specified sweep."""
    if levels is None:
        levels = int(spec.PHASE_LIBRARY["number_of_discrete_phase_levels"])
    if levels < 2:
        raise ValueError("levels must be at least 2")

    diameter = spec.UNIT_CELL["pillar"]["diameter"]
    minimum = float(diameter["minimum"])
    maximum = float(diameter["maximum"])
    step = (maximum - minimum) / (levels - 1)
    return tuple(minimum + i * step for i in range(levels))


def build_unit_cell_geometry(
    diameter_nm: float | None = None,
    grid_shape: tuple[int, int] = DEFAULT_GRID_SHAPE,
) -> dict[str, Any]:
    """Build the Figure 2 unit-cell geometry and rcwa_grad input payload."""
    if diameter_nm is None:
        diameter_nm = default_diameter_nm()

    nx, ny = grid_shape
    if nx <= 0 or ny <= 0:
        raise ValueError("grid_shape entries must be positive")

    diameter_bounds = spec.UNIT_CELL["pillar"]["diameter"]
    if not (diameter_bounds["minimum"] <= diameter_nm <= diameter_bounds["maximum"]):
        raise ValueError(
            "diameter_nm must be within the Figure 2 sweep bounds "
            f"[{diameter_bounds['minimum']}, {diameter_bounds['maximum']}] nm"
        )

    wavelength_nm = float(spec.WAVELENGTHS["design"])
    period_nm = float(spec.UNIT_CELL["lattice"]["period"])
    height_nm = float(spec.UNIT_CELL["pillar"]["height"])
    dof_grid = _cylindrical_pillar_dof(diameter_nm, period_nm, grid_shape)
    dof_flat = _flatten_grid(dof_grid)

    eps_air = _epsilon("superstrate")
    eps_pillar = _epsilon("pillar")
    eps_substrate = _epsilon("substrate")
    eps_background = eps_air
    eps_difference = eps_pillar - eps_background

    lattice_rcwa = {
        "L1": [_normalized_length(period_nm, wavelength_nm), 0.0],
        "L2": [0.0, _normalized_length(period_nm, wavelength_nm)],
    }
    patterned_layer = {
        "name": "silicon_nitride_pillar_grid",
        "method": "Add_LayerGrid",
        "thickness": _normalized_length(height_nm, wavelength_nm),
        "epsdiff": eps_difference,
        "epsbkg": eps_background,
        "Nx": nx,
        "Ny": ny,
        "dof": dof_flat,
    }

    rcwa_grad_input = {
        "reference_wavelength_m": wavelength_nm * 1e-9,
        "frequency": 1.0,
        "lattice_vectors": lattice_rcwa,
        "rcwa_obj": {
            "class": "rcwa.RCWA_obj",
            "nG": None,
            "L1": lattice_rcwa["L1"],
            "L2": lattice_rcwa["L2"],
            "freq": 1.0,
            "theta": 0.0,
            "phi": 0.0,
            "verbose": 0,
        },
        "incident_angles": deepcopy(spec.INCIDENCE["angles"]["normal"]),
        "planewave": {
            "p_amp": 0.0,
            "p_phase": 0.0,
            "s_amp": 1.0,
            "s_phase": 0.0,
            "note": "s-polarized placeholder for normally incident linear polarization",
        },
        "assembly_sequence": (
            {
                "name": "air_superstrate",
                "method": "Add_LayerUniform",
                "thickness": PLACEHOLDER_UNIFORM_THICKNESS,
                "epsilon": eps_air,
            },
            patterned_layer,
            {
                "name": "fused_silica_substrate",
                "method": "Add_LayerUniform",
                "thickness": PLACEHOLDER_UNIFORM_THICKNESS,
                "epsilon": eps_substrate,
            },
        ),
        "grid_layer_getdof": {
            "method": "GridLayer_getDOF",
            "dof": dof_flat,
        },
    }

    return {
        "source": deepcopy(spec.SOURCE),
        "units": deepcopy(spec.UNITS),
        "materials": deepcopy(spec.MATERIALS),
        "unit_cell": {
            "lattice": {
                "type": spec.UNIT_CELL["lattice"]["type"],
                "period_nm": period_nm,
                "vectors_nm": {
                    "a1": [period_nm, 0.0],
                    "a2": [0.0, period_nm],
                },
            },
            "features": (
                {
                    "name": "centered_cylindrical_pillar",
                    "material": "pillar",
                    "shape": "cylinder",
                    "center_nm": [0.0, 0.0],
                    "diameter_nm": float(diameter_nm),
                    "height_nm": height_nm,
                },
            ),
            "layers": (
                {"name": "air_superstrate", "material": "superstrate", "type": "uniform"},
                {
                    "name": "patterned_pillar_layer",
                    "material": "pillar",
                    "background_material": "superstrate",
                    "type": "binary_grid",
                    "grid_shape": grid_shape,
                    "dof_grid": dof_grid,
                },
                {"name": "fused_silica_substrate", "material": "substrate", "type": "uniform"},
            ),
        },
        "rcwa_grad": rcwa_grad_input,
    }


def build_diameter_sweep_geometries(
    levels: int | None = None,
    grid_shape: tuple[int, int] = DEFAULT_GRID_SHAPE,
) -> tuple[dict[str, Any], ...]:
    """Build one geometry payload for each placeholder diameter sweep point."""
    return tuple(
        build_unit_cell_geometry(diameter_nm=diameter_nm, grid_shape=grid_shape)
        for diameter_nm in diameter_sweep_nm(levels)
    )


FIG2_GEOMETRY = build_unit_cell_geometry()
