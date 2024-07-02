import sys
from PySide6 import QtWidgets as qtw
from PySide6 import QtGui   as qtg
from PySide6 import QtCore as qtc

from simulator.view.simulatorView import SimulatorView
from simulator.model.simulatorModel import LOWER_CURRENT_BOUND, PATH_TO_IMAGES, SimulatorModel, UPPER_CURRENT_BOUND

SCREW_MIN = 50
SCREW_MAX = 150
SCREW_STEP = 0.01
SCREW_DEFAULT = 0
SCREW_NOTCHES_VISIBLE = False

TUNNELING_CURRENT_INTERVAL = 50
SCAN_UPDATE_INTERVAL = 500

PATH_TO_IMAGES = "simulator/img"
UPPER_CURRENT_BOUND= 1e-7
LOWER_CURRENT_BOUND= 1e-9

LOG_CURRENT_TOO_HIGH_MSG = "Tunnelstrom zu hoch - Scan vermutlich weiß oder verrauscht"
LOG_CURRENT_TOO_LOW_MSG ="Tunnelstrom zu niedrig - Scan vermutlich schwarz"

    # TODO: ADD PROPER END SIMULATION FUNCTIONALITY 
    # TODO: ADD VIEW BUTTON IN MAIN WINDOW TO REDISPLAY SIMULATOR

class ScanTimerThread(qtc.QThread):
    """ This class represents a custom thread whith its own timer
    """
    def __init__(self, intervalTime=300):
        qtc.QThread.__init__(self)
        self.scanTimer = qtc.QTimer()
        self.scanTimer.setInterval(intervalTime)
        self.scanTimer.moveToThread(self)

    def run(self):
        self.scanTimer.start()
        # print("Thread started")
        loop = qtc.QEventLoop()
        loop.exec_()


class SimulatorWindow(qtw.QMainWindow):

    transmitTunnelCurrent = qtc.Signal(float,float)
    transmitScanImg = qtc.Signal(list)
    transmitLineProfile = qtc.Signal(list)

    scanFinished = qtc.Signal()

    logMessage = qtc.Signal(str)


    startLineIdx: int = 0
    currentLineIdx: int = 0
    timer = None

    # threadpool = None

    def __init__(self):
        """MainWindow constructor.

        This widget will be our main window.
        We'll define all the UI components in here.
        """
        super().__init__()

        self.setWindowTitle("Simulator")
        # Main UI code goes here
        self.view = SimulatorView(SCREW_MIN, SCREW_MAX, SCREW_STEP, SCREW_DEFAULT, SCREW_NOTCHES_VISIBLE)

        self.model = SimulatorModel(pathToImages=PATH_TO_IMAGES, lowerCurrentBound=LOWER_CURRENT_BOUND, upperCurrentBound=UPPER_CURRENT_BOUND)
        self.view.materialChosen.connect(self.model.setCurrentImage)
        self.view.valuesChanged.connect(self.model.updateTunnelCurrent)

        self.setCentralWidget(self.view)
        self.menuBar = self.setupMenuBar()
        self.setMenuBar(self.menuBar)

        # handles tunnelCurrent updates
        self.timer = qtc.QTimer()
        self.timer.setInterval(TUNNELING_CURRENT_INTERVAL)
        self.timer.timeout.connect(self.sendTunnelCurrent)
        self.timer.start()
        
        

        self.model.scanFinished.connect(self.endScan)
        # End main UI code
        self.show()

    def setupMenuBar(self):
        """Sets up the menu bar
        This uses the QMainWindow widget's menuBar property

        Returns:
            [type]: [description]
        """
        menuBar = self.menuBar()
        self.fileMenu = menuBar.addMenu('File')
        self.closeAction = qtg.QAction(
            self.style().standardIcon(qtw.QStyle.SP_DockWidgetCloseButton),
            "Beenden",
            self,
            triggered=self.closeWindow
        )

        self.fileMenu.addAction(self.closeAction)
        

        return menuBar

    def closeWindow(self):
        """If the Simulator is closed via the file menu action it will be disconnected
        """
        self.view.valuesChanged.disconnect(self.model.updateTunnelCurrent)
        self.view.timer.timeout.disconnect(self.sendTunnelCurrent)
        self.close()

    def sendTunnelCurrent(self):
        """Emits the models current tunneling current
        """
        self.transmitTunnelCurrent.emit(self.model.getTunnelCurrent(),self.model.getTargetCurrent())

    def updateControlParameters(self, args):
        """Updates the models PID parameters

        Args:
            args (float, float, float, float): BiasVoltage, proportional Gain, integral Gain, Setpoint
        """
        biasV , pGain, iGain, zHeight = args

        self.model.setPidParams(ki = iGain, kp= pGain, setpoint=zHeight)
        self.model.setBiasVoltage(biasV)
        
    def startScan(self, args):
        """This function starts a scan and takes all the current parameters of the main GUI
        It will start a thread for the process to run on and then pass the updates to self.emitImg

        Args:
            args (float, float, float, int, int ,int ,int ,int, float, float): 
            proportional Gain, integral Gain, Setpoint, Start Coordinate x, start Coordinate y, End Coordinate in x, End Coordinate in y, Tip breadh, BiasVoltage
        """
        pGain, iGain, zHeight, xStart, yStart, xEnd, yEnd, direction, breadth, biasV = args
        self.model.setPidParams(pGain, iGain, zHeight)
        self.model.setBiasVoltage(biasV)

        self.scanCallLambda = lambda startX = xStart, startY = yStart, endX = xEnd, endY = yEnd, dir = direction, vel = breadth: self.emitImg(startX, startY, endX, endY, dir, vel)

        currentVal = self.model.getTunnelCurrent()
        if  currentVal < LOWER_CURRENT_BOUND:
            self.logMessage.emit(LOG_CURRENT_TOO_LOW_MSG)
        if currentVal >= UPPER_CURRENT_BOUND:
            self.logMessage.emit(LOG_CURRENT_TOO_HIGH_MSG)

        self.scanTimerThread = ScanTimerThread(SCAN_UPDATE_INTERVAL)
        self.scanTimerThread.start()

        self.scanTimerThread.scanTimer.timeout.connect(self.scanCallLambda)
        
    def endScan(self):
        """Cleans up after scan
        """
        
        self.logMessage.emit("Scan wurde erfolgreich beendet")

        self.resetScanVariables()
        self.scanTimerThread.scanTimer.timeout.disconnect()

        self.scanTimerThread.terminate()
        
    def emitImg(self, startX, startY, lengthX, lengthY, direction, breadth):
        """Handels line by line emission of scans
        """
        self.startLineIdx = startY
        
        if self.startLineIdx != startY:
            self.currentLineIdx = 1
        elif self.currentLineIdx < lengthY:
            self.currentLineIdx += 1
        else: 
            self.endScan()
            return
        
        
        self.transmitScanImg.emit(self.model.getScanImage(startX, startY, lengthX, self.currentLineIdx, direction, lengthY, breadth))
        


    def resetScanVariables(self):
        self.startLineIdx = 0
        self.currentLineIdx = 0

    def stopScan(self):
        self.scanTimerThread.scanTimer.timeout.disconnect()
        self.resetScanVariables()
        self.scanTimerThread.terminate()

    def pauseScan(self):
        self.scanTimerThread.scanTimer.timeout.disconnect()

    def resumeScan(self):
        self.scanTimerThread.scanTimer.timeout.connect(self.scanCallLambda)

    # # TODO
    # def sendScanLine(self):
    #     self.transmitScanLine.emit(self.model.getScanLine())


if __name__ == '__main__':
    app = qtw.QApplication(sys.argv)
    # it's required to save a reference to MainWindow.
    # if it goes out of scope, it will be destroyed.
    mw = SimulatorWindow()
    sys.exit(app.exec_())
