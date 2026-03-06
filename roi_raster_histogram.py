# -*- coding: utf-8 -*-

import math
import html
from datetime import datetime
import processing

from qgis.PyQt.QtCore import Qt, QSize
from qgis.PyQt.QtGui import QColor, QPainter, QPen, QBrush
from qgis.PyQt.QtWidgets import (
    QAction,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from qgis.core import (
    Qgis,
    QgsProject,
    QgsRasterAttributeTable,
    QgsRasterLayer,
    QgsVectorLayer,
    QgsPalettedRasterRenderer,
)


class HistogramWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows = []
        self.setMinimumHeight(280)

    def minimumSizeHint(self):
        return QSize(640, 280)

    def set_rows(self, rows):
        self.rows = rows or []
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), Qt.white)

        rect = self.rect().adjusted(60, 20, -20, -100)
        if rect.width() <= 0 or rect.height() <= 0:
            return

        if not self.rows:
            painter.setPen(Qt.darkGray)
            painter.drawText(self.rect(), Qt.AlignCenter, "Brak danych do wyświetlenia")
            return

        rows = sorted(self.rows, key=lambda r: r["count"], reverse=True)
        max_count = max(r["count"] for r in rows) if rows else 1
        if max_count <= 0:
            max_count = 1

        painter.setPen(QPen(Qt.black, 1))
        painter.drawLine(rect.left(), rect.bottom(), rect.right(), rect.bottom())
        painter.drawLine(rect.left(), rect.top(), rect.left(), rect.bottom())

        for i in range(6):
            y_ratio = i / 5.0
            y = rect.bottom() - rect.height() * y_ratio
            y_val = max_count * y_ratio
            painter.setPen(QPen(QColor(225, 225, 225), 1))
            painter.drawLine(rect.left(), int(y), rect.right(), int(y))
            painter.setPen(Qt.black)
            painter.drawText(5, int(y) + 5, f"{int(round(y_val))}")

        n = len(rows)
        gap = 8
        usable_width = rect.width() - gap * (n + 1)
        bar_width = max(12, usable_width / max(n, 1))

        x = rect.left() + gap
        for row in rows:
            h = 0 if max_count == 0 else (row["count"] / max_count) * rect.height()
            y = rect.bottom() - h
            color = row.get("color") or QColor(100, 149, 237)

            painter.setPen(QPen(Qt.black, 1))
            painter.setBrush(QBrush(color))
            painter.drawRect(int(x), int(y), int(bar_width), int(h))

            painter.setPen(Qt.black)
            painter.drawText(int(x), int(y) - 6, int(bar_width), 14, Qt.AlignCenter, f'{row["percent"]:.1f}%')

            label = row["label"]
            if len(label) > 16:
                label = label[:14] + "…"

            painter.save()
            painter.translate(int(x + bar_width / 2), rect.bottom() + 28)
            painter.rotate(-45)
            painter.drawText(0, 0, label)
            painter.restore()

            x += bar_width + gap


class RoiRasterHistogramDialog(QDialog):
    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.setWindowTitle("ROI Raster Histogram")
        self.resize(980, 720)

        self.roi_combo = QComboBox()
        self.raster_combo = QComboBox()
        self.band_combo = QComboBox()
        self.add_clipped_checkbox = QCheckBox("Dodaj przycięty raster do projektu")
        self.summary_label = QLabel("Wskaż warstwę ROI i raster z projektu, a następnie uruchom analizę.")
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Wartość", "Etykieta", "Liczba pikseli", "% ROI"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.chart = HistogramWidget()

        self.last_rows = []
        self.last_total_count = 0
        self.last_roi_name = ""
        self.last_raster_name = ""
        self.last_band_label = ""
        self.last_summary_text = ""

        self._build_ui()
        self._refresh_layer_combos()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        grid = QGridLayout()

        refresh_btn = QPushButton("Odśwież listę warstw")
        refresh_btn.clicked.connect(self._refresh_layer_combos)

        self.raster_combo.currentIndexChanged.connect(self._refresh_band_combo)

        grid.addWidget(QLabel("ROI (warstwa poligonowa z projektu):"), 0, 0)
        grid.addWidget(self.roi_combo, 0, 1, 1, 2)

        grid.addWidget(QLabel("Raster klasowy (warstwa z projektu):"), 1, 0)
        grid.addWidget(self.raster_combo, 1, 1, 1, 2)

        grid.addWidget(QLabel("Band:"), 2, 0)
        grid.addWidget(self.band_combo, 2, 1)
        grid.addWidget(self.add_clipped_checkbox, 2, 2)

        layout.addLayout(grid)
        layout.addWidget(refresh_btn)
        layout.addWidget(self.summary_label)

        splitter = QSplitter(Qt.Vertical)
        table_wrap = QWidget()
        table_layout = QVBoxLayout(table_wrap)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.addWidget(self.table)
        splitter.addWidget(table_wrap)
        splitter.addWidget(self.chart)
        splitter.setSizes([320, 360])
        layout.addWidget(splitter)

        btn_row = QHBoxLayout()

        export_btn = QPushButton("Eksport HTML")
        export_btn.clicked.connect(self.export_html)

        run_btn = QPushButton("Uruchom")
        run_btn.clicked.connect(self.run_analysis)

        close_btn = QPushButton("Zamknij")
        close_btn.clicked.connect(self.close)

        btn_row.addWidget(export_btn)
        btn_row.addStretch()
        btn_row.addWidget(run_btn)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def showEvent(self, event):
        self._refresh_layer_combos()
        super().showEvent(event)

    def _clear_results(self):
        self.last_rows = []
        self.last_total_count = 0
        self.last_summary_text = ""
        self.table.setRowCount(0)
        self.chart.set_rows([])

    def _refresh_layer_combos(self):
        current_roi = self.roi_combo.currentData()
        current_raster = self.raster_combo.currentData()

        self.roi_combo.blockSignals(True)
        self.raster_combo.blockSignals(True)

        self.roi_combo.clear()
        self.raster_combo.clear()

        layers = list(QgsProject.instance().mapLayers().values())
        layers.sort(key=lambda lyr: lyr.name().lower())

        for layer in layers:
            if isinstance(layer, QgsVectorLayer) and layer.isValid():
                if layer.geometryType() == Qgis.GeometryType.Polygon:
                    self.roi_combo.addItem(layer.name(), layer.id())

            if isinstance(layer, QgsRasterLayer) and layer.isValid():
                self.raster_combo.addItem(layer.name(), layer.id())

        self._restore_combo_selection(self.roi_combo, current_roi)
        self._restore_combo_selection(self.raster_combo, current_raster)

        self.roi_combo.blockSignals(False)
        self.raster_combo.blockSignals(False)

        self._refresh_band_combo()

    def _restore_combo_selection(self, combo, layer_id):
        if layer_id is None:
            return
        for i in range(combo.count()):
            if combo.itemData(i) == layer_id:
                combo.setCurrentIndex(i)
                return

    def _selected_roi_layer(self):
        layer_id = self.roi_combo.currentData()
        if not layer_id:
            return None
        layer = QgsProject.instance().mapLayer(layer_id)
        return layer if isinstance(layer, QgsVectorLayer) and layer.isValid() else None

    def _selected_raster_layer(self):
        layer_id = self.raster_combo.currentData()
        if not layer_id:
            return None
        layer = QgsProject.instance().mapLayer(layer_id)
        return layer if isinstance(layer, QgsRasterLayer) and layer.isValid() else None

    def _refresh_band_combo(self):
        self.band_combo.clear()
        raster = self._selected_raster_layer()
        if raster is None:
            return

        for band in range(1, raster.bandCount() + 1):
            desc = raster.dataProvider().bandDescription(band) or f"Band {band}"
            self.band_combo.addItem(f"{band} - {desc}", band)

    def _coerce_vector_layer(self, obj, name="temp"):
        if isinstance(obj, QgsVectorLayer):
            return obj
        if isinstance(obj, str):
            layer = QgsVectorLayer(obj, name, "ogr")
            return layer if layer.isValid() else None
        return None

    def _coerce_raster_layer(self, obj, name="temp"):
        if isinstance(obj, QgsRasterLayer):
            return obj
        if isinstance(obj, str):
            layer = QgsRasterLayer(obj, name)
            return layer if layer.isValid() else None
        return None

    def _normalize_value(self, value):
        try:
            val = float(value)
        except Exception:
            return value
        if math.isfinite(val) and abs(val - round(val)) < 1e-9:
            return int(round(val))
        return val

    def _parse_value_from_field_suffix(self, suffix):
        try:
            return int(suffix)
        except Exception:
            pass
        try:
            return float(suffix)
        except Exception:
            return suffix

    def _find_usage_index(self, usages, target_usage):
        for idx, usage in enumerate(usages):
            if usage == target_usage:
                return idx
        return -1

    def _build_label_maps_from_renderer(self, raster_layer):
        label_map = {}
        color_map = {}

        renderer = raster_layer.renderer()
        if renderer is None:
            return label_map, color_map

        if isinstance(renderer, QgsPalettedRasterRenderer):
            try:
                for cls in renderer.classes():
                    value = self._normalize_value(cls.value)
                    label = cls.label if cls.label not in (None, "") else str(value)
                    label_map[value] = str(label)
                    color_map[value] = cls.color
                if label_map:
                    return label_map, color_map
            except Exception:
                pass

        try:
            if hasattr(renderer, "classes"):
                for cls in renderer.classes():
                    value = self._normalize_value(getattr(cls, "value", None))
                    label = getattr(cls, "label", None)
                    color = getattr(cls, "color", None)
                    if value is None:
                        continue
                    label_map[value] = str(label) if label not in (None, "") else str(value)
                    if color is not None:
                        color_map[value] = color
        except Exception:
            pass

        return label_map, color_map

    def _build_label_maps_from_rat(self, raster_layer, band):
        label_map = {}
        color_map = {}

        rat = None
        try:
            rat = raster_layer.attributeTable(band)
        except Exception:
            rat = None

        if rat is None:
            try:
                if raster_layer.canCreateRasterAttributeTable():
                    rat = QgsRasterAttributeTable.createFromRaster(raster_layer)
            except Exception:
                rat = None

        if rat is None:
            return label_map, color_map

        try:
            if not rat.isValid():
                return label_map, color_map
            rows = rat.orderedRows()
            usages = list(rat.usages())
        except Exception:
            return label_map, color_map

        idx_name = self._find_usage_index(usages, Qgis.RasterAttributeTableFieldUsage.Name)
        idx_minmax = self._find_usage_index(usages, Qgis.RasterAttributeTableFieldUsage.MinMax)
        idx_min = self._find_usage_index(usages, Qgis.RasterAttributeTableFieldUsage.Min)
        idx_max = self._find_usage_index(usages, Qgis.RasterAttributeTableFieldUsage.Max)
        idx_red = self._find_usage_index(usages, Qgis.RasterAttributeTableFieldUsage.Red)
        idx_green = self._find_usage_index(usages, Qgis.RasterAttributeTableFieldUsage.Green)
        idx_blue = self._find_usage_index(usages, Qgis.RasterAttributeTableFieldUsage.Blue)
        idx_alpha = self._find_usage_index(usages, Qgis.RasterAttributeTableFieldUsage.Alpha)

        for row in rows:
            label = None
            if idx_name != -1 and idx_name < len(row):
                try:
                    label = str(row[idx_name])
                except Exception:
                    label = None

            color = None
            if min(idx_red, idx_green, idx_blue) != -1:
                try:
                    alpha = 255
                    if idx_alpha != -1 and idx_alpha < len(row):
                        alpha = int(row[idx_alpha])
                    color = QColor(int(row[idx_red]), int(row[idx_green]), int(row[idx_blue]), alpha)
                except Exception:
                    color = None

            if idx_minmax != -1 and idx_minmax < len(row):
                value = self._normalize_value(row[idx_minmax])
                label_map[value] = label or str(value)
                if color is not None:
                    color_map[value] = color
                continue

            if idx_min != -1 and idx_max != -1 and idx_min < len(row) and idx_max < len(row):
                try:
                    vmin = int(round(float(row[idx_min])))
                    vmax = int(round(float(row[idx_max])))
                    text = label or (f"{vmin}-{vmax}" if vmin != vmax else str(vmin))
                    for v in range(vmin, vmax + 1):
                        label_map[v] = text
                        if color is not None:
                            color_map[v] = color
                except Exception:
                    pass

        return label_map, color_map

    def _build_label_maps(self, raster_layer, band):
        label_map = {}
        color_map = {}

        renderer_labels, renderer_colors = self._build_label_maps_from_renderer(raster_layer)
        rat_labels, rat_colors = self._build_label_maps_from_rat(raster_layer, band)

        label_map.update(rat_labels)
        color_map.update(rat_colors)

        label_map.update(renderer_labels)
        color_map.update(renderer_colors)

        return label_map, color_map

    def _populate_table(self, rows):
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            items = [
                QTableWidgetItem(str(row["value"])),
                QTableWidgetItem(row["label"]),
                QTableWidgetItem(str(row["count"])),
                QTableWidgetItem(f'{row["percent"]:.2f}'),
            ]
            for item in items:
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)

            self.table.setItem(r, 0, items[0])
            self.table.setItem(r, 1, items[1])
            self.table.setItem(r, 2, items[2])
            self.table.setItem(r, 3, items[3])

    def _add_preview_clip(self, roi_layer, raster_layer):
        try:
            clip_result = processing.run(
                "gdal:cliprasterbymasklayer",
                {
                    "INPUT": raster_layer,
                    "MASK": roi_layer,
                    "SOURCE_CRS": None,
                    "TARGET_CRS": None,
                    "TARGET_EXTENT": None,
                    "NODATA": None,
                    "ALPHA_BAND": False,
                    "CROP_TO_CUTLINE": True,
                    "KEEP_RESOLUTION": True,
                    "SET_RESOLUTION": False,
                    "X_RESOLUTION": None,
                    "Y_RESOLUTION": None,
                    "MULTITHREADING": False,
                    "OPTIONS": "",
                    "DATA_TYPE": 0,
                    "EXTRA": "",
                    "OUTPUT": "TEMPORARY_OUTPUT",
                },
            )
            clipped_layer = self._coerce_raster_layer(clip_result.get("OUTPUT"), "ROI clip preview")
            if clipped_layer is not None and clipped_layer.isValid():
                QgsProject.instance().addMapLayer(clipped_layer)
        except Exception:
            pass

    def _color_to_hex(self, color):
        if isinstance(color, QColor):
            return color.name()
        return "#6495ed"

    def export_html(self):
        if not self.last_rows:
            QMessageBox.information(self, "Brak danych", "Najpierw uruchom analizę, a potem wykonaj eksport.")
            return

        default_name = f"roi_histogram_{self.last_roi_name or 'roi'}.html"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Zapisz raport HTML",
            default_name,
            "HTML (*.html)",
        )
        if not path:
            return

        if not path.lower().endswith(".html"):
            path += ".html"

        rows_html = []
        chart_html = []

        for row in self.last_rows:
            color_hex = self._color_to_hex(row.get("color"))
            value_txt = html.escape(str(row["value"]))
            label_txt = html.escape(str(row["label"]))

            rows_html.append(
                f"""
                <tr>
                    <td>{value_txt}</td>
                    <td><span class="swatch" style="background:{color_hex};"></span>{label_txt}</td>
                    <td>{row["count"]}</td>
                    <td>{row["percent"]:.2f}%</td>
                </tr>
                """
            )

            chart_html.append(
                f"""
                <div class="bar-row">
                    <div class="bar-label">{label_txt}</div>
                    <div class="bar-wrap">
                        <div class="bar" style="width:{row['percent']:.2f}%; background:{color_hex};"></div>
                    </div>
                    <div class="bar-value">{row['percent']:.2f}% ({row['count']})</div>
                </div>
                """
            )

        doc = f"""<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="utf-8">
<title>ROI Raster Histogram Report</title>
<style>
body {{
    font-family: Arial, Helvetica, sans-serif;
    margin: 24px;
    color: #222;
}}
h1, h2 {{
    margin-bottom: 8px;
}}
.meta {{
    margin-bottom: 20px;
    padding: 14px 16px;
    background: #f5f7fa;
    border: 1px solid #d9dee5;
    border-radius: 8px;
}}
.meta div {{
    margin: 4px 0;
}}
table {{
    border-collapse: collapse;
    width: 100%;
    margin-top: 12px;
}}
th, td {{
    border: 1px solid #d9dee5;
    padding: 8px 10px;
    text-align: left;
}}
th {{
    background: #f0f3f7;
}}
.swatch {{
    display: inline-block;
    width: 14px;
    height: 14px;
    margin-right: 8px;
    vertical-align: middle;
    border: 1px solid #888;
}}
.bar-chart {{
    margin-top: 16px;
    border: 1px solid #d9dee5;
    border-radius: 8px;
    padding: 16px;
    background: #fff;
}}
.bar-row {{
    display: grid;
    grid-template-columns: 140px 1fr 120px;
    gap: 10px;
    align-items: center;
    margin: 8px 0;
}}
.bar-label {{
    font-weight: 600;
}}
.bar-wrap {{
    background: #eef2f7;
    height: 20px;
    border-radius: 4px;
    overflow: hidden;
}}
.bar {{
    height: 100%;
}}
.bar-value {{
    text-align: right;
    white-space: nowrap;
}}
.small {{
    color: #666;
    font-size: 12px;
}}
</style>
</head>
<body>
<h1>ROI Raster Histogram</h1>

<div class="meta">
    <div><strong>ROI:</strong> {html.escape(self.last_roi_name)}</div>
    <div><strong>Raster:</strong> {html.escape(self.last_raster_name)}</div>
    <div><strong>Band:</strong> {html.escape(self.last_band_label)}</div>
    <div><strong>Podsumowanie:</strong> {html.escape(self.last_summary_text)}</div>
    <div><strong>Eksport:</strong> {html.escape(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))}</div>
</div>

<h2>Wykres</h2>
<div class="bar-chart">
    {''.join(chart_html)}
</div>

<h2>Tabela wyników</h2>
<table>
    <thead>
        <tr>
            <th>Wartość</th>
            <th>Etykieta</th>
            <th>Liczba pikseli</th>
            <th>% ROI</th>
        </tr>
    </thead>
    <tbody>
        {''.join(rows_html)}
    </tbody>
</table>

<p class="small">Histogram liczony bezpośrednio z geometrii ROI, bez wpływu pikseli spoza poligonu.</p>
</body>
</html>
"""

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(doc)
        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Nie udało się zapisać HTML:\n{e}")
            return

        QMessageBox.information(self, "Gotowe", f"Raport zapisano:\n{path}")

    def run_analysis(self):
        roi_layer = self._selected_roi_layer()
        raster_layer = self._selected_raster_layer()

        self._clear_results()

        if roi_layer is None or raster_layer is None:
            QMessageBox.warning(self, "Brak danych", "Wskaż warstwę ROI i raster z projektu.")
            return

        if roi_layer.geometryType() != Qgis.GeometryType.Polygon:
            QMessageBox.critical(self, "Błąd", "ROI musi być warstwą poligonową.")
            return

        band = self.band_combo.currentData()
        if band is None:
            band = 1

        try:
            dissolved_result = processing.run(
                "native:dissolve",
                {
                    "INPUT": roi_layer,
                    "FIELD": [],
                    "SEPARATE_DISJOINT": False,
                    "OUTPUT": "TEMPORARY_OUTPUT",
                },
            )
        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Błąd podczas scalania ROI:\n{e}")
            return

        dissolved_roi = self._coerce_vector_layer(dissolved_result.get("OUTPUT"), "ROI dissolved")
        if dissolved_roi is None or not dissolved_roi.isValid():
            QMessageBox.critical(self, "Błąd", "Nie udało się utworzyć warstwy ROI po dissolve.")
            return

        if self.add_clipped_checkbox.isChecked():
            self._add_preview_clip(dissolved_roi, raster_layer)

        prefix = "H_"

        try:
            zh_result = processing.run(
                "native:zonalhistogram",
                {
                    "INPUT_RASTER": raster_layer,
                    "RASTER_BAND": band,
                    "INPUT_VECTOR": dissolved_roi,
                    "COLUMN_PREFIX": prefix,
                    "OUTPUT": "TEMPORARY_OUTPUT",
                },
            )
        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Błąd podczas liczenia histogramu:\n{e}")
            return

        output_layer = self._coerce_vector_layer(zh_result.get("OUTPUT"), "ROI histogram")
        if output_layer is None or not output_layer.isValid():
            QMessageBox.critical(self, "Błąd", "Nie udało się odczytać warstwy wynikowej histogramu.")
            return

        feature = next(output_layer.getFeatures(), None)
        if feature is None:
            QMessageBox.critical(self, "Błąd", "Warstwa wynikowa histogramu jest pusta.")
            return

        label_map, color_map = self._build_label_maps(raster_layer, band)

        rows = []
        total_count = 0

        for field in output_layer.fields():
            fname = field.name()
            if not fname.startswith(prefix):
                continue

            raw_value = fname[len(prefix):]
            value = self._parse_value_from_field_suffix(raw_value)

            try:
                count_raw = feature[fname]
                if count_raw is None:
                    continue
                count = int(round(float(count_raw)))
            except Exception:
                continue

            if count <= 0:
                continue

            total_count += count
            rows.append(
                {
                    "value": value,
                    "label": label_map.get(value, str(value)),
                    "count": count,
                    "percent": 0.0,
                    "color": color_map.get(value),
                }
            )

        if total_count == 0:
            self.summary_label.setText("ROI nie zawiera pikseli klasowych albo wynik jest pusty.")
            return

        rows.sort(key=lambda r: r["count"], reverse=True)
        for row in rows:
            row["percent"] = (row["count"] / total_count) * 100.0

        self._populate_table(rows)
        self.chart.set_rows(rows)

        self.last_rows = rows
        self.last_total_count = total_count
        self.last_roi_name = roi_layer.name()
        self.last_raster_name = raster_layer.name()
        self.last_band_label = self.band_combo.currentText()
        self.last_summary_text = (
            f"Piksele w ROI: {total_count} | Liczba klas w ROI: {len(rows)} | "
            f"Histogram liczony bezpośrednio z geometrii ROI"
        )

        self.summary_label.setText(self.last_summary_text)


class RoiRasterHistogramPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dialog = None

    def initGui(self):
        self.action = QAction("ROI Raster Histogram", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addPluginToMenu("&ROI Raster Histogram", self.action)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        if self.action:
            self.iface.removePluginMenu("&ROI Raster Histogram", self.action)
            self.iface.removeToolBarIcon(self.action)

    def run(self):
        if self.dialog is None:
            self.dialog = RoiRasterHistogramDialog(self.iface, self.iface.mainWindow())
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()