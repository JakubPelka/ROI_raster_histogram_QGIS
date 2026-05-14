# Changelog

All notable changes to this project should be documented in this file.

This project follows a practical changelog style. Keep entries short, factual, and useful for returning to the repository later.

## [Unreleased]

### Added

- Repository cleanup structure.
- Public README focused on plugin purpose, usage, outputs, and limitations.
- Roadmap file for future improvements.
- Development and testing notes.
- Git ignore rules for generated outputs, heavy geodata, archives, and local files.

### To review

- Code structure and formatting.
- Runtime behavior on QGIS 3.40 LTR.
- Plugin packaging workflow.
- Performance on larger raster/ROI datasets.

## [0.1.0] - 2026-05-13

### Added

- Initial working version of ROI Raster Histogram plugin.
- Combined class histogram for polygon ROI features.
- Per-feature result review.
- HTML report export.
- Optional writing of class percentage fields to ROI attributes.
- Class labels/colors from raster renderer or Raster Attribute Table fallback.
