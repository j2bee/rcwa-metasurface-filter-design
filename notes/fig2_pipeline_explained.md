# Figure 2 simulation pipeline explained

This document explains the current Figure 2 reproduction pipeline for
Zhan et al., "Low-Contrast Dielectric Metasurface Optics", ACS Photonics 3(2),
209-214 (2016). It is written as a research-portfolio description: each stage
connects the physical model to the computational implementation.

The pipeline is intentionally built around wrapper code. The vendored
`rcw_grad` solver is treated as an external engine and is not modified.

## File map

| Stage | File | Purpose |
| --- | --- | --- |
| Parameter specification | `geometry/fig2/fig2_spec.py` | Stores paper-derived geometry, material, wavelength, and incidence parameters. |
| Geometry construction | `geometry/fig2/geometry.py` | Converts the specification into a rasterized unit-cell geometry and an `rcw_grad`-compatible payload. |
| RCWA wavelength sweep | `scripts/run_fig2.py` | Builds an RCWA object at each wavelength, solves reflection/transmission, and saves `.npy` and `.csv` spectra. |
| End-to-end smoke test | `scripts/smoke_fig2_pipeline.py` | Runs a tiny one-geometry/two-wavelength sanity check through geometry, RCWA, output, and plotting. |
| Harmonic convergence | `scripts/run_fig2_convergence.py` | Sweeps RCWA harmonic target `nG` and measures resonance and transmission-minimum stability. |
| Geometry sensitivity | `scripts/run_fig2_sensitivity.py` | Perturbs period, pillar radius, and height independently and measures resonance shifts. |
| Spectrum plotting | `figures/fig2/plot_fig2.py` | Plots transmission versus wavelength from saved spectra. |
| Paper comparison | `figures/fig2/comparison/plot_fig2_comparison.py` | Overlays RCWA spectra with a digitized/reference paper curve or a placeholder template. |
| Interface notes | `notes/rcwa_interface.md` | Documents the low-level wrapper contract with `rcw_grad`. |
| Parameter audit | `notes/fig2_parameter_audit.md` | Compares current assumptions against paper-derived target parameters. |

## 1. Geometry definition

The starting point is `geometry/fig2/fig2_spec.py`. This file contains only
structured definitions and no solver code. The main unit-cell parameters are:

- square lattice period: `443 nm`,
- cylindrical silicon nitride pillar height: `633 nm`,
- pillar diameter range: `192-440 nm`,
- design wavelength: `633 nm`,
- incident medium: air,
- substrate: fused silica / quartz.

Physically, this unit cell represents one pixel of the low-contrast dielectric
metasurface. The pillar acts as a truncated dielectric waveguide / scatterer.
By changing the pillar diameter at fixed period and height, the local optical
phase delay and transmission amplitude can be controlled. In the paper-derived
design logic, the diameter range spans a phase library for wavefront shaping.

Computationally, the current simulation uses one geometry instance at a time.
The default diameter is the midpoint of the recorded range, `316 nm`, which is
a placeholder until a calibrated phase-to-diameter lookup is reconstructed.

## 2. Material assignment

Materials are recorded in `fig2_spec.py` and converted to relative
permittivity in `geometry/fig2/geometry.py`:

```text
epsilon = n^2
```

The current fixed-index assumptions are:

| Region | Refractive index | Relative permittivity |
| --- | ---: | ---: |
| air superstrate | `1.0` | `1.0` |
| silicon nitride pillar | `2.0` | `4.0` |
| fused silica / quartz substrate | `1.45` | `2.1025` |

Physically, these values model a transparent, low-index-contrast dielectric
metasurface operating in the visible. This reflects the simplified design
description in the paper-derived sources. It does not yet include material
dispersion or fabrication-dependent absorption.

Computationally, the patterned layer is represented by a binary material field:

```text
epsilon_grid = eps_background + dof * (eps_pillar - eps_background)
```

where `dof = 1` inside the cylindrical pillar and `dof = 0` in the air
background.

## 3. Unit-cell rasterization

`geometry/fig2/geometry.py` converts the analytic cylinder into a grid:

1. Choose a grid shape, defaulting to `128 x 128`.
2. Place a circular pillar at the center of the square unit cell.
3. Mark each grid sample as `1.0` if it lies inside the pillar radius and
   `0.0` otherwise.
4. Flatten the grid into the ordering expected by `rcw_grad.GridLayer_getDOF`.

This rasterization is the bridge between the physical geometry and RCWA's
Fourier representation. A finer grid better approximates the circular boundary.
A coarse grid changes the effective fill factor, which can shift resonances and
change the transmission minimum. The smoke tests intentionally use coarse
grids only to verify code-path health, not physical accuracy.

## 4. RCWA solve process

The solver interface follows the contract documented in `notes/rcwa_interface.md`.
For each wavelength, `scripts/run_fig2.py` performs the sequence:

```python
obj = rcwa.RCWA_obj(nG, L1, L2, freq, theta, phi, verbose=0)
obj.Add_LayerUniform(thick0, eps_air)
obj.Add_LayerGrid(thick_patterned, eps_pillar - eps_air, eps_air, Nx, Ny)
obj.Add_LayerUniform(thickN, eps_substrate)
obj.Init_Setup(Gmethod=0)
obj.MakeExcitationPlanewave(p_amp, p_phase, s_amp, s_phase, order=0)
obj.GridLayer_getDOF(dof)
R, T = obj.RT_Solve(normalize=1)
```

The normalized lattice vectors are:

```text
L1 = [period / design_wavelength, 0]
L2 = [0, period / design_wavelength]
```

and the patterned-layer thickness is:

```text
height / design_wavelength
```

For the nominal geometry, both are close to the paper-derived values:

```text
period / 633 nm = 443 / 633
height / 633 nm = 633 / 633 = 1
```

Physically, RCWA expands the periodic electromagnetic fields in lateral Fourier
orders. The patterned layer couples incident light into these orders; the
scattering matrix then propagates fields through the stack. Increasing `nG`
retains more Fourier content and should make the resonance wavelength and
transmission depth converge.

## 5. Wavelength sweep

`scripts/run_fig2.py` sweeps wavelength and rebuilds the RCWA object at each
sample. The normalized frequency is:

```text
freq = reference_wavelength / wavelength
```

with an optional small imaginary component controlled by `q_ref`, following
the convention used in the local `rcw_grad` examples.

The default sweep currently uses the recorded chromatic characterization range:

```text
455 nm to 625 nm
```

This is useful for studying resonance motion and spectral response, but it is
not the same as the original Figure 2(a-c) phase-library calculation, which is
a fixed-wavelength geometry sweep at the design wavelength. That distinction is
important when interpreting the resulting plot.

## 6. Transmission extraction

The RCWA solver returns reflected and transmitted powers:

```python
R, T = obj.RT_Solve(normalize=1)
```

The output spectrum stored by `scripts/run_fig2.py` has five columns:

| Column | Meaning |
| --- | --- |
| `wavelength_nm` | Physical wavelength sample. |
| `frequency_normalized` | `633 nm / wavelength_nm`. |
| `reflection` | Reflected power from `RT_Solve`. |
| `transmission` | Transmitted power from `RT_Solve`. |
| `residual` | `1 - reflection - transmission`, useful as an energy-balance diagnostic. |

The saved files are:

```text
results/fig2/fig2_transmission_spectrum.npy
results/fig2/fig2_transmission_spectrum.csv
```

Physically, the resonance wavelength is estimated as the wavelength at which
the transmitted power reaches its minimum. This is a practical scalar summary
for convergence and sensitivity studies, even though the full paper Figure 2
phase response requires complex transmission amplitude extraction that is not
implemented yet.

## 7. Plotting

`figures/fig2/plot_fig2.py` loads either the `.npy` or `.csv` spectrum and
plots:

```text
transmission vs wavelength
```

The plot includes clear axes, a fixed transmission scale, a grid, and a legend.
It also includes a placeholder hook for a paper curve overlay.

`figures/fig2/comparison/plot_fig2_comparison.py` extends this by accepting a
manual digitization of a paper/reference curve. When a reference is supplied,
it computes:

- resonance wavelength difference,
- minimum transmission difference,
- normalized resonance difference,
- normalized minimum-transmission difference,
- normalized RMSE,
- normalized mean absolute error.

When no reference is supplied, it writes:

```text
figures/fig2/comparison/paper_curve_placeholder.csv
```

as a template for future digitized paper data.

## 8. Validation and numerical studies

Several scripts validate different aspects of the pipeline.

### Smoke test

`scripts/smoke_fig2_pipeline.py` runs a minimal end-to-end check:

```text
geometry -> RCWA -> .npy/.csv output -> plot
```

It uses a tiny grid, small `nG`, and two wavelength points. This is a software
sanity check only; it is not intended to validate physical convergence.

### Harmonic convergence

`scripts/run_fig2_convergence.py` sweeps `nG` and tracks:

- wavelength at minimum transmission,
- minimum transmission value,
- runtime.

It saves numeric results under:

```text
results/fig2/convergence/
```

and plots under:

```text
figures/fig2/convergence/
```

Physically, a converged simulation should show small changes in resonance
wavelength and transmission minimum as `nG` increases. Runtime typically grows
with retained Fourier order because the layer eigenproblems and scattering
matrices become larger.

### Geometry sensitivity

`scripts/run_fig2_sensitivity.py` independently perturbs:

- period,
- pillar radius,
- pillar height.

For each perturbation, it computes the resonance wavelength and transmission
minimum. This is useful because each geometry parameter has a direct physical
effect:

- increasing period changes diffraction and coupling conditions,
- changing radius changes fill factor and modal effective index,
- changing height changes accumulated phase and Fabry-Perot-like resonant
  behavior of the pillar.

The results are saved under:

```text
results/fig2/sensitivity/
```

## 9. Physical interpretation

The low-contrast SiN metasurface relies on wavelength-scale dielectric pillars
to reshape transmitted optical wavefronts. The pillar geometry controls the
phase delay and transmission amplitude by changing how the incident field
couples into modes of the pillar and the periodic lattice. Resonance-like
features appear when the geometry supports stronger field buildup or mode
coupling; these features can lower transmission and produce rapid phase
variation.

From a design perspective, the useful operating regime balances three goals:

1. large phase coverage,
2. high transmission,
3. robustness to fabrication and numerical perturbations.

The convergence and sensitivity scripts quantify the last point. If small
changes in `nG`, grid resolution, radius, period, or height strongly move the
transmission minimum, then the current setup is not yet reliable for
quantitative comparison to the paper.

## 10. Current limitations

The pipeline is complete enough for wrapper-level studies, sanity checks, and
initial spectral sweeps. Important limitations remain:

- the active runner sweeps wavelength for a single geometry rather than
  reproducing the fixed-wavelength diameter sweep of Figure 2(a-c),
- the default diameter is a midpoint placeholder, not a calibrated phase-library
  state,
- only power transmission is extracted; complex transmission phase is not yet
  saved,
- fixed refractive indices are used instead of dispersive material models,
- substrate treatment is simplified as a uniform exit medium,
- RCWA harmonic and grid convergence must be demonstrated before quantitative
  claims are made.

These limitations are documented explicitly so future results can distinguish
between software-pipeline readiness and paper-level physical reproduction.
