"""Central parameter control for Figure 2 RCWA experiments.

Edit this file to define a new experiment. The iterative runner enforces the
scientific safety rule that only one parameter should change between experiment
iterations unless `ALLOW_MULTIPLE_PARAMETER_CHANGES` is explicitly set to True.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


# Geometry parameters, in nanometers.
GEOMETRY = {
    "p": 443.0,  # square lattice period
    "a": 316.0,  # feature size along x; equal to d for the circular baseline
    "b": 316.0,  # feature size along y; equal to d for the circular baseline
    "d": 316.0,  # circular pillar diameter used by current geometry wrapper
    "h": 633.0,  # pillar height
}

# Material parameters, specified as fixed refractive indices.
MATERIALS = {
    "n_superstrate": 1.0,
    "n_substrate": 1.45,
    "n_pillar": 2.0,
}

# Wavelength sweep, in nanometers.
WAVELENGTHS = {
    "start_nm": 455.0,
    "stop_nm": 625.0,
    "num_points": 171,
}

# RCWA and rasterization settings.
RCWA = {
    "harmonic_order": 101,
    "grid_nx": 128,
    "grid_ny": 128,
    "q_ref": 1e10,
}

# Scientific safety rule:
# Change only one parameter per experiment iteration unless explicitly stated.
ALLOW_MULTIPLE_PARAMETER_CHANGES = False
MULTIPLE_PARAMETER_CHANGE_REASON = ""

# Qualitative bookkeeping used in the iteration log.
EXPERIMENT_NOTES = {
    "label": "baseline",
    "qualitative_comparison_to_paper": "Reference state; paper curve not yet digitized.",
    "hypotheses_for_next_change": (
        "Run convergence and geometry sensitivity studies before changing physical parameters."
    ),
    "explicitly_changed_parameters": (),
}


def get_parameter_set() -> dict[str, Any]:
    """Return a deep-copy snapshot of the current editable parameter set."""
    return {
        "geometry": deepcopy(GEOMETRY),
        "materials": deepcopy(MATERIALS),
        "wavelengths": deepcopy(WAVELENGTHS),
        "rcwa": deepcopy(RCWA),
        "safety": {
            "allow_multiple_parameter_changes": ALLOW_MULTIPLE_PARAMETER_CHANGES,
            "multiple_parameter_change_reason": MULTIPLE_PARAMETER_CHANGE_REASON,
        },
        "experiment_notes": deepcopy(EXPERIMENT_NOTES),
    }


def flatten_parameter_set(parameter_set: dict[str, Any] | None = None) -> dict[str, Any]:
    """Flatten nested parameters for iteration-to-iteration change checks."""
    if parameter_set is None:
        parameter_set = get_parameter_set()

    flat: dict[str, Any] = {}
    for section in ("geometry", "materials", "wavelengths", "rcwa"):
        for key, value in parameter_set[section].items():
            flat[f"{section}.{key}"] = value
    return flat
