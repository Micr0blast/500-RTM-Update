

import sys
import matplotlib
matplotlib.use("Qt5Agg")

from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT

from PySide2 import QtCore as qtc
from PySide2 import QtGui as qtg
from PySide2 import QtWidgets as qtw

from .resources import *
from .canvas import Canvas
import numpy as np


LINE_GRAPH_TITLE = "Linienprofil"
LINE_GRAPH_Y_LABEL = "Höhe"

SCAN_GRAPH_TITLE = "Scan"
SCAN_GRAPH_X_LABEL = "x"
SCAN_GRAPH_Y_LABEL = "y"
CUSTOM_TOOL_LABEL = "Destruktive Werkzeuge"

GRAPH_FONTS = "Sans Serif"

MODE_LINE_PROFILE = 1
MODE_PLANE_PROFILE = 2


LINE_PROFILE_TOOLTIP = "Linienprofil ermitteln"
LINE_PROFILE_STARTED_LOG = "Linienprofil-Werkzeug gestartet - 2 Punkte im Scan auswählen..."
LINE_PROFILE_EXECUTED_LOG = "Linienprofil erfolgreich erzeugt"
PLANE_LEVEL_TOOLTIP = "Ebene begradigen"
PLANE_LEVEL_STARTED_LOG= "Ebene-begradigen-Werkzeug gestartet - 3 Punkte im Scan auswählen..."
PLANE_LEVEL_EXECUTED_LOG = "Ebene erfolgreich begradigt"
DATA_RESET_TOOLTIP = "Bilddaten zurücksetzen"
DATA_RESET_LOG = "Scan wurde zurückgesetzt"

class CustomToolbar(NavigationToolbar2QT):
    """Custom Toolbar to remove tools included in base NavigationTOolbar

    """
    toolitems = [t for t in NavigationToolbar2QT.toolitems if
                 t[0] in ('Home', 'Pan', 'Zoom','Forward', "Back", 'Save')]
    
    def init(self,figure_canvas, parent= None):
        super.__init__(self, figure_canvas, parent= None)

    



class CentralPlotWidget(qtw.QWidget):
    coordinates = []
    points = []
    cid = None
    mode = 0
    image = []
    changedImage = []

    
    logMessage = qtc.Signal(str)

    def __init__(self):
        super().__init__()
        # Main UI code goes here

        self.initPlotUI()
        # End main UI code
        # self.show()

    def initPlotUI(self):

        
        self.image = np.zeros((500, 500))

        self.mainLayout = qtw.QVBoxLayout()

        self.setLayout(self.mainLayout)

        self.scanCanvas = Canvas(parent=self, width=6,
                                 height=6, dpi=100)
        self.axes = self.scanCanvas.fig.subplots(
            2, 1, gridspec_kw={'height_ratios': [3, 15]})
        self.scanCanvas.fig.tight_layout(pad=5.0, w_pad=0)

        self.lineProfileAxe = self.axes[0]

        # self.lineProfileAxe.set_xlabel("")
        self.lineProfileAxe.set_ylabel(LINE_GRAPH_Y_LABEL)
        self.lineProfileAxe.set_title(
            LINE_GRAPH_TITLE, fontweight="bold", fontname=GRAPH_FONTS, fontsize=14, loc="left")

        self.scanAxe = self.axes[1]

        self.scanAxe.set_xlabel(SCAN_GRAPH_X_LABEL)
        self.scanAxe.set_ylabel(SCAN_GRAPH_Y_LABEL)
        self.scanAxe.set_title(SCAN_GRAPH_TITLE, fontweight="bold", fontname=GRAPH_FONTS, fontsize=14, loc="left")

        self.updateImage(self.image)

        self.mainLayout.addWidget(self.scanCanvas)


        ####### Toolbar setup
        self.scanCanvas.toolbar = CustomToolbar(self.scanCanvas.canvas, self)
        
        self.scanCanvas.toolbar.addWidget(qtw.QLabel(CUSTOM_TOOL_LABEL))

        
        self.lineProfileAction =  qtw.QAction(
            qtg.QIcon(":/icons/line_profile_btn.png"),
            LINE_PROFILE_TOOLTIP,
            self,
            triggered=self.startLineProfile)
        self.planeLevelAction = qtw.QAction(
            qtg.QIcon(":/icons/plane_level_btn.png"),
            PLANE_LEVEL_TOOLTIP,
            self,
            triggered = self.startPlaneLevel
        )

        self.resetImageAction = qtw.QAction(
            qtg.QIcon(":/icons/reset_btn"),
            DATA_RESET_TOOLTIP,
            self,
            triggered = self.resetImage
        )
        self.scanCanvas.toolbar.addAction(self.lineProfileAction)
        self.scanCanvas.toolbar.addAction(self.planeLevelAction)
        self.scanCanvas.toolbar.addAction(self.resetImageAction)

        self.scanCanvas.layout.addWidget(self.scanCanvas.toolbar)

    
    def updateImage(self, imageData):
        """Handles updates to the Scan Graph and saves Image Data for reset

        Args:
            imageData: Scan Data
        """
        self.image = None
        self.image = np.array(imageData)
        
        self.scanAxe.clear()
        self.scanAxe.imshow(self.image, cmap="gray", origin='lower')
        
        self.scanAxe.set_xlabel(SCAN_GRAPH_X_LABEL)
        self.scanAxe.set_ylabel(SCAN_GRAPH_Y_LABEL)
        self.scanAxe.set_title(SCAN_GRAPH_TITLE, fontweight="bold", fontname=GRAPH_FONTS, fontsize=14, loc="left")
        self.scanCanvas.canvas.draw()

    def removeToolPointsFromImage(self):
        """Removes points made by tools on the graph
        """
        if self.points:
            [point.pop(0).remove() for point in self.points]
            print(len(self.points))
            self.points = []

    def resetImage(self):
        """Resets the Scan data back to the image received by the STM
        """
        self.removeToolPointsFromImage()
        self.scanAxe.imshow(self.image, cmap="gray", origin='lower')
        self.logMessage.emit(DATA_RESET_LOG)
        self.scanCanvas.canvas.draw()

    def startLineProfile(self):
        """Initiates the line Profile tool
        """
        qtw.QApplication.setOverrideCursor(qtg.QCursor(qtc.Qt.CrossCursor))
        if self.cid != None:
            self.scanCanvas.canvas.mpl_disconnect(self.cid)
        self.removeToolPointsFromImage()
        self.logMessage.emit(LINE_PROFILE_STARTED_LOG)
        self.cid = self.scanCanvas.canvas.mpl_connect("button_press_event", self.onclick)
        self.mode = MODE_LINE_PROFILE
    
    def startPlaneLevel(self):
        """Initiates the Plane Level Tool
        """
        qtw.QApplication.setOverrideCursor(qtg.QCursor(qtc.Qt.CrossCursor))

        if self.cid != None:
            self.scanCanvas.canvas.mpl_disconnect(self.cid)
        self.removeToolPointsFromImage()

        self.logMessage.emit(PLANE_LEVEL_STARTED_LOG)

        self.cid = self.scanCanvas.canvas.mpl_connect("button_press_event", self.onclick)
        self.mode = MODE_PLANE_PROFILE



    def onclick(self, event):
        """Handles on click actions of the tools

        """
        # if clicked outside of canvas exit tool
        if event.xdata == None or event.ydata == None:
            self.removeToolPointsFromImage()
            self.reset()
            self.scanCanvas.canvas.mpl_disconnect(self.cid)
        elif event.button == 1:
            self.coordinates.append((event.xdata, event.ydata))
            self.points.append(self.scanAxe.plot(event.xdata, event.ydata, 'gx',lw=12, label='point'))
            self.scanCanvas.canvas.draw()
            self.logMessage.emit(f'Punkt ({event.xdata:.1f}, {event.ydata:.1f}) gewählt')
            self.checkIfAllCoordsCollected()
    
    def checkIfAllCoordsCollected(self):
        if self.mode == MODE_LINE_PROFILE:
            if len(self.coordinates) == 2:
                self.scanCanvas.fig.canvas.mpl_disconnect(self.cid)
                self.calculateLineProfile()
        elif self.mode == MODE_PLANE_PROFILE:
            if len(self.coordinates) == 3:
                self.scanCanvas.fig.canvas.mpl_disconnect(self.cid)
                self.levelImageByPlane()

    def calculateLineProfile(self):
        """ Executes the Line profile action
        """
        x0, y0 = self.coordinates[0][0], self.coordinates[0][1]
        x1, y1 = self.coordinates[1][0], self.coordinates[1][1]
        length = int(np.hypot(x1-x0, y1-y0))

        xLine, yLine = np.linspace(x0, x1, length), np.linspace(y0, y1, length)
        lineValues = self.image[xLine.astype(np.int), yLine.astype(np.int)]
     
        self.lineProfileAxe.cla()
        
        self.lineProfileAxe.set_ylabel(LINE_GRAPH_Y_LABEL)
        self.lineProfileAxe.set_title(
            LINE_GRAPH_TITLE, fontweight="bold", fontname=GRAPH_FONTS, fontsize=14, loc="left")
        self.lineProfileAxe.plot(lineValues)
        self.scanCanvas.canvas.draw()
        self.reset()
        self.logMessage.emit(LINE_PROFILE_EXECUTED_LOG)
        return

    def levelImageByPlane(self):
        """ Executes the plane level action"""
        x0, y0 = self.coordinates[0][0], self.coordinates[0][1]
        x1, y1 = self.coordinates[1][0], self.coordinates[1][1]
        x2, y2 = self.coordinates[2][0], self.coordinates[2][1]

        p1 = np.array([x0, y0, self.image[int(x0), int(y0)]])
        p2 = np.array([x1, y1, self.image[int(x1), int(y1)]])
        p3 = np.array([x2, y2, self.image[int(x2), int(y2)]])

        v1 = p3 - p1
        v2 = p2 - p1
        crossProd = np.cross(v1, v2)
        a, b, c = crossProd

        a, b, c = np.cross(v1, v2)
        a, b, c = np.cross(p3 - p1, p2 - p1)
        # a, b, c = np.cross(np.array([x2, y2, self.image[int(x2), int(y2)]]) - np.array([x0, y0, self.image[int(x0), int(y0)]]), np.array([x1, y1, self.image[int(x1), int(y1)]]) - np.array([x0, y0, self.image[int(x0), int(y0)]]))
        # a, b, c = np.cross(np.array([x2, y2, self.image[int(x2), int(y2)]]) - np.array([x0, y0, self.image[int(x0), int(y0)]]), np.array([x1, y1, self.image[int(x1), int(y1)]]) - np.array([x0, y0, self.image[int(x0), int(y0)]]))

        d = np.dot(crossProd, p3)
        x = np.arange(0, stop=len(self.image), step=1) 
        y = np.arange(0, stop=len(self.image[0]), step=1)

        plane = (d - a*x - b*y) / c

        # plane = ( np.dot(crossProd, p3) - a*np.arange(0, stop=len(self.image), step=1) - b*np.arange(0, stop=len(self.image[0]), step=1) )/ c

        # leveledImage = np.subtract(self.image, plane)
        if self.changedImage != []:
            self.scanAxe.imshow(np.subtract(self.changedImage, plane), cmap="gray", origin='lower')
        else: 
            self.changedImage = np.subtract(self.image, plane)

            self.scanAxe.imshow(self.changedImage, cmap="gray", origin='lower')

        self.scanCanvas.canvas.draw()
        
        self.logMessage.emit(PLANE_LEVEL_EXECUTED_LOG)
        self.reset()
        

    def reset(self):
        self.mode = 0
        self.coordinates = []
        qtw.QApplication.restoreOverrideCursor()
        


    

if __name__ == '__main__':
    app = qtw.QApplication(sys.argv)
    # it's required to save a reference to MainWindow.
    # if it goes out of scope, it will be destroyed.
    mw = CentralPlotWidget()
    sys.exit(app.exec_())
