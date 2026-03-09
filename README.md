# ROI Raster Histogram for QGIS

A QGIS plugin for calculating class histograms inside polygon ROIs from a classified raster, reviewing both combined and per-feature results, exporting reports to HTML, and optionally writing class percentages back to the ROI attribute table.

The plugin is designed for **classified single-band rasters** such as land cover, habitat maps, landscape classes, categorical environmental rasters, and similar datasets.

## Main features

- Select **ROI polygon layer directly from the current QGIS project**
- Select **raster layer directly from the current QGIS project**
- Select raster **band**
- Choose a **feature label field** for per-feature reporting and navigation
- Calculate the histogram **directly from ROI geometry** using zonal histogram logic
- Avoid false counts from raster bounding box / NoData area outside the polygon
- Display a **combined summary** for all ROI features together
- Display **per-feature results** with:
  - feature selector
  - Previous / Next navigation
  - per-feature chart
  - per-feature result table
- Read class labels and colors from:
  1. **Paletted raster renderer**
  2. **Raster Attribute Table (RAT)** as fallback
- Optionally add a **clipped raster preview** to the project
- Export the result to **HTML report**
- Optionally write **class percentage fields** to the ROI attribute table

## Why this plugin exists

A standard raster clip creates a rectangular raster extent. If statistics are calculated directly from that clipped raster, pixels outside the polygon but inside the bounding box may still affect the result.

This plugin avoids that problem by calculating the histogram **from the ROI geometry itself** instead of deriving statistics from the clipped raster preview.

## Current workflow

1. Read ROI layer from the current QGIS project
2. Read raster layer from the current QGIS project
3. Add a temporary feature UID field for safe per-feature matching during processing
4. Run **zonal histogram** for each ROI feature
5. Read labels and colors from renderer or RAT
6. Build:
   - combined summary
   - per-feature statistics
7. Optionally write class percentages to the original ROI attribute table
8. Optionally export a full HTML report
9. Optionally add a clipped raster preview to the project for visual inspection

## Requirements

- QGIS **3.40** or newer recommended
- Classified raster, preferably:
  - single band
  - integer class values
  - paletted renderer or raster attribute table
- Polygon ROI layer

## Installation

Copy the plugin folder into your QGIS profile plugin directory, for example:

```text
C:\Users\<USER>\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\Roi_raster_histogram
```

The folder should contain at least:

```text
Roi_raster_histogram/
├── __init__.py
├── metadata.txt
└── roi_raster_histogram.py
```

Then:

1. Restart QGIS
2. Open **Plugins > Manage and Install Plugins**
3. Enable **ROI Raster Histogram**

## Usage

1. Load a polygon ROI layer into QGIS
2. Load a classified raster layer into QGIS
3. Open the plugin
4. Select:
   - ROI polygon layer
   - raster layer
   - band
   - feature label field
5. Optional:
   - enable clipped raster preview
   - enable writing class percentages to ROI attribute table
6. Click **Run**
7. Review:
   - **Combined summary** tab
   - **Feature details** tab
8. Optionally export the report to HTML

## Plugin interface

### Combined summary

This tab shows:

- aggregated class histogram for all selected ROI features together
- combined result table with:
  - class value
  - class label
  - pixel count
  - percent share in all ROI pixels

This view is useful for understanding the overall class composition across the full ROI layer.

### Feature details

This tab shows:

- feature selector
- Previous / Next buttons
- selected feature summary
- per-feature histogram
- per-feature result table

This view is intended for actual inspection of individual ROI objects.

## Output fields shown in tables

The plugin reports:

- **Value** – raster class value
- **Label** – class label from renderer or RAT
- **Pixel count** – number of pixels inside ROI
- **% ROI** – percentage share of a class inside a specific ROI or in the combined ROI total

## Writing results to the ROI attribute table

When **Write class percentages to ROI attribute table** is enabled, the plugin writes summary statistics to the original ROI layer.

### General fields

The following helper fields are created when missing:

- `rh_totpx` – total classified pixels in the feature
- `rh_domval` – dominant class value
- `rh_domlbl` – dominant class label
- `rh_dompct` – dominant class percentage

### Class percentage fields

For each detected class, the plugin creates **one percentage field** in the ROI attribute table.

Field names are based on class labels and shortened when necessary.

Examples:

- `p_Akermark`
- `p_Sjo`
- `p_class001`

The exact field name depends on:

- label length
- allowed field-name length
- uniqueness requirements

This means the attribute table is stored in a **wide format**:

- one ROI feature = one row
- one class percentage = one column

This is useful for:

- filtering polygons by class share
- styling polygons by percentage of a class
- quick GIS analysis directly in the attribute table

## HTML export

The HTML export includes:

- ROI layer name
- raster layer name
- band information
- selected feature label field
- overall summary
- combined chart
- combined result table
- per-feature overview table
- per-feature sections with:
  - navigation links
  - per-feature metadata
  - per-feature chart
  - per-feature result table

This makes the report useful for browser viewing, documentation, sharing, or printing to PDF.

## Notes and limitations

- Best suited for **categorical rasters**
- Designed mainly for **single-band classified rasters**
- Labels depend on renderer or RAT availability
- If raster styling is unusual, labels may fall back to raw raster values
- The clipped raster is only a **visual preview** and does **not** drive the histogram calculation
- Field names written to the ROI table may be shortened for compatibility
- Shapefiles have stronger field-name limitations than GeoPackage
- **GeoPackage** is the recommended ROI storage format when writing results back to attributes

## Example use cases

- Land cover composition inside planning polygons
- Habitat share inside ecological study areas
- Landscape structure summaries for multiple ROI features
- Per-polygon classified raster statistics for environmental workflows
- Writing class percentage metrics back to polygons for mapping and filtering

## Current strengths

- Works directly on project layers
- Handles multiple ROI polygons
- Supports per-feature review in the plugin window
- Supports navigation across analyzed features
- Supports HTML reporting
- Supports writing reusable percentage fields back to the ROI layer

## Possible future improvements

- Automatic map selection / zoom to current feature in the details tab
- CSV export
- XLSX export
- Copy current feature result to clipboard
- Sorting options in tables
- Better support for additional raster renderer types
- Optional chart image export
- Optional selection-only processing

## Recommended data setup

Best results are obtained when:

- ROI layer is stored as **GeoPackage**
- raster is a **classified categorical raster**
- classes are represented using:
  - a **paletted renderer**, or
  - a **Raster Attribute Table**

## License

Choose the license you want for GitHub, for example:

- MIT License
- GPL-3.0

## Author

Jakub Pelka
