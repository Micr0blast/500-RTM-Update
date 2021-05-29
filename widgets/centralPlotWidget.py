

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

class CustomToolbar(NavigationToolbar2QT):
    toolitems = [t for t in NavigationToolbar2QT.toolitems if
                 t[0] in ('Home', 'Pan', 'Zoom','Forward', "Back", 'Save')]
    
    def init(self,figure_canvas, parent= None):
        super.__init__(self, figure_canvas, parent= None)

        ## overwrite save here
    



class CentralPlotWidget(qtw.QWidget):
    coordinates = []
    points = []
    cid = None
    mode = 0
    image = []
    changedImage = []

    
    logMessage = qtc.Signal(str)

    def __init__(self):
        """MainWindow constructor.

        This widget will be our main window.
        We'll define all the UI components in here.
        """
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
        self.lineProfileAxe.set_ylabel("Höhe")
        self.lineProfileAxe.set_title(
            "Linienprofil", fontweight="bold", fontname="Sans Serif", fontsize=14, loc="left")

        self.scanAxe = self.axes[1]

        self.scanAxe.set_xlabel("x")
        self.scanAxe.set_ylabel("y")
        self.scanAxe.set_title("Scan", fontweight="bold", fontname="Sans Serif", fontsize=14, loc="left")



        # self.lineProfileAxe.plot(np.linspace(1, 1000, 500))
        self.updateImage(self.image)

        self.mainLayout.addWidget(self.scanCanvas)
        # layout.addStretch()


        ####### Toolbar setup
        self.scanCanvas.toolbar = CustomToolbar(self.scanCanvas.canvas, self)
        
        self.scanCanvas.toolbar.addWidget(qtw.QLabel("Destruktive Werkzeuge"))

        
        self.lineProfileAction =  qtw.QAction(
            qtg.QIcon(":/icons/line_profile_btn.png"),
            "Linienprofil ermitteln",
            self,
            triggered=self.startLineProfile)
        self.planeLevelAction = qtw.QAction(
            qtg.QIcon(":/icons/plane_level_btn.png"),
            "Ebene begradigen",
            self,
            triggered = self.startPlaneLevel
        )

        self.resetImageAction = qtw.QAction(
            qtg.QIcon(":/icons/reset_btn"),
            "Bilddaten zurücksetzen",
            self,
            triggered = self.resetImage
        )
        self.scanCanvas.toolbar.addAction(self.lineProfileAction)
        self.scanCanvas.toolbar.addAction(self.planeLevelAction)
        self.scanCanvas.toolbar.addAction(self.resetImageAction)

        self.scanCanvas.layout.addWidget(self.scanCanvas.toolbar)

    
    def updateImage(self, imageData):
        self.image = None
        self.image = np.array(imageData)
        
        self.scanAxe.clear()
        self.scanAxe.imshow(self.image, cmap="gray", origin='lower')
        
        self.scanAxe.set_xlabel("x")
        self.scanAxe.set_ylabel("y")
        self.scanAxe.set_title("Scan", fontweight="bold", fontname="Sans Serif", fontsize=14, loc="left")
        self.scanCanvas.canvas.draw()

    def removeToolPointsFromImage(self):
        if self.points:
            [point.pop(0).remove() for point in self.points]
            print(len(self.points))
            self.points = []

    def resetImage(self):
        self.removeToolPointsFromImage()
        self.scanAxe.imshow(self.image, cmap="gray", origin='lower')
        self.logMessage.emit("Scan wurde zurückgesetzt")
        self.scanCanvas.canvas.draw()

    def startLineProfile(self):
        qtw.QApplication.setOverrideCursor(qtg.QCursor(qtc.Qt.CrossCursor))
        if self.cid != None:
            self.scanCanvas.canvas.mpl_disconnect(self.cid)
        self.removeToolPointsFromImage()
        self.logMessage.emit("Linienprofil-Werkzeug gestartet - 2 Punkte im Scan auswählen...")
        self.cid = self.scanCanvas.canvas.mpl_connect("button_press_event", self.onclick)
        self.mode = 1
    
    def startPlaneLevel(self):
        qtw.QApplication.setOverrideCursor(qtg.QCursor(qtc.Qt.CrossCursor))

        if self.cid != None:
            self.scanCanvas.canvas.mpl_disconnect(self.cid)
        qtw.QApplication.setOverrideCursor(qtg.QCursor(qtc.Qt.CrossCursor))
        self.removeToolPointsFromImage()

        self.logMessage.emit("Ebene-begradigen-Werkzeug gestartet - 3 Punkte im Scan auswählen...")

        self.cid = self.scanCanvas.canvas.mpl_connect("button_press_event", self.onclick)
        self.mode = 2



    def onclick(self, event):
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
        if self.mode == 1:
            if len(self.coordinates) == 2:
                self.scanCanvas.fig.canvas.mpl_disconnect(self.cid)
                self.calculateLineProfile()
        elif self.mode == 2:
            if len(self.coordinates) == 3:
                self.scanCanvas.fig.canvas.mpl_disconnect(self.cid)
                self.levelImageByPlane()

    def calculateLineProfile(self):
        x0, y0 = self.coordinates[0][0], self.coordinates[0][1]
        x1, y1 = self.coordinates[1][0], self.coordinates[1][1]
        length = int(np.hypot(x1-x0, y1-y0))

        xLine, yLine = np.linspace(x0, x1, length), np.linspace(y0, y1, length)
        lineValues = self.image[xLine.astype(np.int), yLine.astype(np.int)]
     
        self.lineProfileAxe.cla()
        
        self.lineProfileAxe.set_ylabel("Höhe")
        self.lineProfileAxe.set_title(
            "Linienprofil", fontweight="bold", fontname="Sans Serif", fontsize=14, loc="left")
        self.lineProfileAxe.plot(lineValues)
        self.scanCanvas.canvas.draw()
        self.reset()
        self.logMessage.emit("Linienprofil erfolgreich erzeugt")
        return

    def levelImageByPlane(self):
        x0, y0 = self.coordinates[0][0], self.coordinates[0][1]
        x1, y1 = self.coordinates[1][0], self.coordinates[1][1]
        x2, y2 = self.coordinates[2][0], self.coordinates[2][1]

        # p1 = np.array([x0, y0, self.image[int(x0), int(y0)]])
        # p2 = np.array([x1, y1, self.image[int(x1), int(y1)]])
        # p3 = np.array([x2, y2, self.image[int(x2), int(y2)]])

        # v1 = p3 - p1
        # v2 = p2 - p1
        # crossProd = np.cross(v1, v2)
        # a, b, c = crossProd

        # a, b, c = np.cross(v1, v2)
        # a, b, c = np.cross(p3 - p1, p2 - p1)
        # a, b, c = np.cross(np.array([x2, y2, self.image[int(x2), int(y2)]]) - np.array([x0, y0, self.image[int(x0), int(y0)]]), np.array([x1, y1, self.image[int(x1), int(y1)]]) - np.array([x0, y0, self.image[int(x0), int(y0)]]))
        # a, b, c = np.cross(np.array([x2, y2, self.image[int(x2), int(y2)]]) - np.array([x0, y0, self.image[int(x0), int(y0)]]), np.array([x1, y1, self.image[int(x1), int(y1)]]) - np.array([x0, y0, self.image[int(x0), int(y0)]]))

        # d = np.dot(crossProd, p3)
        # x = np.arange(0, stop=len(self.image), step=1) 
        # y = np.arange(0, stop=len(self.image[0]), step=1)

        # plane = (d - a*x - b*y) / c

        # plane = ( np.dot(crossProd, p3) - a*np.arange(0, stop=len(self.image), step=1) - b*np.arange(0, stop=len(self.image[0]), step=1) )/ c

        # leveledImage = np.subtract(self.image, plane)
        if self.changedImage != []:
            self.scanAxe.imshow(np.subtract(self.changedImage, ( np.dot(np.cross(np.array([x2, y2, self.image[int(x2), int(y2)]]) - np.array([x0, y0, self.image[int(x0), int(y0)]]), np.array([x1, y1, self.image[int(x1), int(y1)]]) - np.array([x0, y0, self.image[int(x0), int(y0)]])), np.array([x2, y2, self.image[int(x2), int(y2)]])) - np.cross(np.array([x2, y2, self.image[int(x2), int(y2)]]) - np.array([x0, y0, self.image[int(x0), int(y0)]]), np.array([x1, y1, self.image[int(x1), int(y1)]]) - np.array([x0, y0, self.image[int(x0), int(y0)]]))[0]*np.arange(0, stop=len(self.image), step=1) - np.cross(np.array([x2, y2, self.image[int(x2), int(y2)]]) - np.array([x0, y0, self.image[int(x0), int(y0)]]), np.array([x1, y1, self.image[int(x1), int(y1)]]) - np.array([x0, y0, self.image[int(x0), int(y0)]]))[1]*np.arange(0, stop=len(self.image[0]), step=1) )/ np.cross(np.array([x2, y2, self.image[int(x2), int(y2)]]) - np.array([x0, y0, self.image[int(x0), int(y0)]]), np.array([x1, y1, self.image[int(x1), int(y1)]]) - np.array([x0, y0, self.image[int(x0), int(y0)]]))[2]), cmap="gray", origin='lower')
        else: 
            self.changedImage = np.subtract(self.image, ( np.dot(np.cross(np.array([x2, y2, self.image[int(x2), int(y2)]]) - np.array([x0, y0, self.image[int(x0), int(y0)]]), np.array([x1, y1, self.image[int(x1), int(y1)]]) - np.array([x0, y0, self.image[int(x0), int(y0)]])), np.array([x2, y2, self.image[int(x2), int(y2)]])) - np.cross(np.array([x2, y2, self.image[int(x2), int(y2)]]) - np.array([x0, y0, self.image[int(x0), int(y0)]]), np.array([x1, y1, self.image[int(x1), int(y1)]]) - np.array([x0, y0, self.image[int(x0), int(y0)]]))[0]*np.arange(0, stop=len(self.image), step=1) - np.cross(np.array([x2, y2, self.image[int(x2), int(y2)]]) - np.array([x0, y0, self.image[int(x0), int(y0)]]), np.array([x1, y1, self.image[int(x1), int(y1)]]) - np.array([x0, y0, self.image[int(x0), int(y0)]]))[1]*np.arange(0, stop=len(self.image[0]), step=1) )/ np.cross(np.array([x2, y2, self.image[int(x2), int(y2)]]) - np.array([x0, y0, self.image[int(x0), int(y0)]]), np.array([x1, y1, self.image[int(x1), int(y1)]]) - np.array([x0, y0, self.image[int(x0), int(y0)]]))[2])

            self.scanAxe.imshow(self.changedImage, cmap="gray", origin='lower')

        self.scanCanvas.canvas.draw()
        
        self.logMessage.emit("Ebene erfolgreich begradigt")
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
