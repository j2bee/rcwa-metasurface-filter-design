# Figure 2 iterative refinement log

Safety rule: only ONE parameter change per experiment iteration unless explicitly stated.

## exp_001 - 2026-05-17T02:29:12Z

- Label: baseline
- Changed parameters: None (baseline/reference state).
- Safety rule status: compliant
- Results folder: `results/fig2/exp_001`
- Figure: `figures/fig2/exp_001.png`

### Parameter set

| Section | Parameter | Value |
| --- | --- | ---: |
| geometry | p | 443.0 |
| geometry | a | 316.0 |
| geometry | b | 316.0 |
| geometry | d | 316.0 |
| geometry | h | 633.0 |
| materials | n_superstrate | 1.0 |
| materials | n_substrate | 1.45 |
| materials | n_pillar | 2.0 |
| wavelengths | start_nm | 455.0 |
| wavelengths | stop_nm | 625.0 |
| wavelengths | num_points | 171 |
| rcwa | harmonic_order | 101 |
| rcwa | grid_nx | 128 |
| rcwa | grid_ny | 128 |
| rcwa | q_ref | 10000000000.0 |

### Observed metrics

| Metric | Value |
| --- | ---: |
| resonance_wavelength_nm | 577.0 |
| minimum_transmission | 0.9110038202455477 |
| bandwidth_fwhm_nm | 49.25949826430917 |
| resonance_shift_vs_reference_nm | None |
| minimum_transmission_delta_vs_reference | None |

### Qualitative comparison to paper

Reference state; paper curve not yet digitized.

### Hypotheses for next change

Run convergence and geometry sensitivity studies before changing physical parameters.

