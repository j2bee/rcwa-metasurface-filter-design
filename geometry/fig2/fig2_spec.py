"""Structured parameters for reproducing Figure 2 of Zhan et al. (2016).

This module intentionally contains no simulation code. Values are given in
nanometers unless a field name states otherwise.
"""

SOURCE = {
    "paper": "Low-Contrast Dielectric Metasurface Optics",
    "authors": ("A. Zhan", "S. Colburn", "R. Trivedi", "T. K. Fryett", "C. M. Dodson", "A. Majumdar"),
    "journal": "ACS Photonics 3(2), 209-214 (2016)",
    "doi": "10.1021/acsphotonics.5b00660",
    "figure": "Figure 2, panels a-c",
}

UNITS = {
    "length": "nm",
    "angle": "degree",
    "wavelength": "nm",
}

MATERIALS = {
    "superstrate": {
        "name": "air",
        "refractive_index": 1.0,
        "loss_model": "fixed, lossless",
    },
    "pillar": {
        "name": "silicon nitride",
        "formula": "SiN_x",
        "refractive_index": 2.0,
        "loss_model": "fixed, lossless over visible design band",
    },
    "substrate": {
        "name": "fused silica / quartz",
        "formula": "SiO2",
        "refractive_index": 1.45,
        "loss_model": "fixed, lossless",
    },
}

UNIT_CELL = {
    "lattice": {
        "type": "square",
        "period": 443.0,
        "period_ratio_to_design_wavelength": 0.7,
    },
    "pillar": {
        "shape": "cylindrical",
        "height": 633.0,
        "diameter": {
            "minimum": 192.0,
            "maximum": 440.0,
            "sweep_parameter": True,
        },
        "diameter_ratio_to_period": {
            "minimum": 0.4334085778781038,
            "maximum": 0.9932279909706546,
        },
    },
    "substrate": {
        "material": "fused silica / quartz",
        "thickness_for_unit_cell_sweep": 633.0,
    },
}

PHASE_LIBRARY = {
    "target_phase_span_rad": (0.0, 6.283185307179586),
    "number_of_discrete_phase_levels": 6,
    "diameter_range": {
        "minimum": 192.0,
        "maximum": 440.0,
    },
    "selection_rule": "choose pillar diameter from RCWA phase lookup at the design wavelength",
}

WAVELENGTHS = {
    "design": 633.0,
    "fdtd_operation": 632.0,
    "figure_2_unit_cell_response_range": {
        "minimum": 633.0,
        "maximum": 633.0,
    },
    "chromatic_characterization_range": {
        "minimum": 455.0,
        "maximum": 625.0,
    },
}

INCIDENCE = {
    "illumination": "plane wave",
    "direction": "from air superstrate toward silica substrate",
    "polarization": {
        "basis": "linear",
        "primary": "x",
        "equivalent_due_to_cylindrical_symmetry": ("x", "y"),
    },
    "angles": {
        "normal": {
            "theta": 0.0,
            "phi": 0.0,
        },
        "oblique_test_cases": (
            {"theta": 10.0, "phi": 0.0},
            {"theta": 20.0, "phi": 0.0},
        ),
    },
}

FIGURE_2_TARGETS = {
    "panels": ("a", "b", "c"),
    "response_quantities": (
        "transmission_amplitude",
        "transmission_phase",
    ),
    "sweep": {
        "parameter": "pillar.diameter",
        "minimum": 192.0,
        "maximum": 440.0,
        "fixed_period": 443.0,
        "fixed_height": 633.0,
        "fixed_wavelength": 633.0,
    },
}
