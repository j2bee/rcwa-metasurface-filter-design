# RCWA interface contract

This note summarizes the wrapper-facing contract for `rcw_grad` as used in this
repository. It is based on `rcw_grad/rcwa.py`, `rcw_grad/materials/materials.py`,
and the example assembly functions under `rcw_grad/examples/`.

## Unit-cell simulation inputs

Create one `rcwa.RCWA_obj` per frequency / incidence / geometry state:

```python
obj = rcwa.RCWA_obj(nG, L1, L2, freq, theta, phi, verbose=0)
```

- `nG`: Fourier truncation target. `Init_Setup()` may adjust the actual retained
  order count.
- `L1`, `L2`: 2D lattice vectors as `[x, y]` lists, normalized to the reference
  wavelength used by the sweep. Examples use `Lx = Period / lam0`.
- `freq`: normalized frequency. Examples use `freq = lam0 / wavelength`; a small
  imaginary part may be added as `freq * (1 + 1j / (2 * Q))`.
- `theta`, `phi`: incidence angles in radians.
- First and last layers must be uniform.

Layer thicknesses passed to `Add_LayerUniform` / `Add_LayerGrid` are also
normalized to the same reference wavelength.

## Materials

Material helpers live in `rcw_grad/materials/materials.py`. They expose:

```python
material = materials.silicon(...)
epsilon = material.epsilon(x, x_type="lambda")
```

- Built-ins include `SiN`, `silica`, `silicon`, and `gold`.
- `epsilon(...)` returns relative permittivity.
- `x_type="lambda"` expects wavelength in meters for tabulated/interpolated
  materials. The `SiN` class internally converts to microns after this call.
- Some materials accept `epsimag` to impose a minimum imaginary permittivity.
- Examples compute patterned contrast as `epsdiff = material.epsilon(lambda) -
  epsbkg`.

For fixed-index wrappers, use `epsilon = n**2` directly.

## Geometry handoff

`rcw_grad` supports uniform layers and patterned grid layers:

```python
obj.Add_LayerUniform(thickness, epsilon)
obj.Add_LayerGrid(thickness, epsdiff, epsbkg, Nx, Ny)
```

After all layers are added:

```python
obj.Init_Setup(Gmethod=0)
obj.MakeExcitationPlanewave(p_amp, p_phase, s_amp, s_phase, order=0)
obj.GridLayer_getDOF(dof)
```

Grid-layer contract:

- `dof` is a flattened array concatenating all patterned layers in layer order.
- Each grid layer contributes `Nx * Ny` values.
- `GridLayer_getDOF` reshapes each slice to `[Nx, Ny]` and forms
  `epsilon_grid = epsdiff * dof + epsbkg`.
- For binary geometry, use `dof=1` inside the patterned material and `dof=0` in
  the background.
- For direct permittivity grids, use `GridLayer_geteps(ep_all)` instead of
  `GridLayer_getDOF(dof)`.

The usual layer stack for a transmission unit cell is:

1. uniform incident medium,
2. one or more patterned grid layers,
3. uniform exit medium / substrate.

## Excitation

Plane-wave excitation is set with:

```python
obj.MakeExcitationPlanewave(
    p_amp, p_phase, s_amp, s_phase, order=0, direction="forward"
)
```

- `p_amp` / `s_amp` select p- and s-polarized components.
- Phases are in radians.
- `direction` defaults to `"forward"`; `"backward"` is also supported.
- Examples commonly use `{"p_amp": 0, "s_amp": 1, "p_phase": 0, "s_phase": 0}`.

## Transmission spectra extraction

For each wavelength/frequency sample:

```python
R, T = obj.RT_Solve(normalize=1)
```

- `R` and `T` are reflected and transmitted powers.
- `normalize=1` applies the incident-medium / angle normalization used by the
  examples.
- A spectrum is built by looping over wavelengths, rebuilding or updating the
  object for each `freq`, then storing `(wavelength, R, T)`.
- Examples often sweep normalized `freq` and save arrays after sorting.

Minimal wrapper sequence:

```python
freq = lam0 / wavelength
obj = rcwa.RCWA_obj(nG, L1, L2, freq, theta, phi, verbose=0)
obj.Add_LayerUniform(thick0, eps_incident)
obj.Add_LayerGrid(thick_patterned, eps_material - eps_background, eps_background, Nx, Ny)
obj.Add_LayerUniform(thickN, eps_exit)
obj.Init_Setup(Gmethod=0)
obj.MakeExcitationPlanewave(p_amp, p_phase, s_amp, s_phase, order=0)
obj.GridLayer_getDOF(dof.flatten())
R, T = obj.RT_Solve(normalize=1)
```
