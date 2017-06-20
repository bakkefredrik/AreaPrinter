# -*- coding: utf-8 -*-
"""
/***************************************************************************
 AreaPrinter
                                 A QGIS plugin
 AreaPrinter
                             -------------------
        begin                : 2017-06-18
        copyright            : (C) 2017 by Fredrik Bakke
        email                : bakkefredrik@gmail.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load AreaPrinter class from file AreaPrinter.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .AreaPrinter import AreaPrinter
    return AreaPrinter(iface)
