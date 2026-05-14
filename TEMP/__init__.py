# -*- coding: utf-8 -*-

def classFactory(iface):
    from .roi_raster_histogram import RoiRasterHistogramPlugin
    return RoiRasterHistogramPlugin(iface)