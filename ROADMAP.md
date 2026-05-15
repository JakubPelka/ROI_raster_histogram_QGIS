# Roadmap

This roadmap lists practical improvements for ROI Raster Histogram. It is intentionally small and focused.

## Current status

**MAINTAINED — working plugin, early public version.**

The plugin works and is useful, but the code should still be reviewed before treating it as a polished QGIS plugin.

## Priority 1 — repository hygiene

- [x] Add clearer README.
- [x] Add MIT license.
- [x] Add `.gitignore` focused on QGIS, Python, generated outputs, archives, and geodata safety.
- [x] Add basic development notes.
- [x] Add testing checklist.
- [x] Add screenshots.
- [ ] Add a small synthetic sample dataset, if useful and safe.

## Priority 2 — plugin stability

- [x] Test installation from ZIP package.
- [x] Test on a clean QGIS profile.
- [x] Test on QGIS 3.40 LTR.
- [ ] Check whether plugin metadata is fully valid.
- [ ] Check whether all imports are required.
- [ ] Review error handling for missing/invalid layers.
- [ ] Review behavior when ROI and raster CRS differ.
- [ ] Review behavior for empty ROI intersections.

## Priority 3 — user-facing improvements

- [ ] Add automatic zoom/select current feature in the details tab.
- [ ] Add selection-only processing.
- [ ] Add CSV export.
- [ ] Add XLSX export.
- [ ] Add copy current feature result to clipboard.
- [ ] Add sorting options in result tables.
- [ ] Add clearer warning before modifying the original ROI attribute table.
- [ ] Add option to choose output field prefix.

## Priority 4 — code structure and performance

- [ ] Split the single Python file into smaller modules.
- [ ] Separate UI, processing logic, report export, and attribute writing.
- [ ] Add small helper functions for field-name generation and class-label extraction.
- [ ] Add testable pure-Python functions where possible.
- [ ] Profile performance on larger datasets.
- [ ] Consider chunking or progress feedback for large analyses.

## Priority 5 — renderer and raster support

- [ ] Improve support for additional renderer types.
- [ ] Improve handling of Raster Attribute Tables from different raster formats.
- [ ] Document expected raster formats and limitations.
- [ ] Add clearer fallback behavior when labels/colors are unavailable.

## Not planned for now

- Uploading private or real geodata to the repository.
- Large bundled sample rasters.
- Heavy framework migration before the current plugin is tested and documented.
