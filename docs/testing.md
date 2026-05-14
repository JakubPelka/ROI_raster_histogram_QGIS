# Testing checklist

Use this checklist before tagging a release or publishing a ZIP package.

## 1. Installation tests

- [ ] Install by copying the plugin folder into the QGIS profile plugin directory.
- [ ] Install from ZIP using QGIS Plugin Manager.
- [ ] Test on a clean QGIS profile.
- [ ] Confirm the plugin appears as **ROI Raster Histogram**.
- [ ] Confirm the plugin opens from menu and toolbar.

## 2. Basic workflow

- [ ] Load a polygon ROI layer.
- [ ] Load a classified raster layer.
- [ ] Open the plugin.
- [ ] Select ROI layer.
- [ ] Select raster layer.
- [ ] Select raster band.
- [ ] Select feature label field.
- [ ] Run analysis.
- [ ] Confirm combined summary appears.
- [ ] Confirm per-feature details appear.
- [ ] Confirm Previous / Next feature navigation works.

## 3. Result correctness

- [ ] Test with one polygon fully inside one raster class.
- [ ] Test with one polygon crossing several raster classes.
- [ ] Test with multiple ROI polygons.
- [ ] Test polygon with no classified pixels.
- [ ] Test polygons partly outside raster extent.
- [ ] Compare results with expected class counts on a small synthetic raster.

## 4. Class labels and colors

- [ ] Test raster with paletted renderer.
- [ ] Test raster with Raster Attribute Table.
- [ ] Test raster without labels.
- [ ] Confirm fallback labels are raw raster values.
- [ ] Confirm chart colors are reasonable.

## 5. Attribute writing

Use a copy of the ROI layer.

- [ ] Enable writing class percentages.
- [ ] Confirm helper fields are created.
- [ ] Confirm class percentage fields are created.
- [ ] Confirm values are written to correct features.
- [ ] Confirm existing fields are not unintentionally overwritten.
- [ ] Test with GeoPackage.
- [ ] Test with Shapefile only if needed, because field names are limited.

## 6. HTML export

- [ ] Export HTML report.
- [ ] Open report in a browser.
- [ ] Confirm combined chart appears.
- [ ] Confirm combined table appears.
- [ ] Confirm per-feature overview appears.
- [ ] Confirm per-feature sections appear.
- [ ] Confirm navigation links work.
- [ ] Print to PDF from browser if needed.

## 7. Clipped raster preview

- [ ] Enable clipped raster preview.
- [ ] Confirm preview layer is added to the QGIS project.
- [ ] Confirm preview is not used as the source of histogram statistics.

## 8. Error handling

- [ ] Run with no ROI selected.
- [ ] Run with no raster selected.
- [ ] Run with invalid/non-polygon ROI layer.
- [ ] Run with empty ROI layer.
- [ ] Run with unsupported raster styling.
- [ ] Confirm messages are understandable.

## 9. Public repository safety

Before pushing:

- [ ] No private geodata.
- [ ] No large rasters.
- [ ] No generated reports.
- [ ] No local QGIS profile paths except generic examples.
- [ ] No ZIP backups.
- [ ] No credentials or tokens.
