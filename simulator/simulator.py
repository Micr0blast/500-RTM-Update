import sys
from PySide2 import QtWidgets as qtw
from PySide2 import QtGui as qtg
from PySide2 import QtCore as qtc


# from model.Model import Model
from simulator.view.simulatorView import SimulatorView
from simulator.model.simulatorModel import SimulatorModel

screwMin = 50
screwMax = 150
stepSize = 0.01
default = 0
notchesVisible = False

class ScanTimerThread(qtc.QThread):
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

# class ScanTimerThread_Two(qtc.QThread):
    
#     timeout = qtc.Signal()
#     def __init__(self, secondsPerIteration, iterations):
#         qtc.QThread.__init__(self)
#         self.seconds = secondsPerIteration
#         self.iterations = iterations

#     def run(self):
        
#         print("Thread started")
#         for i in range(iterations): 
#             time.sleep(self.seconds)
#             self.timeout.emit()



# class Worker(qtc.QRunnable):
#     '''
#     Worker thread
#     '''

#     timeout = qtc.Signal()

#     def __init__(self,  iterations, time=1):
#         super(Worker, self).__init__()
#         self.timeToWait =  time
#         self.iterations = iterations

#     def run(self):
#         '''
#         Your code goes in this function
#         '''
#         for i in range(self.iterations):
#             time.sleep(self.time)
#             self.timeout.emit()
#         print("Thread complete")

class SimulatorWindow(qtw.QMainWindow):

    transmitTunnelCurrent = qtc.Signal(float)
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
        self.view = SimulatorView(
            screwMin, screwMax, stepSize, default, notchesVisible)

        # import sim mod
        # connect with play button pressed
        # send image data to view or send lines to view for update
        self.model = SimulatorModel()
        self.view.materialChosen.connect(self.model.setCurrentImage)
        self.view.valuesChanged.connect(self.model.updateTunnelCurrent)

        self.setCentralWidget(self.view)
        self.menuBar = self.setupMenuBar()
        self.setMenuBar(self.menuBar)

        # handles tunnelCurrent updates
        self.timer = qtc.QTimer()
        self.timer.setInterval(50)
        self.timer.timeout.connect(self.sendTunnelCurrent)
        self.timer.start()

        # self.threadpool = qtc.QThreadPool()

        
        

        self.model.scanFinished.connect(self.endScan)
        

        # End main UI code
        self.show()

    def setupMenuBar(self):
        menuBar = self.menuBar()
        self.fileMenu = menuBar.addMenu('File')
        # add reset state action
        

        self.closeAction = qtw.QAction(
            self.style().standardIcon(qtw.QStyle.SP_DockWidgetCloseButton),
            "Beenden",
            self,
            triggered=self.closeWindow
        )

        self.fileMenu.addAction(self.closeAction)
        

        return menuBar

    def closeWindow(self):
        self.view.valuesChanged.disconnect(self.model.updateTunnelCurrent)
        self.view.timer.timeout.disconnect(self.sendTunnelCurrent)
        self.close()

    def sendTunnelCurrent(self):
        self.transmitTunnelCurrent.emit(self.model.getTunnelCurrent())

    def updateControlParameters(self, args):
        biasV , pGain, iGain, zHeight = args

        self.model.setPidParams(ki = iGain, kp= pGain, setpoint=zHeight)
        
    def startScan(self, args):
        pGain, iGain, zHeight, xStart, yStart, xEnd, yEnd, direction, breadth, biasV = args
        self.model.setPidParams(pGain, iGain, zHeight)
        self.model.setBiasVoltage(biasV)

        # print("Timer started")
       
        # qtc.QTimer.singleShot(2000, lambda: self.model.getScanImage(xStart, yStart, xEnd, yEnd, direction, yEnd, breadth))

        self.scanCallLambda = lambda startX = xStart, startY = yStart, endX = xEnd, endY = yEnd, dir = direction, vel = breadth: self.emitImg(startX, startY, endX, endY, dir, vel)

        currentVal = self.model.getTunnelCurrent()
        if  currentVal < 1e-9:
            self.logMessage.emit("Tunnelstrom zu niedrig - Scan vermutlich schwarz")
        if currentVal >= 10e-8:
            self.logMessage.emit("Tunnelstrom zu hoch - Scan vermutlich weiß oder verrauscht")

        # qtc.QTimer.singleShot(2000, 
        #     lambda startX = xStart, startY = yStart, endX = xEnd, endY = yEnd, dir = direction, vel = breadth:
        #     self.emitImg(startX, startY, endX, endY, dir, vel))
        self.scanTimerThread = ScanTimerThread()
        self.scanTimerThread.start()

        self.scanTimerThread.scanTimer.timeout.connect(self.scanCallLambda)
        
        # self.logMessage.emit("Thread started")
        

    def endScan(self):
        
        self.logMessage.emit("Scan wurde erfolgreich beendet")
        self.model.scanFinished.emit()
        self.resetScanVariables()
        # self.scanTimerThread.stopTimer()
        # self.scanFinished.emit()
        # self.scanTimerThread.scanTimer.timeout.disconnect(self.scanCallLambda)
        self.scanTimerThread.scanTimer.timeout.disconnect()

        self.scanTimerThread.terminate()
        



    def emitImg(self, startX, startY, lengthX, lengthY, direction, breadth):
        self.startLineIdx = startY
        
        if self.startLineIdx != startY:
            
            self.currentLineIdx = 1
            print("Case 1")
        elif self.currentLineIdx < lengthY:
            self.currentLineIdx += 1
            print("Case 2")
        else: 
            print("Case 3")
            self.endScan()
            
            return
        
        # self.currentLineIdx = lengthY
        
        
        self.transmitScanImg.emit(self.model.getScanImage(startX, startY, lengthX, self.currentLineIdx, direction, lengthY, breadth))
        


    def resetScanVariables(self):
        self.startLineIdx = 0
        self.currentLineIdx = 0

    def stopScan(self):
        self.scanTimerThread.scanTimer.timeout.disconnect(self.scanCallLambda)

        self.resetScanVariables()
        
        # print("timer stopped")
        # self.scanFinished.emit()
        # self.scanTimerThread.stopTimer()
        self.scanTimerThread.terminate()

    def pauseScan(self):
        
        self.scanTimerThread.scanTimer.timeout.disconnect(self.scanCallLambda)

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
