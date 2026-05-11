# Metasurface RCWA Simulation Project

This repository contains simulation and analysis tools for studying nanoscale metasurface spectral filters using Rigorous Coupled-Wave Analysis (RCWA).
The goal is to reproduce and explore periodic nanostructured “code mask” designs that control optical transmission spectra for applications in computational optics and nanophotonic signal encoding.

## Structure
* **rcw_grad/** – RCWA simulation engine (external repository)
* **scripts/** – custom simulation and analysis scripts
* **geometry/** – unit cell and metasurface design definitions
* **results/** – generated transmission spectra and data outputs
* **figures/** – plots and visualizations
* **notes/** – documentation and research notes

## Goals
* Reproduce metasurface spectral filter results from recent literature
* Study the relationship between unit cell geometry and transmission spectra
* Build a library of simulated optical responses for different structures

## Methods
* Rigorous Coupled-Wave Analysis (RCWA)
* Parameter sweeps over geometric variables (p, a, b, d)
* Spectral transmission analysis across wavelength range

## Status
**Initial setup and baseline simulation reproduction in progress.**
