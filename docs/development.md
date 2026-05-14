# Development notes

## Goal

ROI Raster Histogram should remain a small, understandable QGIS plugin for calculating class histograms inside polygon ROIs from classified rasters.

The repository should be easy to return to after a long break and safe to keep public.

## Repository principles

Keep in the repository:

- source code,
- plugin metadata,
- README and documentation,
- small synthetic sample data only if explicitly documented,
- scripts that help package or test the plugin.

Do not keep in the repository:

- private geodata,
- real project data,
- large rasters,
- generated HTML reports,
- temporary clipped rasters,
- ZIP backups,
- local QGIS profile files,
- credentials, tokens, or local paths.

## Current code layout

The plugin code currently remains in the repository root:

```text
__init__.py
metadata.txt
roi_raster_histogram.py
```

This keeps manual QGIS installation simple because the repository folder can act directly as the plugin folder.

A deeper structure can be introduced later, for example:

```text
roi_raster_histogram/
├── __init__.py
├── plugin.py
├── dialog.py
├── processing.py
├── report.py
└── fields.py
```

Do this only together with tested import-path updates.

## Suggested refactoring direction

When the plugin is stable, split responsibilities:

| Area | Suggested module |
| --- | --- |
| QGIS plugin entry point | `plugin.py` |
| Dialog and widgets | `dialog.py` |
| Histogram/zonal processing | `processing.py` |
| Attribute writing | `fields.py` |
| HTML report export | `report.py` |
| Renderer/RAT class labels | `classes.py` |

Keep the public behavior unchanged during refactoring.

## Commit strategy

Use small commits:

1. documentation and repo hygiene,
2. metadata/init cleanup,
3. packaging script,
4. code formatting only,
5. functional refactor,
6. new features.

Avoid mixing formatting, refactoring, and new behavior in one commit.

## Suggested branch names

```text
cleanup/repo-structure
cleanup/readme
fix/plugin-metadata
refactor/split-modules
feature/csv-export
feature/selection-only
```

## Manual test environment

Recommended:

- QGIS 3.40 LTR or newer,
- clean QGIS profile for install tests,
- one small classified raster,
- one small polygon GeoPackage ROI layer.

## Packaging

Use:

```bash
python scripts/package_plugin.py
```

The script creates a ZIP package in `dist/`.

Do not commit files from `dist/`. Attach release ZIPs to GitHub Releases instead.
