# -*- coding: utf-8 -*-
"""QGIS plugin entry point for ROI Raster Histogram."""


def classFactory(iface):
    """Load the plugin class for QGIS."""
    from .roi_raster_histogram import RoiRasterHistogramPlugin

    return RoiRasterHistogramPlugin(iface)
