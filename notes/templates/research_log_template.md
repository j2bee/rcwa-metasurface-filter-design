# Metasurface simulation research log

## Metadata

- Date:
- Researcher:
- Project / figure:
- Repository branch / commit:
- Related scripts:
- Related result files:
- Related figure files:

## Objective

Describe the purpose of this simulation.

- What paper, device, figure, or hypothesis is being investigated?
- What physical quantity is being reproduced or explored?
- What is the expected outcome?

## Geometry

Document the simulated unit cell or device geometry.

| Parameter | Value | Units | Source / rationale |
| --- | ---: | --- | --- |
| Period |  |  |  |
| Feature shape |  |  |  |
| Feature width / diameter / radius |  |  |  |
| Feature height |  |  |  |
| Lattice type |  |  |  |
| Substrate thickness / model |  |  |  |

Notes:

- Geometry construction method:
- Rasterization / grid resolution:
- Known approximations:

## Materials

Document all refractive index or permittivity assumptions.

| Region | Material | n / epsilon | Loss model | Source / rationale |
| --- | --- | --- | --- | --- |
| Superstrate |  |  |  |  |
| Patterned feature |  |  |  |  |
| Background |  |  |  |  |
| Substrate |  |  |  |  |

Notes:

- Fixed-index or dispersive model:
- Absorption included:
- Temperature / fabrication assumptions:

## RCWA settings

Record solver configuration.

| Setting | Value | Notes |
| --- | ---: | --- |
| Harmonic order / nG |  |  |
| Grid Nx x Ny |  |  |
| Wavelength range |  |  |
| Number of wavelength samples |  |  |
| Incident angle theta |  |  |
| Incident angle phi |  |  |
| Polarization |  |  |
| Normalization |  |  |
| Q / imaginary frequency factor |  |  |

Command used:

```bash

```

## Observed resonances

Summarize resonance and transmission features.

| Feature | Wavelength | Transmission | Reflection | Notes |
| --- | ---: | ---: | ---: | --- |
| Minimum transmission |  |  |  |  |
| Secondary feature |  |  |  |  |

Plots:

- Spectrum:
- Convergence:
- Sensitivity:
- Comparison to paper:

## Interpretation

Explain the results physically and computationally.

- Which geometric or material feature likely sets the resonance?
- Is the resonance consistent with the expected paper/device behavior?
- Does the transmission depth look physical?
- Are there signs of numerical artifacts?
- How do convergence and sensitivity checks affect confidence?

## Validation

Record checks performed.

- Smoke test:
- Energy balance / residual:
- Harmonic convergence:
- Grid convergence:
- Geometry sensitivity:
- Comparison against paper/reference data:

## Next steps

List concrete follow-up actions.

1.
2.
3.

## Open questions

Track unresolved scientific or implementation questions.

- 
- 
- 

## Notes and decisions

Capture context that may matter later.

- Parameter choices that were assumptions:
- Deviations from the paper:
- Reasons for accepting/rejecting a result:
- Links to related commits, issues, or PRs:
