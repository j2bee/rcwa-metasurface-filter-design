# Figure 2 parameter audit

This audit compares the current Figure 2 setup in `geometry/fig2/`,
`scripts/run_fig2.py`, and `scripts/smoke_fig2_pipeline.py` against the
paper-derived target parameters for Zhan et al., "Low-Contrast Dielectric
Metasurface Optics", ACS Photonics 3(2), 209-214 (2016),
DOI `10.1021/acsphotonics.5b00660`.

The ACS landing page confirms the SiN low-contrast metasurface platform and
visible-regime transmission/focusing results, but the accessible page text does
not expose all Figure 2 numerical captions. Numerical values below therefore
come from the paper setup as restated in Alan Zhan's 2019 University of
Washington thesis, which describes the same silicon-nitride forward-design
platform: SiN refractive index `n = 2`, fused quartz/silica substrate
`n_sub = 1.45`, parameters `t = lambda`, `p = 0.7 lambda`, design wavelength
`633 nm`, and pillar diameters `192-440 nm`.

## Comparison table

| Parameter | Paper / target value | Current setup | Status | Resonance / transmission risk |
| --- | --- | --- | --- | --- |
| Period | `p = 0.7 lambda`; at `lambda = 633 nm`, `p = 443 nm`. | `fig2_spec.UNIT_CELL["lattice"]["period"] = 443.0 nm`; `geometry.py` normalizes to `L1 = L2 = 443/633 = 0.6998`. | Matches target within rounding. | Low risk if wavelength normalization remains tied to `633 nm`. Changing reference wavelength without changing physical period would shift all normalized diffraction conditions. |
| Feature size | Cylindrical SiN pillars; diameter range `192-440 nm` for six phase levels across `0-2pi`. | Spec records `192-440 nm`. `geometry.py` can build any one diameter in this range. `default_diameter_nm()` uses midpoint `316 nm`. `run_fig2.py` runs one diameter unless `--diameter-nm` is changed. | Target range captured, but active simulation is a single placeholder geometry. | High risk for paper reproduction: Figure 2 phase/amplitude curves require sweeping diameter/duty cycle at fixed wavelength. A single midpoint diameter can land on the wrong side of a resonance and produce a misleading transmission depth. |
| Pillar height | `t = lambda`; at design wavelength, `t = 633 nm`. | `fig2_spec` height is `633.0 nm`; `geometry.py` passes patterned-layer thickness `633/633 = 1.0`. | Matches target. | High sensitivity: resonant phase and transmission depend strongly on height. Even small deviations can shift phase coverage and resonance locations. |
| Substrate | Fused quartz / silica wafer, `n_sub = 1.45`; substrate thickness used in parameter search was `t_sub = lambda`. | `fig2_spec` substrate is "fused silica / quartz", `n = 1.45`. `geometry.py` models the exit medium as a uniform layer with epsilon `1.45^2`; `thickness_for_unit_cell_sweep = 633 nm` is recorded but not passed as a separate finite substrate layer. | Material index matches; finite substrate treatment is simplified. | Moderate risk: semi-infinite substrate is usually appropriate for unit-cell transmission, but finite substrate thickness or air/glass backside interference would alter Fabry-Perot fringes and apparent transmission depth. |
| Superstrate / incident medium | Air, normally incident from air side for unit-cell lookup. | Air `n = 1.0`; layer stack is air -> patterned SiN-in-air grid -> silica substrate. | Matches intended incidence side. | Low-to-moderate risk if actual experiment includes illumination through substrate or additional interfaces; direction changes alter Fresnel background. |
| Refractive index assumptions | Paper setup uses low-contrast SiN with `n = 2` and substrate `n_sub = 1.45`; treated as transparent/lossless in visible design discussion. | Fixed, lossless values: air `1.0`, SiN_x `2.0`, SiO2 `1.45`. No dispersion or absorption. The repository's `rcw_grad.materials.SiN` dispersion model is not used. | Matches simplified paper-design assumptions, but not a measured dispersive material model. | Moderate-to-high risk for wavelength sweeps: fixed `n` suppresses material dispersion. Resonance position and depth may shift relative to fabricated devices or any paper simulation that used wavelength-dependent indices. |
| Wavelength for Figure 2 unit-cell response | Unit-cell phase/amplitude lookup is at design wavelength `633 nm` (FDTD operation also restated as `632 nm`). | `fig2_spec.WAVELENGTHS["design"] = 633 nm`; `figure_2_unit_cell_response_range = 633-633 nm`. | Captured in spec. | Low risk for the intended lookup if runner uses fixed `633 nm`. |
| Wavelength sweep range | The Figure 2(a-c) unit-cell library is not a broadband wavelength sweep; it is a geometry/duty-cycle response at fixed design wavelength. Separate lens chromatic characterization reports `455-625 nm`. | `run_fig2.py` defaults to `455-625 nm` using `chromatic_characterization_range`, for one diameter. Smoke test uses `620-625 nm`. | Mismatch for reproducing Figure 2(a-c). | High risk: sweeping wavelength at one geometry does not reproduce the paper's Figure 2 lookup. Resonance features in this spectrum should not be compared directly against paper diameter-sweep curves. |
| Polarization | Cylindrical pillars are polarization-insensitive at normal incidence; unit-cell lookup can use either linear polarization. | `fig2_spec` says primary `x`, equivalent `x/y`; `geometry.py`/`run_fig2.py` use `s_amp = 1`, `p_amp = 0` at `theta = phi = 0`. | Acceptable placeholder at normal incidence. | Low risk at normal incidence. At oblique incidence, p/s are no longer equivalent and both should be checked. |
| Incidence angle | Normal incidence for unit-cell lookup; oblique cases of 10 and 20 degrees appear in angular-incidence characterization. | `geometry.py` and `run_fig2.py` use normal incidence only. Spec records 10 and 20 degree oblique test cases but the runner does not expose them. | Matches normal-incidence lookup; oblique tests not implemented. | Low risk for Figure 2(a-c); high risk if comparing angular-incidence panels or experiments. |
| RCWA harmonic count | Not specified in the accessible ACS page or thesis excerpt for the Figure 2 unit-cell lookup. A converged reproduction requires harmonic convergence testing. | `run_fig2.py` default `--nG 101`; smoke test default `--nG 5`; geometry payload leaves `nG = None` as a placeholder until assembly. | Placeholder / unverified. | High numerical risk: too few harmonics can shift resonance position, smooth sharp features, and change transmission minima. `nG=5` is only a smoke-test value and is not physically reliable. |
| Grid resolution | Paper describes parameter search using RCWA but accessible text does not provide grid resolution. | `geometry.py` default grid `(128, 128)`; runner default `128 x 128`; smoke test `8 x 8`. | Placeholder / unverified. | High numerical risk: rasterizing a cylinder on a coarse grid changes fill factor and effective diameter. This can move resonances and alter transmission depth; `8 x 8` is only for sanity checking. |
| Geometry representation | Paper unit cell is a cylindrical pillar on a periodic square lattice. | Rasterized binary cylinder centered in the unit cell; background in patterned layer is air. | Conceptually matches. | Moderate risk: stair-stepped grid boundaries approximate the cylinder. Increasing `Nx`, `Ny` and comparing convergence is required. |
| Phase-library structure | Six discrete pillar diameters selected from a phase lookup spanning `0-2pi`; resonant discontinuities removed during parameter search. | Spec records six phase levels and diameter bounds, but there is no paper-calibrated phase-to-diameter lookup yet. `diameter_sweep_nm()` linearly spaces placeholder diameters. | Placeholder. | High risk: linear diameter spacing is not equivalent to equal phase spacing. Using it for phase masks would distort designed wavefronts and transmission. |
| Output quantity | Paper Figure 2 unit-cell plots report transmission amplitude and phase versus duty cycle / geometry. | `run_fig2.py` stores reflected power, transmitted power, and residual versus wavelength. It does not currently store complex transmission phase/amplitude. | Mismatch for Figure 2(a-c). | High risk for comparison: power transmission spectra cannot reproduce phase-delay panels or complex-amplitude lookup without additional extraction logic. |
| Surrounding uniform layer thickness | RCWA exterior media are effectively incident/exit media; examples use placeholder `thick0 = thickN = 1`. | `geometry.py` uses `PLACEHOLDER_UNIFORM_THICKNESS = 1.0` for air and substrate uniform layers. | Placeholder following local `rcw_grad` examples. | Usually low for power R/T, but phase reference or complex transmission extraction may depend on layer/reference-plane conventions. |

## Key mismatches to resolve before quantitative comparison

1. **Runner sweep type does not match Figure 2(a-c).** The current runner sweeps
   wavelength for one midpoint pillar diameter. The paper's Figure 2 unit-cell
   library is a fixed-wavelength geometry/duty-cycle sweep that reports
   transmission amplitude and phase. This is the largest conceptual mismatch.

2. **No complex transmission phase is extracted yet.** Current outputs are
   `R`, `T`, and residual. Reproducing Figure 2 phase curves requires extending
   the wrapper to extract complex zeroth-order transmission amplitude or an
   equivalent phase observable from `rcw_grad`.

3. **The active feature size is a placeholder.** `316 nm` is the midpoint of
   the paper diameter range, not a paper-selected phase state. It should not be
   interpreted as one of the six phase-library diameters unless verified against
   the original lookup.

4. **RCWA convergence is unverified.** `nG=101` is a reasonable starting default,
   but not paper-confirmed. `nG=5` and `8 x 8` grid in the smoke test only prove
   code-path health; they are not physically meaningful.

5. **Material dispersion is suppressed.** Fixed `n(SiN)=2` and `n(SiO2)=1.45`
   match the simple paper-design assumptions, but a broadband wavelength sweep
   should eventually decide whether to use fixed indices or `rcw_grad` material
   dispersion. This choice can shift resonance wavelengths and change depth.

6. **Substrate is simplified.** The code uses a uniform silica exit medium, not
   a finite substrate plus backside interface. This is acceptable for many
   unit-cell calculations but should be documented when comparing to measured
   spectra.

## Recommended next checks

- Add a fixed-`633 nm` diameter sweep mode for Figure 2(a-c).
- Add complex zeroth-order transmission amplitude/phase extraction or document
  exactly why only power transmission is available.
- Converge `nG` and grid resolution (`Nx`, `Ny`) for several diameters,
  especially near resonant features.
- Replace linearly spaced placeholder phase diameters with digitized or
  recomputed phase-library diameters.
- Decide whether broadband spectra should use fixed paper indices or the
  available `rcw_grad.materials.SiN` / `silica` dispersion models.
