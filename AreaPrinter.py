# -*- coding: utf-8 -*-
"""
/***************************************************************************
 AreaPrinter
                                 A QGIS plugin
 AreaPrinter
                              -------------------
        begin                : 2017-06-18
        git sha              : $Format:%H$
        copyright            : (C) 2017 by Fredrik Bakke
        email                : bakkefredrik@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtGui import QAction, QIcon, QMessageBox, QColor

from pyproj import Proj, transform

from qgis.core import *
from qgis.gui import *
import math
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from AreaPrinter_dialog import AreaPrinterDialog
from AreaPrinter_toolDialog import AreaPrinterToolDialog
import os.path
gridConvergence = 0.0
scale = 0.0
A4PortraitHeight = 0.0
A4PortraitWidth = 0.0
topMargin = 0.0
bottomMargin = 0.0
sideMargin = 0.0

extentHeight = 0.0
extentWidth = 0.0


class AreaPrinter:
    """QGIS Plugin Implementation."""
    initialized = 0
    initializedTools = 0
    doRotate = 0 #rotate to true north	
    extents = list()
    overlap = 0.1 #value*100 = %overlap
    layer = QgsVectorLayer
    pr = QgsVectorDataProvider
    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'AreaPrinter_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)


        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&AreaPrinter')

        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'AreaPrinter')
        self.toolbar.setObjectName(u'AreaPrinter')

	self.toolbar2 = self.iface.addToolBar(u'AreaPrinterTools')
        self.toolbar2.setObjectName(u'AreaPrinterTools')

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('AreaPrinter', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        # Create the dialog (after translation) and keep reference
        self.dlg = AreaPrinterDialog()
	self.tools = AreaPrinterToolDialog()

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/AreaPrinter/mountainIcon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'AreaPrinter'),
            callback=self.run,
            parent=self.iface.mainWindow())

	self.add_action(
            icon_path,
            text=self.tr(u'Grid Convergence'),
            callback=self.runTools,
            parent=self.iface.mainWindow())



    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&AreaPrinter'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar


    def run(self):

	#check if projection is supported
	CRS = self.iface.mapCanvas().mapRenderer().destinationCrs().authid()  #the canvas' current CRS 
	if getUtmZoneNumberFromProjection(CRS) == 0:	#did not get zone
		self.userWarning("Projection is not supported. Please set the project CRS to WGS84 / UTM#.",'')
		self.dlg.close()
	else:
		self.setup()
        	"""Run method that performs all the real wrk"""
        	# show the dialog
        	self.dlg.show()
        	# Run the dialog event loop
        	result = self.dlg.exec_()
        	# See if OK was pressed
        	if result:
        	    # Do something useful here - delete the line containing pass and
        	    # substitute with your code.
        	    pass

    def setup(self):
	
	if(self.initialized == 0):
		
		self.dlg.adjustBtnN.clicked.connect(self.moveNBtnClicked)
		self.dlg.adjustBtnS.clicked.connect(self.moveSBtnClicked)
		self.dlg.adjustBtnE.clicked.connect(self.moveEBtnClicked)
		self.dlg.adjustBtnW.clicked.connect(self.moveWBtnClicked)
	
		self.dlg.addBtnN.clicked.connect(self.addNBtnClicked)
		self.dlg.addBtnS.clicked.connect(self.addSBtnClicked)
		self.dlg.addBtnE.clicked.connect(self.addEBtnClicked)
		self.dlg.addBtnW.clicked.connect(self.addWBtnClicked)

		self.dlg.exitBtn.clicked.connect(self.exitBtnClicked)
		self.dlg.removeLastBtn.clicked.connect(self.removeLastPage)
		self.dlg.saveBtn.clicked.connect(self.generateComposer)
		self.dlg.resetBtn.clicked.connect(self.reset)

		self.initialized = 1	
	
		self.calculateValues()
		self.createInitialPage()
	
		
	if len(self.iface.activeComposers()) > 0:
		self.userWarning("A composer already exist. please remove it before continuing",'Using this plugin can have unintended consequences for existing print composers, as it is not able to distinguish between them')


	if self.dlg.rotCb.isChecked():
		self.doRotate = 1
	else:
		self.doRotate = 0
		
	self.updateGridConvergence()			
	self.layer =  QgsVectorLayer('Polygon', 'AreaPrinter' , "memory")
	self.pr = self.layer.dataProvider() 		
			
			
	for ex in self.extents:
		self.printExtents(ex)
	
	QgsMapLayerRegistry.instance().addMapLayers([self.layer])
	
	#opacity
	layerRenderer = self.layer.rendererV2()
	sym = QgsFillSymbolV2.createSimple({'color':'0,32,32,32', 
                                      'color_border':'#000000',
                                      'width_border':'0.2'})
	layerRenderer.setSymbol(sym)
	

    def printExtents(self, rect):
	
	
	centre = rect.center()
	
	rotation = 0	
	if self.doRotate == 1:
		rotation = -self.gridConvergence
	
	p1 = rotatePoint(centre, QgsPoint(rect.xMinimum(), rect.yMinimum()),rotation)
	p2 = rotatePoint(centre, QgsPoint(rect.xMinimum(), rect.yMaximum()),rotation)
	p3 = rotatePoint(centre, QgsPoint(rect.xMaximum(), rect.yMinimum()),rotation)
	p4 = rotatePoint(centre, QgsPoint(rect.xMaximum(), rect.yMaximum()),rotation)

	poly = QgsFeature()

	points = [p1,p2,p4,p3]
	#points = [QgsPoint(rotatedRect.xMinimum(), rotatedRect.yMinimum()), QgsPoint(rotatedRect.xMinimum(), rotatedRect.yMaximum()), QgsPoint(rotatedRect.xMaximum(), rotatedRect.yMaximum()),QgsPoint(rotatedRect.xMaximum(), rotatedRect.yMinimum())]
	poly.setGeometry(QgsGeometry.fromPolygon([points]))
	self.pr.addFeatures([poly])
	self.layer.updateExtents()
	


    
    def moveNBtnClicked(self):
	if self.dlg.moveAllCb.isChecked():
		self.moveMap("North", True)
	else:
		self.moveMap("North", False)

    def moveSBtnClicked(self):
	if self.dlg.moveAllCb.isChecked():
		self.moveMap("South", True)
	else:
		self.moveMap("South", False)

    def moveEBtnClicked(self):
	if self.dlg.moveAllCb.isChecked():
		self.moveMap("East", True)
	else:
		self.moveMap("East", False)

    def moveWBtnClicked(self):
	if self.dlg.moveAllCb.isChecked():
		self.moveMap("West", True)
	else:
		self.moveMap("West", False)

    def moveMap(self, direction, moveAll):
	self.emptyLayer()
	offsetStep = 1000.0
	offsetX =0.0;
	offsetY =0.0;
	if direction == "North":
		offsetY = offsetStep
	elif direction == "South":
		offsetY = 0.0-offsetStep
	elif direction == "East":
		offsetX = offsetStep
	elif direction == "West":
		offsetX = 0.0-offsetStep

	if moveAll == True :
		for ex in self.extents:
			ex.setYMaximum(ex.yMaximum() + offsetY)
			ex.setYMinimum(ex.yMinimum() + offsetY)
			ex.setXMaximum(ex.xMaximum() + offsetX)
			ex.setXMinimum(ex.xMinimum() + offsetX)
	else: #move only last extent
		ex = self.extents[len(self.extents)-1] #dont use on empty list
		ex.setYMaximum(ex.yMaximum() + offsetY)
		ex.setYMinimum(ex.yMinimum() + offsetY)
		ex.setXMaximum(ex.xMaximum() + offsetX)
		ex.setXMinimum(ex.xMinimum() + offsetX)
	
	for ex in self.extents:
		self.printExtents(ex)
	


    def addNBtnClicked(self):
	self.addExtent("North")
    def addSBtnClicked(self):
	self.addExtent("South")
    def addEBtnClicked(self):
	self.addExtent("East")
    def addWBtnClicked(self):
	self.addExtent("West")

    def addExtent(self, direction):
	self.emptyLayer()
	lastExtent = self.extents[len(self.extents)-1] #dont use on empty list

	offsetX = lastExtent.width() * (1.0-self.overlap);	
	offsetY = lastExtent.height() * (1.0-self.overlap);

	doOffsetX = 0.0
	doOffsetY = 0.0
	if direction == "North":
		doOffsetY = offsetY
	elif direction == "South":
		doOffsetY = 0.0-offsetY
	elif direction == "East":
		doOffsetX = offsetX
	elif direction == "West":
		doOffsetX = 0.0-offsetX

	newExtent = QgsRectangle(lastExtent)	


	newExtent.setXMaximum(lastExtent.xMaximum() + doOffsetX)	
	newExtent.setXMinimum(lastExtent.xMinimum() + doOffsetX)
	newExtent.setYMaximum(lastExtent.yMaximum() + doOffsetY)	
	newExtent.setYMinimum(lastExtent.yMinimum() + doOffsetY)
	
	#now move extent in accordance with angle
	tmpCenter = newExtent.center()
	origin = lastExtent.center()
	
	rotation = 0	
	if self.doRotate == 1:
		rotation = -self.gridConvergence
	centreInRotatedSpace = rotatePoint(origin, tmpCenter, rotation)
	
	extentInRotatedSpace = QgsRectangle(newExtent)
	extentInRotatedSpace.setXMinimum(centreInRotatedSpace.x() - newExtent.width() / 2.0)	
	extentInRotatedSpace.setXMaximum(centreInRotatedSpace.x() + newExtent.width() / 2.0)
	extentInRotatedSpace.setYMinimum(centreInRotatedSpace.y() - newExtent.height() / 2.0)	
	extentInRotatedSpace.setYMaximum(centreInRotatedSpace.y() + newExtent.height() / 2.0)
	
	self.extents.append(extentInRotatedSpace)
	for ex in self.extents:
		self.printExtents(ex)
	

    def exitBtnClicked(self):
	#first remove layer
	QgsMapLayerRegistry.instance().removeMapLayer(self.layer.id())

	self.dlg.close()


    def removeLastPage(self):
	if len(self.extents) > 1:	
		self.extents.pop()
		self.emptyLayer()

		for ex in self.extents:
			self.printExtents(ex)	

    def emptyLayer(self):
	with edit(self.layer):
		    listOfIds = [feat.id() for feat in self.layer.getFeatures()]
		    self.layer.deleteFeatures( listOfIds )


    def generateComposer(self):

	#first remove layer
	QgsMapLayerRegistry.instance().removeMapLayer(self.layer.id())
	#then create and set up composer
	self.iface.createNewComposer("AreaPrinter")
	composerViewIndex = len(self.iface.activeComposers()) -1
	comp = self.iface.activeComposers()[0].composition()      # new compositions dont have consistent index
	comp.setNumPages(len(self.extents))

	spaceBetweenPages = comp.spaceBetweenPages()
	comp.setPaperSize(A4PortraitWidth,A4PortraitHeight) 
	
	CRS = self.iface.mapCanvas().mapRenderer().destinationCrs().authid()  #the canvas' current CRS 
	mapName = self.dlg.mapNameEdit.text()
	
	for i in range(0, len(self.extents)):
		newMap = QgsComposerMap(comp, sideMargin, i* (A4PortraitHeight + spaceBetweenPages) + topMargin, A4PortraitWidth- 2*sideMargin, A4PortraitHeight - topMargin - bottomMargin )
    		
		newMap.setNewExtent(self.extents[i])
		
		gc = 0
		if self.doRotate == 1:
			gc = self.gridConvergence
			if gc < 0:	#composer dont handle negative
				gc = 360+gc
		
		newMap.setMapRotation(gc)
		newMap.setFrameEnabled(True)


		self.createUtmGrid(newMap)
		
		comp.addComposerMap(newMap)
	self.createScaleBars()	
	self.createScales()		
	self.createInfoLabels(CRS, mapName)
	
    def userWarning(self, text, details):
	msg = QMessageBox()
	msg.setIcon(QMessageBox.Warning)
	msg.setText(text)
	msg.setWindowTitle("Warning")
	msg.setDetailedText(details)
	msg.exec_() 

    def createUtmGrid(self, mapItem):
	grid = QgsComposerMapGrid('kilometerGrid', mapItem)
	grid.setIntervalX(1000.0)	#km
	grid.setIntervalY(1000.0)	#km
	
	if scale == 10000:
		grid.setIntervalX(250.0)	#km
		grid.setIntervalY(250.0)
	else:
		grid.setIntervalX(1000.0)	#km
		grid.setIntervalY(1000.0)

	grid.setGridLineWidth(0.1)
	grid.setAnnotationEnabled(True) 
	grid.setAnnotationDirection(2,1) # right side vertical
	grid.setAnnotationDirection(0,3) # top side horizontal
	grid.setAnnotationDisplay(3,0) # none at left
	grid.setAnnotationDisplay(3,2) # none at bottom
	grid.setAnnotationPrecision(0) # no decimals
	grid.setGridLineColor(QColor("#407AA0"))

	mapItem.grids().addGrid(grid)

	
    def createScaleBars(self): #mapnumber from zero
	comp = self.iface.activeComposers()[0].composition()
	for i in range(0, len(comp.composerMapItems())):


		scaleBar = QgsComposerScaleBar(comp)
		scaleBar.setComposerMap(comp.composerMapItems()[i])			
			
		scaleBar.setNumMapUnitsPerScaleBarUnit(1000.0)				
#		scaleBar.setUnits(2) #km
		scaleBar.setUnitLabeling("km")
		scaleBar.setNumSegmentsLeft(0)
		
		if scale == 50000:		# special case, scalebar cannot fit four labels
			scaleBar.setNumSegments(2)
			scaleBar.setNumUnitsPerSegment(500.0)
		else:
			scaleBar.setNumSegments(4)
			scaleBar.setNumUnitsPerSegment(250.0)

		comp.addComposerScaleBar(scaleBar)		
		scaleBar.setItemPosition(sideMargin,A4PortraitHeight,6,i+1)  #x,y,lowerleft,page
					
    def createScales(self): #mapnumber from zero
	comp = self.iface.activeComposers()[0].composition()
	for i in range(0, len(comp.composerMapItems())):
		scale = QgsComposerScaleBar(comp)
		scale.setComposerMap(comp.composerMapItems()[i])			
			
		scale.setStyle("Numeric")
		comp.addComposerScaleBar(scale)		
		scale.setItemPosition(160,A4PortraitHeight,6,i+1)  #x,y,lowerleft,page

    def createInfoLabels(self,CRS,mapName):
	tmpString="QGIS/AreaPrinter"	
	

	if self.doRotate == 1:
		upString = "Up=True North. "
	elif self.doRotate == 0:
		upString = "UP=Grid North. "
	else:
		upString = " "

	infoLabelText = mapName + ". " + "UTM zone: "+ "%0.1f" % getUtmZoneNumberFromProjection(CRS) + ". " + upString + "Grid Convergence="+str(self.gridConvergence)+". " + tmpString
	
	comp = self.iface.activeComposers()[0].composition()
	pages = len(comp.composerMapItems())
	for i in range(0, len(comp.composerMapItems())):
		#add info label		
		label = QgsComposerLabel(comp)
		label.setText(infoLabelText)
		label.adjustSizeToText()
		comp.addComposerLabel(label)		
		label.setItemRotation(270)	#before positioning		
		label.setItemPosition(0,A4PortraitHeight-bottomMargin,0,i+1) #x,y,upperleft,page
		

		#add page number
		pageIndex = i+1
		pageLabel = QgsComposerLabel(comp)
		pageLabel.setText("Page " + str(pageIndex) + "/" + str(pages) )
		pageLabel.adjustSizeToText()
		comp.addComposerLabel(pageLabel)		
		pageLabel.setItemPosition(A4PortraitWidth - sideMargin,0,2,i+1) #x,y,upperright,page


    def reset(self):
	del self.extents[:] #delete extents
	
	if self.dlg.rotCb.isChecked():
		self.doRotate = 1
	else:
		self.doRotate = 0
	self.emptyLayer()	
	self.calculateValues()
	self.updateGridConvergence()
	self.createInitialPage()
	self.printExtents(self.extents[0])
	

    def createInitialPage(self):
	extent_1 = QgsRectangle(self.iface.mapCanvas().extent())
	# "center" the first page in canvas	
	xMin = extent_1.xMinimum() + (extent_1.xMaximum() - extent_1.xMinimum()) /2.0
	xMax = xMin + extentWidth
	yMin = extent_1.yMinimum() + (extent_1.yMaximum() - extent_1.yMinimum()) /2.0
	yMax = yMin + extentHeight
	extent_1.setXMinimum(xMin)
	extent_1.setYMinimum(yMin)
	extent_1.setXMaximum(xMax)
	extent_1.setYMaximum(yMax)
	
	self.extents.append(extent_1)
	


    def calculateValues(self):

	
	global scale
	global A4PortraitHeight
	global A4PortraitWidth
	global topMargin
	global bottomMargin
	global sideMargin
	global extentHeight
	global extentWidth


	if self.dlg.rb10.isChecked():
		scale = 10000
	elif self.dlg.rb25.isChecked():
		scale = 25000
	elif self.dlg.rb50.isChecked():
		scale = 50000
	else:
		scale = 25000	#default 1:25000

	A4PortraitHeight = 297.0
	A4PortraitWidth = 210.0
	topMargin = 10.0
	bottomMargin = 10.0
	sideMargin = 10.0
	
	extentHeight = scale * (A4PortraitHeight - topMargin - bottomMargin) / 1000.0 #mm to m
	extentWidth = scale * (A4PortraitWidth - 2.0*sideMargin)  / 1000.0 #mm to m

    def updateGridConvergence(self):
	authId = self.iface.mapCanvas().mapRenderer().destinationCrs().authid()
	utmZone = getUtmZoneNumberFromProjection(authId)
	trueNorthMeridianLongitude = getTrueNorthMeridianLongitudeOfUtmZone(utmZone)
	canvasCenter = self.iface.mapCanvas().extent().center()
	centerGeoGraphic = getGeoGraphicCoordinate(authId, canvasCenter.x(), canvasCenter.y())
	gc = self.findGridConvergence(centerGeoGraphic.x(), centerGeoGraphic.y(), trueNorthMeridianLongitude)
	
	self.dlg.rotateEdit.setText("%0.1f" % gc)

	
	self.gridConvergence = gc   #store grid convergence



    def runTools(self):

	if(self.initializedTools == 0):		
		self.tools.calcBtn.clicked.connect(self.toolsCalcBtnClicked)
		self.initializedTools = 1
	self.tools.show()
        # Run the dialog event loop
        result = self.tools.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass

    #returns the grid convergence (angle clockwise from a true north meridian

    def toolsCalcBtnClicked(self):
	pointLong = float(self.tools.longEdit.text())
	pointLat = float(self.tools.latEdit.text())
	trueLong = float(self.tools.tLongEdit.text())
	result = str(self.findGridConvergence(pointLong, pointLat, trueLong))
	self.tools.resultLabel.setText(result)

    def findGridConvergence(self, pointLongitude, pointLatitude, trueNorthMeridianLongitude):

	A = math.tan(math.radians(pointLongitude-trueNorthMeridianLongitude))
	B = math.sin(math.radians(pointLatitude))
	C = A * B
	D = math.degrees(math.atan(C))
	return D





def rotatePoint(origin, point, angle):
    #rotate point clockwise around origin, angle in degrees
    
    cosAngle = math.cos(math.radians(-angle))
    sinAngle = math.sin(math.radians(-angle))

    returnX = origin.x() + cosAngle * (point.x() - origin.x()) - sinAngle * (point.y() - origin.y())
    returnY = origin.y() + sinAngle * (point.x() - origin.x()) + cosAngle * (point.y() - origin.y())
    return QgsPoint(returnX,returnY)


def rotateRectangleAroundCentre(rect, angle):
    #rotate rectangle angle degrees clockwise
    ret = QgsRectangle(0,0,0,0)
    centre = rect.center()

    xMin = rect.xMinimum()
    xMax = rect.xMaximum()
    yMin = rect.yMinimum()
    yMax = rect.yMaximum()

    p1 = rotatePoint(centre, QgsPoint(xMin,yMin),angle)
    p2 = rotatePoint(centre, QgsPoint(xMax,yMax),angle)

    return QgsRectangle(p1,p2)



	#returns or an utm zone numberor 0
def getUtmZoneNumberFromProjection(authId):
	numberString = authId.split(':')[1]
	num = int(numberString)
	if(num >= 32601 and num <= 32660):
		return num - 32600
	elif(num >= 32701 and num <= 32760):
		return num - 32700
	else:
		return 0

	
def getTrueNorthMeridianLongitudeOfUtmZone(zone): 
	if zone >= 31 and zone <= 60 :
		return (zone -31 ) * 6.0 + 3.0
	elif zone > 0 and zone <= 30 :
		return -((30 - zone) * 6.0 + 3.0)	#west is negative


def getGeoGraphicCoordinate(inProjectionString, inX, inY):

	inProj = Proj(init=inProjectionString)
	outProj = Proj(init='EPSG:4326')	
	x2,y2 = transform(inProj,outProj,inX,inY)	
	
	return  QgsPoint(x2,y2)




