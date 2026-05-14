# ROI Raster Histogram for QGIS

**Status:** MAINTAINED — working QGIS plugin, early public version  
**License:** MIT  
**Target platform:** QGIS 3.40 or newer recommended

ROI Raster Histogram is a free QGIS plugin for calculating class histograms inside polygon regions of interest (ROIs) from classified raster layers.

It is designed for categorical, single-band rasters such as land cover maps, habitat maps, landscape classes, environmental classifications, or similar raster datasets where each pixel value represents a class.

## What the plugin does

The plugin calculates how much of each raster class occurs inside one or more polygon features.

It can:

- calculate a combined class histogram for all ROI polygons,
- calculate per-feature class histograms,
- show results as tables and charts inside QGIS,
- read class labels and colors from a paletted raster renderer,
- use Raster Attribute Table (RAT) information as a fallback,
- export the result to an HTML report,
- optionally write class percentage fields back to the ROI attribute table,
- optionally add a clipped raster preview for visual inspection.

## Why this plugin exists

A common workflow is to clip a classified raster by a polygon and then calculate statistics from the clipped raster.

This can be misleading when the clipped raster keeps a rectangular extent. Pixels outside the polygon but inside the raster bounding box may still affect statistics if they are not handled correctly.

ROI Raster Histogram avoids that problem by calculating the histogram from the ROI geometry itself, not from the visual clipped preview.

The clipped raster preview is only a visual aid. It does not drive the final histogram calculation.

## Typical use cases

- land cover composition inside planning areas,
- habitat share inside ecological study areas,
- landscape class summaries for multiple polygons,
- environmental reporting based on classified rasters,
- checking dominant raster classes inside polygons,
- writing class-percentage metrics back to polygon attributes for mapping or filtering.

## Main features

### Project-layer based workflow

The plugin works directly with layers already loaded in the current QGIS project.

You select:

- ROI polygon layer,
- classified raster layer,
- raster band,
- feature label field.

### Combined summary

The combined summary shows aggregated class statistics for all analyzed ROI features.

It includes:

- raster class value,
- class label,
- pixel count,
- percentage share of all ROI pixels.

### Per-feature details

The feature details view lets you inspect each ROI polygon separately.

It includes:

- feature selector,
- Previous / Next navigation,
- per-feature chart,
- per-feature result table,
- total classified pixels,
- dominant class value,
- dominant class label,
- dominant class percentage.

### Class labels and colors

The plugin tries to read class names and colors from:

1. paletted raster renderer,
2. Raster Attribute Table (RAT), if available.

If labels are not available, raw raster values are used as class labels.

### Attribute-table output

When **Write class percentages to ROI attribute table** is enabled, the plugin writes results back to the original ROI layer.

General fields:

| Field | Meaning |
| --- | --- |
| `rh_totpx` | Total classified pixels inside the ROI feature |
| `rh_domval` | Dominant raster class value |
| `rh_domlbl` | Dominant raster class label |
| `rh_dompct` | Dominant raster class percentage |

Class percentage fields are created dynamically, one field per detected raster class.

Example field names:

| Example field | Meaning |
| --- | --- |
| `p_Akermark` | Percentage of the class named `Akermark` |
| `p_Sjo` | Percentage of the class named `Sjo` |
| `p_class001` | Fallback field name for class 001 |

The attribute table is stored in a wide format:

- one ROI feature = one row,
- one class percentage = one column.

GeoPackage is recommended when writing results back to attributes. Shapefiles have short field-name limits and may force stronger field-name shortening.

### HTML export

The HTML report includes:

- ROI layer name,
- raster layer name,
- raster band,
- selected feature label field,
- combined summary,
- combined chart,
- combined result table,
- per-feature overview table,
- per-feature sections with charts and tables.

The report is useful for documentation, review, sharing, or printing to PDF from a browser.

## Requirements

- QGIS 3.40 or newer recommended.
- Polygon ROI layer.
- Classified raster layer, preferably:
  - single-band,
  - integer class values,
  - paletted renderer or Raster Attribute Table.

No external Python packages are required for runtime. The plugin uses Python, PyQt, QGIS API, GDAL tools, and QGIS Processing components provided by QGIS.

## Recommended data setup

Best results are obtained when:

- ROI polygons are stored in GeoPackage,
- raster is a categorical classified raster,
- raster classes have labels and colors in a paletted renderer or Raster Attribute Table,
- ROI polygons and raster are in compatible coordinate reference systems,
- ROI features have a clear label/name field for easier review.

## Installation

### Manual installation from repository folder

Copy the plugin folder into your QGIS profile plugin directory.

Example on Windows:

```text
C:\Users\<USER>\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\ROI_raster_histogram_QGIS
```

The plugin folder should contain at least:

```text
ROI_raster_histogram_QGIS/
├── __init__.py
├── metadata.txt
└── roi_raster_histogram.py
```

Then:

1. Restart QGIS.
2. Open **Plugins > Manage and Install Plugins**.
3. Enable **ROI Raster Histogram**.

### Installation from ZIP package

If a release ZIP is available:

1. Open **Plugins > Manage and Install Plugins**.
2. Choose **Install from ZIP**.
3. Select the plugin ZIP file.
4. Enable **ROI Raster Histogram**.

## Usage

1. Load a polygon ROI layer into QGIS.
2. Load a classified raster layer into QGIS.
3. Open **ROI Raster Histogram** from the QGIS plugin menu or toolbar.
4. Select:
   - ROI polygon layer,
   - classified raster layer,
   - raster band,
   - feature label field.
5. Optional:
   - enable clipped raster preview,
   - enable writing class percentages to the ROI attribute table.
6. Click **Run**.
7. Review:
   - **Combined summary** tab,
   - **Feature details** tab.
8. Optionally export the result to HTML.

## Output table columns

| Column | Meaning |
| --- | --- |
| Value | Raster class value |
| Label | Class label from renderer, RAT, or raw value fallback |
| Pixel count | Number of pixels inside the ROI geometry |
| % ROI | Percentage share of the class inside the ROI |

## Notes and limitations

- Best suited for categorical rasters.
- Designed mainly for single-band classified rasters.
- Labels depend on renderer or RAT availability.
- If raster styling is unusual, labels may fall back to raw raster values.
- The clipped raster is only a visual preview.
- Field names written to the ROI table may be shortened for compatibility.
- Shapefiles have stronger field-name limitations than GeoPackage.
- Large rasters and many ROI polygons may require optimization in future versions.

## Repository structure

```text
ROI_raster_histogram_QGIS/
├── README.md
├── LICENSE
├── CHANGELOG.md
├── ROADMAP.md
├── requirements.txt
├── metadata.txt
├── __init__.py
├── roi_raster_histogram.py
├── docs/
│   ├── development.md
│   ├── testing.md
│   └── screenshots/
│       └── README.md
├── sample_data/
│   └── README.md
└── scripts/
    └── package_plugin.py
```

The plugin code remains in the repository root so the repository folder can still work as a QGIS plugin folder during manual installation.

A deeper package structure can be introduced later, but that should be done together with code refactoring and import-path updates.

## Development notes

This repository should contain source code, documentation, and small synthetic sample data only.

Do not commit:

- private geodata,
- large rasters,
- generated reports,
- temporary clipped rasters,
- local QGIS profile files,
- ZIP backups,
- exported outputs,
- credentials or tokens.

See [`docs/development.md`](docs/development.md) and [`docs/testing.md`](docs/testing.md) for maintenance notes.

## Roadmap

Planned or possible improvements are tracked in [`ROADMAP.md`](ROADMAP.md).

Current high-value candidates:

- selection-only processing,
- CSV export,
- XLSX export,
- automatic zoom/select current feature,
- better handling of additional raster renderer types,
- clearer large-data performance notes,
- optional sample dataset for public testing.

## License

MIT License. See [`LICENSE`](LICENSE).

## Author

Jakub Pelka
