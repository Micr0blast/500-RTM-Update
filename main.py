import sys

from PySide2 import QtWidgets as qtw
from PySide2 import QtGui as qtg
from PySide2 import QtCore as qtc
import numpy as np
import tifffile

from widgets.resources import *

from widgets.centralPlotWidget import CentralPlotWidget
from simulator.simulator import SimulatorWindow
from widgets.canvas import Canvas


class ValueRadioButton(qtw.QRadioButton):
    def __init__(self):
        super(ValueRadioButton, self).__init__()
        self.value = None

    def setValue(self, val):
        self.value = val

    def getValue(self):
        return self.value


class MainWindow(qtw.QMainWindow):

    microscope = None
    imgData = []

    isMidScan = False

    def __init__(self):
        """MainWindow constructor.

        This widget will be our main window.
        We'll define all the UI components in here.
        """
        super().__init__()
        # Main UI code goes here

        self.redLEDPxm = qtg.QPixmap(":/icons/led_red.png").scaled(16,16,qtc.Qt.KeepAspectRatio)
        self.greenLEDPxm = qtg.QPixmap(":/icons/led_green.png").scaled(16,16,qtc.Qt.KeepAspectRatio)

        self.setWindowTitle("STM Scan UI")
        self.resize(1200, 800)

        self.menuBar = self.menuBar()
        self.fileMenu = self.menuBar.addMenu("Datei")
        self.helpMenu = self.menuBar.addMenu("Hilfe")

        self.openAction = qtw.QAction(
            self.style().standardIcon(qtw.QStyle.SP_DirOpenIcon),
            "Dateispeicherort auswhälen",
            self,
            triggered=self.showChooseSaveDirDialog
        )

        self.closeAction = qtw.QAction(
            self.style().standardIcon(qtw.QStyle.SP_DockWidgetCloseButton),
            "Beenden",
            self,
            triggered=self.close
        )
        self.saveAction = qtw.QAction(
            self.style().standardIcon(qtw.QStyle.SP_DriveCDIcon),
            "Scan Speichern...",
            self,
            triggered=self.saveScan
        )

        # self.fileMenu.addAction(self.openAction)
        # self.fileMenu.addAction(self.saveAction)
        self.fileMenu.addAction(self.closeAction)

        # statusbar
        self.statusBar = qtw.QStatusBar(parent=self)
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Welcome to the 500€ RTM")
        self.scannerStatusLabel = qtw.QLabel("Standby")
        self.statusBar.addPermanentWidget(self.scannerStatusLabel)

        # toolbar
        # self.setupToolBar()
        
        
        self.setupLogDock()

        # self.setupFileTree()

        self.setupTabs()

        self.setupExperimentDock()

        # self.showSplashScreen()

        self.setStyleSheet(
            """
            QTextEdit {
                font-size: 14px;
            }
            QPushButton {
                color: #333;
                font-size: 12px;
                font-weight: bold;
            }
            QLabel {
                font-size: 12px;
            }
            QTabBar::tab {
                background: #ccc;
                font-weight: bold;
                padding: 8px;
                margin: 12px 12px 0 12px;
                height: 32px;
                width: 86px;
                
                border: solid 3px gray;
                }
            QTabBar::tab:selected {background: #fff;}
            QTabWidget>QWidget>QWidget {
                margin: 12px;
                }
            """
        )

        
        self.layout().setContentsMargins(128, 128, 128, 32)

        # End main UI code
        self.show()

        # self.showIntroScreen()
 
    def setupExperimentDock(self):
        # each param has a box and a slider in dependence on one another
        # each box has a validator constraining it to certain values
        # 2 rows
        self.experimentDock = qtw.QDockWidget("Scan-Parameter")
        self.experimentDock.setTitleBarWidget(qtw.QWidget(self))
        self.experimentDock.setFeatures(qtw.QDockWidget.NoDockWidgetFeatures)
        self.addDockWidget(qtc.Qt.RightDockWidgetArea, self.experimentDock)

        self.expDockWidgetContainer = qtw.QWidget()
        self.expDockWidgetContainer.setLayout(qtw.QVBoxLayout())
        self.experimentDock.setWidget(self.expDockWidgetContainer)

        self.piGroupBox = qtw.QGroupBox("Regel-Parameter", self)
        self.piGroupBox.setStyleSheet("QGroupBox {font-weight: bold;}")
        self.piGroupBox.resize(60, 180)
        self.piGroupBox.setLayout(qtw.QVBoxLayout())
        self.piGroupBox.layout().setAlignment(qtc.Qt.AlignCenter)

        
        self.biasVoltageRow = self.createParameterRow("Bias-Spannung", "0.1", "0.1 - 1.0 V", double=True, top=1.0, bottom=0.1)
        self.pGainRow = self.createParameterRow("kP:", "2", "0-100000", double=True, bottom=0, top=100000)
        self.iGainRow = self.createParameterRow("kI:", "0.5", "0-100000", double=True, bottom=0, top=100000)
        self.zHeightRow = self.createParameterRow("Zielstrom:", "20", "10-100nA")
        self.updateControlParametersBtn = qtw.QPushButton("Parameter aktualisieren", clicked=self.updateParametersHandler)

        self.piGroupBox.layout().addWidget(self.biasVoltageRow) # TODO : ADD TO SIMULATOR
        self.piGroupBox.layout().addWidget(self.pGainRow)
        self.piGroupBox.layout().addWidget(self.iGainRow)
        self.piGroupBox.layout().addWidget(self.zHeightRow)

        self.piGroupBox.layout().addWidget(self.updateControlParametersBtn)
        

        self.scanGroupBox = qtw.QGroupBox("Scan-Parameter", self)
        self.scanGroupBox.setStyleSheet("QGroupBox {font-weight: bold;}")
        self.scanGroupBox.setLayout(qtw.QVBoxLayout())

        self.xStartRow = self.createParameterRow("Startkoordinate X:","250", "0 - 4000")
        self.yStartRow = self.createParameterRow("Startkoordinate Y:", "250", "0 - 4000")
        self.xEndRow = self.createParameterRow("Auflösung", "250", "Pixel x Pixel")
        # self.yEndRow = self.createParameterRow("Höhe", "500", "Pixel")
        self.scanGroupBox.layout().addWidget(self.xStartRow)
        self.scanGroupBox.layout().addWidget(self.yStartRow)
        self.scanGroupBox.layout().addWidget(self.xEndRow)
        # self.scanGroupBox.layout().addWidget(self.yEndRow)

        self.directionRow = qtw.QWidget()
        self.directionRow.setLayout(qtw.QHBoxLayout())
        self.directionRow.layout().addWidget(qtw.QLabel("relative Scan-Richtung:", self))
        self.radioDirectionLeft = ValueRadioButton()
        self.radioDirectionLeft.setChecked(True)
        self.radioDirectionLeft.setValue(0)
        self.radioDirectionLeft.setText("Links")
        self.radioDirectionRight = ValueRadioButton()
        self.radioDirectionRight.setText("Rechts")
        self.radioDirectionRight.setValue(1)

        self.directionRow.layout().addWidget(self.radioDirectionLeft)
        self.directionRow.layout().addWidget(self.radioDirectionRight)

        self.scanGroupBox.layout().addWidget(self.directionRow)

        ## remove
        # self.multiplierRow = self.createParameterRow(
        #     "DAC-Multiplikator", "1", "1 - 100")
        # self.scanGroupBox.layout().addWidget(self.multiplierRow)

        self.scanVelocityRow = self.createParameterRow(
            "Scan-Breite", "0.2", "0.1 - 20.0 mV/px", True, 0.1, 20
        )
        self.scanGroupBox.layout().addWidget(self.scanVelocityRow)

        self.controlGroupBox = qtw.QGroupBox("Scan-Controls", self)
        self.controlGroupBox.setStyleSheet("QGroupBox {font-weight: bold;}")
        self.startBtn =  qtw.QPushButton("Start", clicked=self.startHandler )
        self.startBtn.setShortcut("Return")
        self.pauseBtn =  qtw.QPushButton("Pause", clicked=self.pauseHandler)
        self.stopBtn =  qtw.QPushButton("Stop", clicked=self.stopHandler)
        self.pauseBtn.setEnabled(False)
        self.stopBtn.setEnabled(False)
        self.controlGroupBox.setLayout(qtw.QVBoxLayout())
        self.controlGroupBox.layout().addWidget(self.startBtn)
        self.controlGroupBox.layout().addWidget(self.pauseBtn)
        self.controlGroupBox.layout().addWidget(self.stopBtn)

        self.expDockWidgetContainer.layout().addWidget(self.piGroupBox)
        self.expDockWidgetContainer.layout().addWidget(self.scanGroupBox)
        self.expDockWidgetContainer.layout().addWidget(self.controlGroupBox)
        self.expDockWidgetContainer.layout().addStretch()

    def getExperimentParameters(self):
        biasV = float(self.biasVoltageRow.children()[2].text())
        pGain = float(self.pGainRow.children()[2].text())
        iGain = float(self.iGainRow.children()[2].text())
        zHeight = float(self.zHeightRow.children()[2].text())
        xStart = int(self.xStartRow.children()[2].text())
        yStart = int(self.yStartRow.children()[2].text())
        xEnd = int(self.xEndRow.children()[2].text())
        # yEnd = int(self.yEndRow.children()[2].text())
        yEnd = xEnd

        direction = 0 if self.directionRow.children()[2].isChecked() else 1
        # multiplier = int(self.multiplierRow.children()[2].text())
        velocity = float(self.scanVelocityRow.children()[2].text())

        return (pGain, iGain, zHeight, xStart, yStart, xEnd, yEnd, direction, velocity, biasV)

    def updateParametersHandler(self):
        biasV = float(self.biasVoltageRow.children()[2].text())
        pGain = float(self.pGainRow.children()[2].text())
        iGain = float(self.iGainRow.children()[2].text())
        zHeight = float(self.zHeightRow.children()[2].text())

        if self.microscope != None:
            self.microscope.updateControlParameters((biasV, pGain, iGain, zHeight))
            self.updateLog("Kontroll-Parameter aktualisiert.")
        else:
            self.updateLog("RTM auswählen um Kontroll-Parameter zu aktualisieren.")

   
    def setupToolBar(self):
        self.toolBar = qtw.QToolBar("Scan")
        self.toolBar.setMovable(False)
        self.toolBar.setFloatable(False)

        self.lineProfileAction = qtw.QAction(
            "Linienprofil erzeugen",
            self,
            triggered=self.actionNotImplemented
        )
        self.adjustLevelsAction = qtw.QAction(
            "Graustufen anpassen",
            self,
            triggered=self.actionNotImplemented
        )
        self.levelPlaneAction = qtw.QAction(
            "Ebenen angleichen",
            self,
            triggered=self.actionNotImplemented
        )
        self.toolBar.addAction(self.lineProfileAction)
        self.toolBar.addAction(self.adjustLevelsAction)
        self.toolBar.addAction(self.levelPlaneAction)

        self.addToolBar(qtc.Qt.TopToolBarArea, self.toolBar)

    def actionNotImplemented(self):
        self.updateLog("Feature wurde noch nicht implementiert")

    def showIntroScreen(self):
        self.introScreen = qtw.QMessageBox()
        self.introScreen.resize(126, 98)
        self.introScreen.setWindowTitle("Wilkommen!")
        self.introScreen.setText("Wilkommen zum 500€-RTM GUI")
        self.introScreen.setInformativeText(
            "Als erstes müssen Sie einen Ordner festlegen,"
            "in dem die Projektdaten gespeichert werden sollen"
        )

        self.introScreen.setWindowModality(qtc.Qt.WindowModal)
        self.introScreen.addButton("Ordner auswählen", qtw.QMessageBox.YesRole)
        self.introScreen.addButton(qtw.QMessageBox.Close)

        response = self.introScreen.exec_()
        if response == 0:
            self.showChooseSaveDirDialog()

    def showSplashScreen(self):
        self.splashScreen = qtw.QMessageBox()
        self.splashScreen.setWindowTitle("500€-RTM GIU")
        self.splashScreen.setText("Beta Software Warning!")
        self.splashScreen.setInformativeText(
            "This is very beta software, "
            "are you really sure you want to use it?"
        )

        self.splashScreen.setDetailedText(
            "This Scan UI was written for educational purpose for the 500€-RTM project"
        )

        # set to modal, otherwise the dialog won't return a response
        self.splashScreen.setWindowModality(qtc.Qt.WindowModal)
        self.splashScreen.addButton(qtw.QMessageBox.Yes)
        self.splashScreen.addButton(qtw.QMessageBox.Abort)

        response = self.splashScreen.exec_()
        if response == qtw.QMessageBox.Abort:
            self.close()
            sys.exit()

    def setupFileTree(self):
        # self show Dialog
        # docks
        self.fileTreeDock = qtw.QDockWidget("Projektordner")
        self.addDockWidget(qtc.Qt.LeftDockWidgetArea, self.fileTreeDock)
        self.fileTreeDock.setFeatures(
            qtw.QDockWidget.DockWidgetClosable
        )

        # filetree
        self.fileTreeWidget = qtw.QWidget()
        self.fileTreeWidget.setLayout(qtw.QHBoxLayout())
        self.fileTreeDock.setWidget(self.fileTreeWidget)
        self.fileModel = qtw.QFileSystemModel()
        self.fileModel.setResolveSymlinks(False)
        self.fileModel.setRootPath(qtc.QDir.homePath())
        self.fileModel.setNameFilters(
            ['*.ome.tif', '*.ome.tiff', 'ome.tf2', 'ome.tf8', 'ome.btf'])
        self.treeView = qtw.QTreeView()
        self.treeView.setModel(self.fileModel)
        self.treeView.setIndentation(10)
        self.treeView.setSortingEnabled(True)
        self.treeView.setWindowTitle("Projektordner")

        self.fileTreeWidget.layout().addWidget(self.treeView)

    def setupLogDock(self):
        self.spiDock = qtw.QDockWidget("Log")
        
        self.spiDock.setFeatures(qtw.QDockWidget.NoDockWidgetFeatures)
        self.addDockWidget(qtc.Qt.BottomDockWidgetArea, self.spiDock)

        self.logWidget = qtw.QWidget()
        self.logWidget.setLayout(qtw.QVBoxLayout())
        self.spiDock.setWidget(self.logWidget)

        self.logTextArea = qtw.QTextEdit("", readOnly=True)
        self.logTextArea.setUndoRedoEnabled(False)
        self.logTextArea.setStyleSheet("""
                QTextEdit { 
                    background: black;
                    color: white;
                } 
            """)
        self.logWidget.layout().addWidget(self.logTextArea)

    def updateLog(self, update):
        self.logTextArea.append(update)

    def createParameterRow(self, label: str, placeholder: str, unitLabel: str, double=False, bottom=0.1, top=5.0) -> qtw.QWidget:
        container = qtw.QWidget(self)
        container.setLayout(qtw.QHBoxLayout())
        container.layout().setAlignment(qtc.Qt.AlignCenter)
        rowLbl = qtw.QLabel(text=label, parent=self)
        rowEdit = qtw.QLineEdit(placeholder)
        rowEdit.setMaximumWidth(30)
        if double:
            validator = qtg.QDoubleValidator(bottom, top,2, parent=self)
            validator.setNotation(qtg.QDoubleValidator.StandardNotation)
        else:
            validator = qtg.QIntValidator(self)
        rowEdit.setValidator(validator)
        unitLbl = qtw.QLabel(text=unitLabel, parent=self)

        container.layout().addStretch()
        container.layout().addWidget(rowLbl)
        container.layout().addWidget(rowEdit)
        container.layout().addWidget(unitLbl)
        # container.layout().addStretch()

        return container

    def saveScan(self):

        if self.imgData != None:
            fileName = qtw.QFileDialog.getSaveFileName(
                self, 
                "Datei speichern unter...",
                "",
                "TIFF Files (*.tif  *.ome.tif)")
            tifffile.imsave(fileName[0], data=self.imgData, photometric="minisblack")
            self.updateLog(f"Scan wurder unter {fileName} gespeichert")
        else:
            self.updateLog("Es ist noch kein Scan vorhanden")

    
    def showChooseSaveDirDialog(self):
        folderName = qtw.QFileDialog.getExistingDirectory(
            self,
            "Projektordner auswählen",
            qtc.QDir.homePath()
        )
        if folderName:
            try:
                self.treeView.setRootIndex(self.fileModel.index(folderName))
            except Exception as e:
                qtw.QMessageBox.critical(
                    f'Ordner konnte nicht geöffnet werden: {e}')
            
        
    
    def setupTabs(self):
        # tab containers
        self.tabWidget = qtw.QTabWidget()
        
        self.setCentralWidget(self.tabWidget)
        self.tabWidget.setTabPosition(qtw.QTabWidget.North)
        
        self.prepContainer = qtw.QWidget()
        self.scanContainer = qtw.QWidget()

        self.prepContainer.setLayout(qtw.QVBoxLayout())
        self.prepContainer.layout().setSpacing(36)

        nData = 100
        self.xData = np.arange(nData)
        self.yData = np.zeros(nData)
        self.prepCanvas = Canvas(self)
        self.prepAxe = self.prepCanvas.fig.add_subplot(111)
        self.prepAxe.plot(self.xData, self.yData, linewidth=4, color="r", label="Tunnelstrom")
        self.prepAxe.legend()
        self.prepAxe.set_ylim(0, 10e-8)

        

        self.prepAxe.set_xlabel("t")
        self.prepAxe.set_ylabel("Tunnelstrom")
        self.prepAxe.autoscale(False)
        self.prepCanvas.setSizePolicy(
            qtw.QSizePolicy(qtw.QSizePolicy.Expanding,
                            qtw.QSizePolicy.Expanding)
        )

        self.prepCanvas.canvas.draw()

        self.prepLbl = qtw.QLabel("Vorbereitung")
        self.prepLbl.setFont(qtg.QFont("SansSerif", 16, qtg.QFont.Bold))

        # RTM Connectivity
        self.prepDescrLbl = qtw.QLabel("Wählen Sie das RTM aus:")
        self.prepDescrLbl.setStyleSheet("padding-left: 16px")
        self.rtmSelectRow = qtw.QHBoxLayout()
        self.rtmSelectRow.setSpacing(12)

        self.rtmComboBox = qtw.QComboBox()
        self.rtmComboBox.setStyleSheet("max-width: 128px")
        # self.rtmStateLbl = qtw.QLabel("Status: ")
        self.rtmStateLED = qtw.QLabel("Status")
        self.rtmStateLED.setPixmap(self.redLEDPxm)
        self.rtmBtn = qtw.QPushButton("Liste updaten")
        self.rtmConnectBtn = qtw.QPushButton("Verbinden")
        self.rtmComboBox.setStyleSheet("max-width: 128px")

        self.rtmComboBox.addItem("Auswählen...")
        self.rtmComboBox.model().item(0).setEnabled(False)
        self.rtmComboBox.addItem("Simulator")

        self.rtmSelectRow.addWidget(self.prepDescrLbl)
        self.rtmSelectRow.addWidget(self.rtmComboBox)
        self.rtmSelectRow.addWidget(self.rtmBtn)
        self.rtmSelectRow.addWidget(self.rtmConnectBtn)
        self.rtmSelectRow.addWidget(qtw.QLabel("Status:"))
        self.rtmSelectRow.addWidget(self.rtmStateLED)
        self.rtmSelectRow.addStretch()

        self.rtmConnectBtn.clicked.connect(self.connectWithRTM)

        self.prepCondDescrLbl = qtw.QLabel(
            "Nähern Sie die Spitze am Mikroskop an das eingelegte Material an, bis ein Tunnelstrom fließt")
        self.prepCondDescrLbl.setStyleSheet("margin-top:60px")
        
        self.prepCondDescrLbl.setFont(qtg.QFont("SansSerif", 14, qtg.QFont.Bold))

        self.prepContainer.layout().addWidget(self.prepLbl)
        self.prepContainer.layout().addLayout(self.rtmSelectRow)
        self.prepContainer.layout().addWidget(self.prepCondDescrLbl)

        # if rtm selected show anweisung

        self.prepContainer.layout().addWidget(self.prepCanvas)

        self.scanContainer.setLayout(qtw.QHBoxLayout())

        self.centrWidget = CentralPlotWidget()
        self.scanContainer.layout().addWidget(self.centrWidget)
        self.centrWidget.logMessage.connect(self.updateLog)

        self.tabWidget.addTab(self.prepContainer, "Vorbereitung")

        self.tabWidget.addTab(self.scanContainer, "Scans")

    def updateScanCanvas(self, img):
        print("Updated Image")
        self.imgData = img
        self.centrWidget.updateImage(self.imgData)
        self.statusBar.showMessage("Scan aktualisiert", 1000)

        # qtw.QApplication.allWidgets()
        # gc.collect()
        
        # self.updateLog("Scan aktualisiert.")

    def connectWithRTM(self):
        selected = self.rtmComboBox.currentIndex()
        if selected == 1:
            self.updateLog("Verbindung wird aufgebaut...")
            qtc.QTimer.singleShot(2000, lambda: self.showSimulator())
        else:
            # init rtm connection
            return None

    def updatePlot(self, emission):
        # Drop off the first y element, append a new one.
        if emission > 10e-8:
            emission = 10e-8
        self.yData = np.append(self.yData[1:], emission)
        self.prepAxe.cla()  
        self.prepAxe.plot(self.xData, self.yData, lw="4", color='g', label="Tunnelstrom")
        self.prepAxe.axhline(y=self.microscope.model.getTargetCurrent(), linestyle="--", label="Zieltunnelstrom")   
        self.prepAxe.legend() 

        self.prepAxe.set_ylim(0, 1e-7)

        self.prepAxe.set_xlabel("t")
        self.prepAxe.set_ylabel("Tunnelstrom")
        self.prepCanvas.canvas.draw()
        

    def showSimulator(self):
        if self.microscope is None:
            self.microscope = SimulatorWindow()
            self.microscope.transmitTunnelCurrent.connect(self.updatePlot)
            self.microscope.logMessage.connect(self.updateLog)
            self.rtmStateLED.setPixmap(self.greenLEDPxm)
            self.microscope.scanFinished.connect(self.stopHandler)
            self.updateLog("Verbindung hergestellt!")
            self.microscope.show()
        else:
            self.microscope.show()

    def startHandler(self):

        # disable start button
        
        params = self.getExperimentParameters()
        
        
        if self.microscope is None:
            qtw.QMessageBox.warning(self,
                                    "Mikroskop Verbinden!",
                                    "Es muss eine Verbindung zu einem Rastertunnelmikroskop bestehen um einen Scan zu starten!")
        elif self.isMidScan:
            
            self.statusBar.showMessage("Scan fortgesetzt",10)
            self.microscope.transmitScanImg.connect(self.updateScanCanvas)
            self.startBtn.setEnabled(False)
            self.stopBtn.setEnabled(True)
            self.microscope.resumeScan()
            
            self.updateLog(f"Scan wird fortgesetzt.")
        else:
            # self.centrWidget.initPlotUI()
            self.statusBar.showMessage("Scan gestarted",10)
            self.microscope.transmitScanImg.connect(self.updateScanCanvas)

            self.startBtn.setEnabled(False)
            self.stopBtn.setEnabled(True)
            self.pauseBtn.setEnabled(True)
            self.microscope.startScan(params)
            self.isMidScan = True
            self.updateLog(f"Scan mit {params} gestartet")
                
            if self.tabWidget.currentIndex() == 0:
                self.updateLog("Scan wurde gestartet - bitte in den Scan Tab wechseln")

        


    def pauseHandler(self):
        self.microscope.pauseScan()
        self.startBtn.setEnabled(True)
        self.pauseBtn.setEnabled(False)
        self.stopBtn.setEnabled(True)

    def stopHandler(self):
        self.isMidScan = False
        self.startBtn.setEnabled(True)
        self.pauseBtn.setEnabled(False)
        self.stopBtn.setEnabled(False)
        self.microscope.stopScan()
        self.microscope.transmitScanImg.disconnect(self.updateScanCanvas)




if __name__ == '__main__':

    app = qtw.QApplication(sys.argv)
    # it's required to save a reference to MainWindow.
    # if it goes out of scope, it will be destroyed.
    mw = MainWindow()



    sys.exit(app.exec_())
    
