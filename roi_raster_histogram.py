# -*- coding: utf-8 -*-

import math
import html
from datetime import datetime
import processing

from qgis.PyQt.QtCore import Qt, QSize, QVariant
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
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from qgis.core import (
    Qgis,
    QgsField,
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
        self.setMinimumHeight(300)

    def minimumSizeHint(self):
        return QSize(640, 300)

    def set_rows(self, rows):
        self.rows = rows or []
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), Qt.white)

        rect = self.rect().adjusted(60, 20, -20, -150)
        if rect.width() <= 0 or rect.height() <= 0:
            return

        if not self.rows:
            painter.setPen(Qt.darkGray)
            painter.drawText(self.rect(), Qt.AlignCenter, "No data to display")
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

            pct_y = max(y - 18, rect.top() + 12)
            painter.setPen(Qt.black)
            painter.drawText(int(x), int(pct_y), int(bar_width), 14, Qt.AlignCenter, f'{row["percent"]:.1f}%')

            label = row["label"]
            if len(label) > 28:
                label = label[:26] + "…"

            painter.save()
            painter.translate(int(x + bar_width / 2), rect.bottom() + 8)
            painter.rotate(90)
            painter.drawText(0, 0, label)
            painter.restore()

            x += bar_width + gap


class RoiRasterHistogramDialog(QDialog):
    FEATURE_ID_SENTINEL = "__feature_id__"
    UID_FIELD = "__rh_uid"

    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.setWindowTitle("ROI Raster Histogram")
        self.resize(1120, 800)

        self.roi_combo = QComboBox()
        self.raster_combo = QComboBox()
        self.band_combo = QComboBox()
        self.id_field_combo = QComboBox()
        self.add_clipped_checkbox = QCheckBox("Add clipped raster preview to project")
        self.write_attributes_checkbox = QCheckBox("Write class percentages to ROI attribute table")
        self.summary_label = QLabel("Select an ROI layer and a raster layer from the project, then run the analysis.")

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Value", "Label", "Pixel count", "% ROI"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.chart = HistogramWidget()

        self.tabs = QTabWidget()
        self.feature_combo = QComboBox()
        self.feature_combo.currentIndexChanged.connect(self._on_feature_changed)
        self.prev_feature_btn = QPushButton("Previous")
        self.prev_feature_btn.clicked.connect(self._show_previous_feature)
        self.next_feature_btn = QPushButton("Next")
        self.next_feature_btn.clicked.connect(self._show_next_feature)
        self.detail_info_label = QLabel("No feature selected")
        self.detail_meta_label = QLabel("Run the analysis to view per-feature details.")
        self.detail_meta_label.setWordWrap(True)
        self.detail_chart = HistogramWidget()
        self.detail_table = QTableWidget(0, 4)
        self.detail_table.setHorizontalHeaderLabels(["Value", "Label", "Pixel count", "% ROI"])
        self.detail_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self.last_rows = []
        self.last_total_count = 0
        self.last_roi_name = ""
        self.last_raster_name = ""
        self.last_band_label = ""
        self.last_summary_text = ""
        self.last_feature_stats = []
        self.last_identifier_field = self.FEATURE_ID_SENTINEL

        self._build_ui()
        self._refresh_layer_combos()
        self._show_empty_details()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        grid = QGridLayout()

        refresh_btn = QPushButton("Refresh layer list")
        refresh_btn.clicked.connect(self._refresh_layer_combos)

        self.raster_combo.currentIndexChanged.connect(self._refresh_band_combo)
        self.roi_combo.currentIndexChanged.connect(self._refresh_id_field_combo)

        grid.addWidget(QLabel("ROI (polygon layer from project):"), 0, 0)
        grid.addWidget(self.roi_combo, 0, 1, 1, 3)

        grid.addWidget(QLabel("Classified raster (layer from project):"), 1, 0)
        grid.addWidget(self.raster_combo, 1, 1, 1, 3)

        grid.addWidget(QLabel("Band:"), 2, 0)
        grid.addWidget(self.band_combo, 2, 1)
        grid.addWidget(QLabel("Feature label field:"), 2, 2)
        grid.addWidget(self.id_field_combo, 2, 3)

        grid.addWidget(self.add_clipped_checkbox, 3, 1)
        grid.addWidget(self.write_attributes_checkbox, 3, 2, 1, 2)

        layout.addLayout(grid)
        layout.addWidget(refresh_btn)
        layout.addWidget(self.summary_label)

        summary_tab = QWidget()
        summary_layout = QVBoxLayout(summary_tab)
        summary_splitter = QSplitter(Qt.Vertical)
        table_wrap = QWidget()
        table_layout = QVBoxLayout(table_wrap)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.addWidget(self.table)
        summary_splitter.addWidget(table_wrap)
        summary_splitter.addWidget(self.chart)
        summary_splitter.setSizes([320, 420])
        summary_layout.addWidget(summary_splitter)

        details_tab = QWidget()
        details_layout = QVBoxLayout(details_tab)
        details_top = QHBoxLayout()
        details_top.addWidget(QLabel("Feature:"))
        details_top.addWidget(self.feature_combo, 1)
        details_top.addWidget(self.prev_feature_btn)
        details_top.addWidget(self.next_feature_btn)
        details_layout.addLayout(details_top)
        details_layout.addWidget(self.detail_info_label)
        details_layout.addWidget(self.detail_meta_label)
        details_splitter = QSplitter(Qt.Vertical)
        details_splitter.addWidget(self.detail_chart)
        details_table_wrap = QWidget()
        details_table_layout = QVBoxLayout(details_table_wrap)
        details_table_layout.setContentsMargins(0, 0, 0, 0)
        details_table_layout.addWidget(self.detail_table)
        details_splitter.addWidget(details_table_wrap)
        details_splitter.setSizes([380, 260])
        details_layout.addWidget(details_splitter)

        self.tabs.addTab(summary_tab, "Combined summary")
        self.tabs.addTab(details_tab, "Feature details")
        layout.addWidget(self.tabs)

        btn_row = QHBoxLayout()
        export_btn = QPushButton("Export HTML")
        export_btn.clicked.connect(self.export_html)
        run_btn = QPushButton("Run")
        run_btn.clicked.connect(self.run_analysis)
        close_btn = QPushButton("Close")
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
        self.last_feature_stats = []
        self.table.setRowCount(0)
        self.chart.set_rows([])
        self.detail_table.setRowCount(0)
        self.detail_chart.set_rows([])
        self.feature_combo.blockSignals(True)
        self.feature_combo.clear()
        self.feature_combo.blockSignals(False)
        self._show_empty_details()

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
            if isinstance(layer, QgsVectorLayer) and layer.isValid() and layer.geometryType() == Qgis.GeometryType.Polygon:
                self.roi_combo.addItem(layer.name(), layer.id())
            if isinstance(layer, QgsRasterLayer) and layer.isValid():
                self.raster_combo.addItem(layer.name(), layer.id())

        self._restore_combo_selection(self.roi_combo, current_roi)
        self._restore_combo_selection(self.raster_combo, current_raster)

        self.roi_combo.blockSignals(False)
        self.raster_combo.blockSignals(False)

        self._refresh_band_combo()
        self._refresh_id_field_combo()

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
        current_band = self.band_combo.currentData()
        self.band_combo.clear()
        raster = self._selected_raster_layer()
        if raster is None:
            return
        for band in range(1, raster.bandCount() + 1):
            desc = raster.dataProvider().bandDescription(band) or f"Band {band}"
            self.band_combo.addItem(f"{band} - {desc}", band)
        if current_band is not None:
            for i in range(self.band_combo.count()):
                if self.band_combo.itemData(i) == current_band:
                    self.band_combo.setCurrentIndex(i)
                    break

    def _refresh_id_field_combo(self):
        current_value = self.id_field_combo.currentData()
        self.id_field_combo.clear()
        self.id_field_combo.addItem("[Feature ID]", self.FEATURE_ID_SENTINEL)

        roi_layer = self._selected_roi_layer()
        if roi_layer is not None:
            for field in roi_layer.fields():
                self.id_field_combo.addItem(field.name(), field.name())

        if current_value is not None:
            for i in range(self.id_field_combo.count()):
                if self.id_field_combo.itemData(i) == current_value:
                    self.id_field_combo.setCurrentIndex(i)
                    break

    def _selected_id_field(self):
        val = self.id_field_combo.currentData()
        return val or self.FEATURE_ID_SENTINEL

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

    def _feature_display_name(self, feature, id_field):
        if id_field == self.FEATURE_ID_SENTINEL:
            return f"Feature {feature.id()}"
        try:
            val = feature[id_field]
            if val in (None, ""):
                return f"Feature {feature.id()}"
            return str(val)
        except Exception:
            return f"Feature {feature.id()}"

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

    def _populate_table(self, rows, table_widget=None):
        table_widget = table_widget or self.table
        table_widget.setRowCount(len(rows))
        for r, row in enumerate(rows):
            items = [
                QTableWidgetItem(str(row["value"])),
                QTableWidgetItem(row["label"]),
                QTableWidgetItem(str(row["count"])),
                QTableWidgetItem(f'{row["percent"]:.2f}'),
            ]
            for item in items:
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            table_widget.setItem(r, 0, items[0])
            table_widget.setItem(r, 1, items[1])
            table_widget.setItem(r, 2, items[2])
            table_widget.setItem(r, 3, items[3])

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

    def _build_svg_chart(self, rows, width=980, height=420):
        if not rows:
            return "<p style='font-family:Arial; color:#666;'>No chart data available.</p>"

        rows = sorted(rows, key=lambda r: r["count"], reverse=True)
        left = 60
        top = 20
        right = 20
        bottom = 170
        plot_width = width - left - right
        plot_height = height - top - bottom
        max_count = max(1, max(r["count"] for r in rows))
        gap = 8
        n = len(rows)
        bar_width = max(12, (plot_width - gap * (n + 1)) / max(1, n))

        elements = [
            f"<rect x='0' y='0' width='{width}' height='{height}' fill='white' />",
            f"<line x1='{left}' y1='{top}' x2='{left}' y2='{top + plot_height}' stroke='black' stroke-width='1' />",
            f"<line x1='{left}' y1='{top + plot_height}' x2='{left + plot_width}' y2='{top + plot_height}' stroke='black' stroke-width='1' />",
        ]

        for i in range(6):
            ratio = i / 5.0
            y = top + plot_height - plot_height * ratio
            y_val = int(round(max_count * ratio))
            elements.append(
                f"<line x1='{left}' y1='{y:.2f}' x2='{left + plot_width}' y2='{y:.2f}' stroke='#e1e1e1' stroke-width='1' />"
            )
            elements.append(
                f"<text x='6' y='{y + 4:.2f}' font-size='12' font-family='Arial'>{y_val}</text>"
            )

        x = left + gap
        for row in rows:
            bar_height = 0 if max_count == 0 else (row["count"] / max_count) * plot_height
            y = top + plot_height - bar_height
            color = self._color_to_hex(row.get("color"))
            pct = f"{row['percent']:.1f}%"
            label_txt = str(row["label"])
            if len(label_txt) > 28:
                label_txt = label_txt[:26] + "…"
            label = html.escape(label_txt)
            cx = x + bar_width / 2.0
            pct_y = max(y - 10, top + 12)
            label_y = top + plot_height + 8

            elements.append(
                f"<rect x='{x:.2f}' y='{y:.2f}' width='{bar_width:.2f}' height='{bar_height:.2f}' fill='{color}' stroke='black' stroke-width='1' />"
            )
            elements.append(
                f"<text x='{cx:.2f}' y='{pct_y:.2f}' text-anchor='middle' font-size='12' font-family='Arial'>{pct}</text>"
            )
            elements.append(
                f"<text x='{cx:.2f}' y='{label_y:.2f}' transform='rotate(90 {cx:.2f} {label_y:.2f})' text-anchor='start' font-size='12' font-family='Arial'>{label}</text>"
            )
            x += bar_width + gap

        return (
            f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {width} {height}' width='100%' height='{height}' "
            f"preserveAspectRatio='xMidYMid meet'>{''.join(elements)}</svg>"
        )

    def _aggregate_rows_from_features(self, feature_stats):
        agg = {}
        for stat in feature_stats:
            for row in stat["rows"]:
                key = row["value"]
                if key not in agg:
                    agg[key] = {
                        "value": row["value"],
                        "label": row["label"],
                        "count": 0,
                        "percent": 0.0,
                        "color": row.get("color"),
                    }
                agg[key]["count"] += row["count"]
                if agg[key].get("color") is None and row.get("color") is not None:
                    agg[key]["color"] = row.get("color")

        total_count = sum(v["count"] for v in agg.values())
        rows = list(agg.values())
        rows.sort(key=lambda r: r["count"], reverse=True)
        if total_count > 0:
            for row in rows:
                row["percent"] = (row["count"] / total_count) * 100.0
        return rows, total_count

    def _sanitize_field_label(self, text):
        value = str(text or "").strip()
        value = "".join(ch if ch.isalnum() else "_" for ch in value)
        while "__" in value:
            value = value.replace("__", "_")
        value = value.strip("_")
        return value or "class"

    def _build_percent_field_map(self, class_info):
        used_names = set()
        field_map = {}

        for idx, info in enumerate(class_info, start=1):
            value = info["value"]
            label = info["label"]

            base = f"p_{self._sanitize_field_label(label)}"
            if len(base) > 10:
                base = base[:10]
            if base in ("p_", ""):
                base = f"p_c{idx:03d}"[:10]

            candidate = base
            if candidate.lower() in used_names:
                candidate = f"p_c{idx:03d}"[:10]

            if candidate.lower() in used_names:
                stem = candidate[:8]
                suffix = 1
                while True:
                    trial = f"{stem}{suffix}"[:10]
                    if trial.lower() not in used_names:
                        candidate = trial
                        break
                    suffix += 1

            used_names.add(candidate.lower())
            field_map[value] = candidate

        return field_map

    def _prepare_feature_stats(self, zh_layer, id_field, label_map, color_map):
        feature_stats = []
        prefix = "H_"

        for feature in zh_layer.getFeatures():
            rows = []
            total_count = 0
            for field in zh_layer.fields():
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

            if total_count <= 0:
                dominant = None
            else:
                rows.sort(key=lambda r: r["count"], reverse=True)
                for row in rows:
                    row["percent"] = (row["count"] / total_count) * 100.0
                dominant = rows[0] if rows else None

            try:
                uid = int(feature[self.UID_FIELD])
            except Exception:
                uid = feature.id()

            feature_stats.append(
                {
                    "uid": uid,
                    "display_name": self._feature_display_name(feature, id_field),
                    "rows": rows,
                    "total_count": total_count,
                    "dominant": dominant,
                }
            )

        feature_stats.sort(key=lambda s: s["display_name"].lower())
        return feature_stats

    def _write_stats_to_roi_layer(self, roi_layer, feature_stats):
        if not feature_stats:
            return True, "No feature statistics to write."

        class_map = {}
        for stat in feature_stats:
            for row in stat["rows"]:
                value = row["value"]
                if value not in class_map:
                    class_map[value] = {"value": value, "label": row["label"]}

        class_info = [class_map[value] for value in sorted(class_map.keys(), key=lambda v: str(v))]
        percent_field_map = self._build_percent_field_map(class_info)

        required_fields = [
            QgsField("rh_totpx", QVariant.Int),
            QgsField("rh_domval", QVariant.String, len=40),
            QgsField("rh_domlbl", QVariant.String, len=80),
            QgsField("rh_dompct", QVariant.Double, len=20, prec=4),
        ]

        for info in class_info:
            required_fields.append(QgsField(percent_field_map[info["value"]], QVariant.Double, len=20, prec=4))

        existing_names = {f.name() for f in roi_layer.fields()}
        new_fields = [fld for fld in required_fields if fld.name() not in existing_names]

        started_edit = False
        if not roi_layer.isEditable():
            if not roi_layer.startEditing():
                return False, "Failed to start editing the ROI layer."
            started_edit = True

        if new_fields:
            if not roi_layer.dataProvider().addAttributes(new_fields):
                if started_edit:
                    roi_layer.rollBack()
                return False, "Failed to add fields to the ROI layer."
            roi_layer.updateFields()

        field_idx = {f.name(): roi_layer.fields().indexFromName(f.name()) for f in roi_layer.fields()}
        stats_by_uid = {stat["uid"]: stat for stat in feature_stats}

        for feature in roi_layer.getFeatures():
            stat = stats_by_uid.get(feature.id())
            if stat is None:
                continue

            dominant = stat["dominant"]
            roi_layer.changeAttributeValue(feature.id(), field_idx["rh_totpx"], stat["total_count"])
            roi_layer.changeAttributeValue(feature.id(), field_idx["rh_domval"], str(dominant["value"]) if dominant else None)
            roi_layer.changeAttributeValue(feature.id(), field_idx["rh_domlbl"], dominant["label"] if dominant else None)
            roi_layer.changeAttributeValue(feature.id(), field_idx["rh_dompct"], round(dominant["percent"], 4) if dominant else 0.0)

            for info in class_info:
                roi_layer.changeAttributeValue(feature.id(), field_idx[percent_field_map[info["value"]]], 0.0)

            for row in stat["rows"]:
                roi_layer.changeAttributeValue(
                    feature.id(),
                    field_idx[percent_field_map[row["value"]]],
                    round(row["percent"], 4),
                )

        if started_edit:
            if not roi_layer.commitChanges():
                errors = "; ".join(roi_layer.commitErrors()) if hasattr(roi_layer, "commitErrors") else "Unknown commit error."
                roi_layer.rollBack()
                return False, f"Failed to commit ROI attribute updates: {errors}"

        return True, "Class percentage fields written to ROI attribute table."

    def _show_empty_details(self):
        self.detail_info_label.setText("No feature selected")
        self.detail_meta_label.setText("Run the analysis to view per-feature details.")
        self.detail_chart.set_rows([])
        self.detail_table.setRowCount(0)
        self.prev_feature_btn.setEnabled(False)
        self.next_feature_btn.setEnabled(False)

    def _set_feature_combo_from_stats(self):
        self.feature_combo.blockSignals(True)
        self.feature_combo.clear()
        for idx, stat in enumerate(self.last_feature_stats):
            self.feature_combo.addItem(stat["display_name"], idx)
        self.feature_combo.blockSignals(False)
        if self.feature_combo.count() > 0:
            self.feature_combo.setCurrentIndex(0)
            self._render_feature_detail(0)
        else:
            self._show_empty_details()

    def _update_feature_nav(self, index):
        count = len(self.last_feature_stats)
        self.prev_feature_btn.setEnabled(count > 0 and index > 0)
        self.next_feature_btn.setEnabled(count > 0 and index < count - 1)

    def _render_feature_detail(self, index):
        if index < 0 or index >= len(self.last_feature_stats):
            self._show_empty_details()
            return

        stat = self.last_feature_stats[index]
        dominant = stat["dominant"]
        self.detail_info_label.setText(
            f"Feature {index + 1} of {len(self.last_feature_stats)} | {stat['display_name']} | Pixels: {stat['total_count']}"
        )
        self.detail_meta_label.setText(
            f"Total classified pixels: {stat['total_count']} | "
            f"Dominant class value: {dominant['value'] if dominant else '-'} | "
            f"Dominant class label: {dominant['label'] if dominant else '-'} | "
            f"Dominant share: {dominant['percent']:.2f}%" if dominant else
            f"Total classified pixels: {stat['total_count']}"
        )
        self.detail_chart.set_rows(stat["rows"])
        self._populate_table(stat["rows"], self.detail_table)
        self._update_feature_nav(index)

    def _on_feature_changed(self, index):
        self._render_feature_detail(index)

    def _show_previous_feature(self):
        idx = self.feature_combo.currentIndex()
        if idx > 0:
            self.feature_combo.setCurrentIndex(idx - 1)

    def _show_next_feature(self):
        idx = self.feature_combo.currentIndex()
        if idx < self.feature_combo.count() - 1:
            self.feature_combo.setCurrentIndex(idx + 1)

    def export_html(self):
        if not self.last_rows:
            QMessageBox.information(self, "No data", "Run the analysis first, then export the report.")
            return

        default_name = f"roi_histogram_{self.last_roi_name or 'roi'}.html"
        path, _ = QFileDialog.getSaveFileName(self, "Save HTML report", default_name, "HTML (*.html)")
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
                    <td><span class=\"swatch\" style=\"background:{color_hex};\"></span>{label_txt}</td>
                    <td>{row['count']}</td>
                    <td>{row['percent']:.2f}%</td>
                </tr>
                """
            )
            chart_html.append(
                f"""
                <div class=\"bar-row\">
                    <div class=\"bar-label\">{label_txt}</div>
                    <div class=\"bar-wrap\"><div class=\"bar\" style=\"width:{row['percent']:.2f}%; background:{color_hex};\"></div></div>
                    <div class=\"bar-value\">{row['percent']:.2f}% ({row['count']})</div>
                </div>
                """
            )

        overview_rows = []
        sections_html = []
        total_features = len(self.last_feature_stats)

        for i, stat in enumerate(self.last_feature_stats, start=1):
            section_id = f"feature-{i}"
            prev_link = f"#feature-{i - 1}" if i > 1 else "#overview"
            next_link = f"#feature-{i + 1}" if i < total_features else "#top"
            dominant = stat["dominant"]

            if dominant:
                overview_rows.append(
                    f"""
                    <tr>
                        <td><a href=\"#{section_id}\">{html.escape(stat['display_name'])}</a></td>
                        <td>{stat['total_count']}</td>
                        <td>{html.escape(dominant['label'])}</td>
                        <td>{dominant['percent']:.2f}%</td>
                    </tr>
                    """
                )
            else:
                overview_rows.append(
                    f"""
                    <tr>
                        <td><a href=\"#{section_id}\">{html.escape(stat['display_name'])}</a></td>
                        <td>{stat['total_count']}</td>
                        <td>-</td>
                        <td>-</td>
                    </tr>
                    """
                )

            feature_svg = self._build_svg_chart(stat["rows"], width=980, height=420)
            feature_table = []
            for row in stat["rows"]:
                color_hex = self._color_to_hex(row.get("color"))
                value_txt = html.escape(str(row["value"]))
                label_txt = html.escape(str(row["label"]))
                feature_table.append(
                    f"""
                    <tr>
                        <td>{value_txt}</td>
                        <td><span class=\"swatch\" style=\"background:{color_hex};\"></span>{label_txt}</td>
                        <td>{row['count']}</td>
                        <td>{row['percent']:.2f}%</td>
                    </tr>
                    """
                )

            sections_html.append(
                f"""
                <section id=\"{section_id}\" class=\"feature-section\">
                    <div class=\"nav\"><a href=\"{prev_link}\">Previous</a> | <a href=\"#overview\">Overview</a> | <a href=\"{next_link}\">Next</a></div>
                    <h2>{html.escape(stat['display_name'])}</h2>
                    <div class=\"meta\">
                        <div><strong>Total classified pixels:</strong> {stat['total_count']}</div>
                        <div><strong>Dominant class:</strong> {html.escape(dominant['label']) if dominant else '-'}</div>
                        <div><strong>Dominant share:</strong> {dominant['percent']:.2f}%</div>
                    </div>
                    <div class=\"bar-chart\">{feature_svg}</div>
                    <table>
                        <thead>
                            <tr>
                                <th>Value</th>
                                <th>Label</th>
                                <th>Pixel count</th>
                                <th>% ROI</th>
                            </tr>
                        </thead>
                        <tbody>{''.join(feature_table)}</tbody>
                    </table>
                </section>
                """
            )

        doc = f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
<meta charset=\"utf-8\">
<title>ROI Raster Histogram Report</title>
<style>
body {{font-family: Arial, Helvetica, sans-serif; margin: 24px; color: #222;}}
h1, h2 {{margin-bottom: 8px;}}
.meta {{margin-bottom: 20px; padding: 14px 16px; background: #f5f7fa; border: 1px solid #d9dee5; border-radius: 8px;}}
.meta div {{margin: 4px 0;}}
table {{border-collapse: collapse; width: 100%; margin-top: 12px;}}
th, td {{border: 1px solid #d9dee5; padding: 8px 10px; text-align: left;}}
th {{background: #f0f3f7;}}
.swatch {{display: inline-block; width: 14px; height: 14px; margin-right: 8px; vertical-align: middle; border: 1px solid #888;}}
.bar-chart {{margin-top: 16px; border: 1px solid #d9dee5; border-radius: 8px; padding: 16px; background: #fff;}}
.bar-row {{display: grid; grid-template-columns: 140px 1fr 120px; gap: 10px; align-items: center; margin: 8px 0;}}
.bar-label {{font-weight: 600;}}
.bar-wrap {{background: #eef2f7; height: 20px; border-radius: 4px; overflow: hidden;}}
.bar {{height: 100%;}}
.bar-value {{text-align: right; white-space: nowrap;}}
.small {{color: #666; font-size: 12px;}}
.feature-section {{margin-top: 28px; padding-top: 12px; border-top: 2px solid #e3e7ec;}}
.nav {{margin: 8px 0 14px 0;}}
.nav a {{text-decoration: none;}}
</style>
</head>
<body>
<a id=\"top\"></a>
<h1>ROI Raster Histogram</h1>
<div class=\"meta\">
    <div><strong>ROI layer:</strong> {html.escape(self.last_roi_name)}</div>
    <div><strong>Raster layer:</strong> {html.escape(self.last_raster_name)}</div>
    <div><strong>Band:</strong> {html.escape(self.last_band_label)}</div>
    <div><strong>Feature label field:</strong> {html.escape(self.last_identifier_field)}</div>
    <div><strong>Summary:</strong> {html.escape(self.last_summary_text)}</div>
    <div><strong>Exported:</strong> {html.escape(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}</div>
</div>

<h2>Combined result</h2>
<div class=\"bar-chart\">{self._build_svg_chart(self.last_rows, width=980, height=420)}</div>
<table>
    <thead>
        <tr>
            <th>Value</th>
            <th>Label</th>
            <th>Pixel count</th>
            <th>% ROI</th>
        </tr>
    </thead>
    <tbody>{''.join(rows_html)}</tbody>
</table>

<h2 id=\"overview\">Per-feature overview</h2>
<table>
    <thead>
        <tr>
            <th>Feature</th>
            <th>Total classified pixels</th>
            <th>Dominant class</th>
            <th>Dominant share</th>
        </tr>
    </thead>
    <tbody>{''.join(overview_rows)}</tbody>
</table>

{''.join(sections_html)}

<p class=\"small\">The histogram is calculated directly from ROI geometry, without influence from pixels outside the polygon.</p>
</body>
</html>
"""

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(doc)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save HTML:\n{e}")
            return

        QMessageBox.information(self, "Done", f"Report saved:\n{path}")

    def run_analysis(self):
        roi_layer = self._selected_roi_layer()
        raster_layer = self._selected_raster_layer()
        id_field = self._selected_id_field()

        self._clear_results()

        if roi_layer is None or raster_layer is None:
            QMessageBox.warning(self, "Missing data", "Select an ROI layer and a raster layer from the project.")
            return

        if roi_layer.geometryType() != Qgis.GeometryType.Polygon:
            QMessageBox.critical(self, "Error", "ROI must be a polygon layer.")
            return

        band = self.band_combo.currentData()
        if band is None:
            band = 1

        try:
            uid_result = processing.run(
                "native:fieldcalculator",
                {
                    "INPUT": roi_layer,
                    "FIELD_NAME": self.UID_FIELD,
                    "FIELD_TYPE": 1,
                    "FIELD_LENGTH": 20,
                    "FIELD_PRECISION": 0,
                    "FORMULA": "$id",
                    "OUTPUT": "TEMPORARY_OUTPUT",
                },
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error while preparing ROI features:\n{e}")
            return

        roi_uid_layer = self._coerce_vector_layer(uid_result.get("OUTPUT"), "ROI uid")
        if roi_uid_layer is None or not roi_uid_layer.isValid():
            QMessageBox.critical(self, "Error", "Failed to create temporary ROI UID layer.")
            return

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
            QMessageBox.critical(self, "Error", f"Error while dissolving ROI preview layer:\n{e}")
            return

        dissolved_roi = self._coerce_vector_layer(dissolved_result.get("OUTPUT"), "ROI dissolved")
        if self.add_clipped_checkbox.isChecked() and dissolved_roi is not None and dissolved_roi.isValid():
            self._add_preview_clip(dissolved_roi, raster_layer)

        try:
            zh_result = processing.run(
                "native:zonalhistogram",
                {
                    "INPUT_RASTER": raster_layer,
                    "RASTER_BAND": band,
                    "INPUT_VECTOR": roi_uid_layer,
                    "COLUMN_PREFIX": "H_",
                    "OUTPUT": "TEMPORARY_OUTPUT",
                },
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error while calculating histogram:\n{e}")
            return

        zh_layer = self._coerce_vector_layer(zh_result.get("OUTPUT"), "ROI histogram")
        if zh_layer is None or not zh_layer.isValid():
            QMessageBox.critical(self, "Error", "Failed to read histogram result layer.")
            return

        label_map, color_map = self._build_label_maps(raster_layer, band)
        feature_stats = self._prepare_feature_stats(zh_layer, id_field, label_map, color_map)

        if not feature_stats:
            self.summary_label.setText("ROI does not contain classified pixels or the result is empty.")
            return

        combined_rows, total_count = self._aggregate_rows_from_features(feature_stats)
        if total_count <= 0:
            self.summary_label.setText("ROI does not contain classified pixels or the result is empty.")
            return

        self._populate_table(combined_rows, self.table)
        self.chart.set_rows(combined_rows)

        self.last_rows = combined_rows
        self.last_total_count = total_count
        self.last_feature_stats = feature_stats
        self.last_roi_name = roi_layer.name()
        self.last_raster_name = raster_layer.name()
        self.last_band_label = self.band_combo.currentText()
        self.last_identifier_field = "[Feature ID]" if id_field == self.FEATURE_ID_SENTINEL else id_field
        self.last_summary_text = (
            f"Features analyzed: {len(feature_stats)} | Pixels in ROI: {total_count} | "
            f"Classes in ROI: {len(combined_rows)} | Histogram calculated directly from ROI geometry"
        )
        self.summary_label.setText(self.last_summary_text)
        self._set_feature_combo_from_stats()

        if self.write_attributes_checkbox.isChecked():
            ok, msg = self._write_stats_to_roi_layer(roi_layer, feature_stats)
            if ok:
                QMessageBox.information(self, "Attribute table updated", msg)
            else:
                QMessageBox.warning(self, "Attribute update failed", msg)


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
