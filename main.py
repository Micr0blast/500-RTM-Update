import sys

from PySide2 import QtWidgets as qtw
from PySide2 import QtGui as qtg
from PySide2 import QtCore as qtc
import tifffile

from widgets.resources import *

from widgets.scanTabWidget import ScanTabWidget
from widgets.fileTreeWidget import FileTreeWidget
from widgets.preparationTabWidget import PreparationTabWidget
from simulator.simulator import SimulatorWindow

ENABLE_FILE_TREE = False
ENABLE_SPLASH_SCREEN = False

PID_PARAMETER_LABEL = "Regel-Parameter"
SCAN_PARAMETER_LABEL = "Scan-Parameter"

WINDOW_TITLE = "STM Scan-UI"

INITIAL_WINDOW_WIDTH = 1200
INITIAL_WINDOW_HEIGHT = 800

# For Parameters ( FieldLabel:string, DefaultValue:float/int, Unit:string, isDecimal:bool MinimumValue:float/int, MaximumValue: float/int )
BIAS_VOLTAGE_VALUES = ("Bias-Spannung", 0.1, "V", True, 0.1, 1.0)
PK_VALUES = ("kP:", 2, "", True, 0, 10000)
IK_VALUES = ("kI:", 0.5, "", True, 0, 10000)
SETPOINT_VALUES = ("Zielstrom:", 20, "nA", True, 10, 100)
X_START_VALUES = ("Startkoordinate X:", 250, "", False, 0, 4000)
Y_START_VALUES = ("Startkoordinate Y:", 250, "", False, 0, 4000)
RESOLUTION_VALUES = ("Auflösung:", 250, "pixel x pixel", False, "", "")


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

        This widget is be our main window.
        We'll define all the UI components in here.
        """
        super().__init__()


        self.setWindowTitle(WINDOW_TITLE)
        self.resize(INITIAL_WINDOW_WIDTH, INITIAL_WINDOW_HEIGHT)

        # Top menu bar
        self.setupTopBarMenus()
        

        # Statusbar
        self.setupStatusBar()

        # Top Tool bar
        # self.setupToolBar()

        # Log
        self.setupLogDock()


        # Tabs
        self.setupTabs()

        # Parameters dock
        self.setupParametersDock()

        # enable beta splash screen
        if ENABLE_SPLASH_SCREEN:
            self.showSplashScreen()

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

        if ENABLE_FILE_TREE:
            self.showFileDirScreen()
            self.setupFileTree()

    def setupTopBarMenus(self):
        """Sets up the top bar menus
        """
        self.menuBar = self.menuBar()
        self.fileMenu = self.menuBar.addMenu("Datei")
        self.helpMenu = self.menuBar.addMenu("Hilfe")

        self.closeAction = qtw.QAction(
            self.style().standardIcon(qtw.QStyle.SP_DockWidgetCloseButton),
            "Beenden",
            self,
            triggered=self.close
        )
        
        self.fileMenu.addAction(self.closeAction)

        self.saveAction = qtw.QAction(
            self.style().standardIcon(qtw.QStyle.SP_DriveCDIcon),
            "Scan Speichern...",
            self,
            triggered=self.saveScan
        )
        if ENABLE_FILE_TREE:
            self.openAction = qtw.QAction(
                self.style().standardIcon(qtw.QStyle.SP_DirOpenIcon),
                "Dateispeicherort auswählen",
                self,
                triggered=self.showChooseSaveDirDialog
            )
            

        # self.fileMenu.addAction(self.openAction)
        # self.fileMenu.addAction(self.saveAction)

    def setupStatusBar(self):
        """Sets up the status bar
        """
        self.statusBar = qtw.QStatusBar(parent=self)
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Welcome to the 500€ RTM")
        self.scannerStatusLabel = qtw.QLabel("Standby")
        self.statusBar.addPermanentWidget(self.scannerStatusLabel)

    def setupParametersDock(self):
        """Setup up the experiment dock widget"""

        self.experimentDock = qtw.QDockWidget("Scan-Parameter")
        self.experimentDock.setTitleBarWidget(qtw.QWidget(self))
        self.experimentDock.setFeatures(qtw.QDockWidget.NoDockWidgetFeatures)
        self.addDockWidget(qtc.Qt.RightDockWidgetArea, self.experimentDock)

        self.expDockWidgetContainer = qtw.QWidget()
        self.expDockWidgetContainer.setLayout(qtw.QVBoxLayout())
        self.experimentDock.setWidget(self.expDockWidgetContainer)

        # z-Height Controller Parameters Widgets and layout
        self.piGroupBox = qtw.QGroupBox(f"{PID_PARAMETER_LABEL}", self)
        self.piGroupBox.setStyleSheet("QGroupBox {font-weight: bold;}")
        self.piGroupBox.resize(60, 180)
        self.piGroupBox.setLayout(qtw.QVBoxLayout())
        self.piGroupBox.layout().setAlignment(qtc.Qt.AlignCenter)

        self.biasVoltageRow = self.createParameterRow(
            BIAS_VOLTAGE_VALUES[0], f"{BIAS_VOLTAGE_VALUES[1]}", f"{BIAS_VOLTAGE_VALUES[4]} - {BIAS_VOLTAGE_VALUES[5]} {BIAS_VOLTAGE_VALUES[2]}", double=BIAS_VOLTAGE_VALUES[3], top=BIAS_VOLTAGE_VALUES[4], bottom=BIAS_VOLTAGE_VALUES[5])
        self.pGainRow = self.createParameterRow(
            PK_VALUES[0], f"{PK_VALUES[1]}", f"{PK_VALUES[4]} - {PK_VALUES[5]} {PK_VALUES[2]}", double=PK_VALUES[3], top=PK_VALUES[4], bottom=PK_VALUES[5])
        self.iGainRow = self.createParameterRow(
            IK_VALUES[0], f"{IK_VALUES[1]}", f"{IK_VALUES[4]} - {IK_VALUES[5]} {IK_VALUES[2]}", double=IK_VALUES[3], top=IK_VALUES[4], bottom=IK_VALUES[5])
        self.zHeightRow = self.createParameterRow(
            SETPOINT_VALUES[0], f"{SETPOINT_VALUES[1]}", f"{SETPOINT_VALUES[4]} - {SETPOINT_VALUES[5]} {SETPOINT_VALUES[2]}", double=SETPOINT_VALUES[3], top=SETPOINT_VALUES[4], bottom=SETPOINT_VALUES[5])
        self.updateControlParametersBtn = qtw.QPushButton(
            f"{PID_PARAMETER_LABEL} aktualisieren", clicked=self.updateParametersHandler)

        self.piGroupBox.layout().addWidget(self.biasVoltageRow)  # TODO : ADD TO SIMULATOR
        self.piGroupBox.layout().addWidget(self.pGainRow)
        self.piGroupBox.layout().addWidget(self.iGainRow)
        self.piGroupBox.layout().addWidget(self.zHeightRow)

        self.piGroupBox.layout().addWidget(self.updateControlParametersBtn)

        # Scan Parameters Widgets and Layout
        self.scanGroupBox = qtw.QGroupBox(f"{SCAN_PARAMETER_LABEL}", self)
        self.scanGroupBox.setStyleSheet("QGroupBox {font-weight: bold;}")
        self.scanGroupBox.setLayout(qtw.QVBoxLayout())

        self.xStartRow = self.createParameterRow(
            X_START_VALUES[0], f"{X_START_VALUES[1]}", f"{X_START_VALUES[4]} - {X_START_VALUES[5]} {X_START_VALUES[2]}", double=X_START_VALUES[3], top=X_START_VALUES[4], bottom=X_START_VALUES[5])

        self.yStartRow = self.createParameterRow(
            Y_START_VALUES[0], f"{Y_START_VALUES[1]}", f"{Y_START_VALUES[4]} - {Y_START_VALUES[5]} {Y_START_VALUES[2]}", double=Y_START_VALUES[3], top=Y_START_VALUES[4], bottom=Y_START_VALUES[5])

            
        # refactored to resolution parameters
        self.xEndRow = self.createParameterRow(
            RESOLUTION_VALUES[0], f"{RESOLUTION_VALUES[1]}", f"{RESOLUTION_VALUES[4]} - {RESOLUTION_VALUES[5]} {RESOLUTION_VALUES[2]}", double=RESOLUTION_VALUES[3], top=RESOLUTION_VALUES[4], bottom=RESOLUTION_VALUES[5])
        # self.yEndRow = self.createParameterRow("Höhe", "500", "Pixel")
        self.scanGroupBox.layout().addWidget(self.xStartRow)
        self.scanGroupBox.layout().addWidget(self.yStartRow)
        self.scanGroupBox.layout().addWidget(self.xEndRow)
        # self.scanGroupBox.layout().addWidget(self.yEndRow)

        # Direction Radio Group
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

        # TODO: add later
        # self.multiplierRow = self.createParameterRow(
        #     "DAC-Multiplikator", "1", "1 - 100")
        # self.scanGroupBox.layout().addWidget(self.multiplierRow)

        self.scanVelocityRow = self.createParameterRow(
            "Scan-Breite", "0.2", "0.1 - 20.0 mV/px", True, 0.1, 20
        )
        self.scanGroupBox.layout().addWidget(self.scanVelocityRow)

        self.controlGroupBox = qtw.QGroupBox("Scan-Controls", self)
        self.controlGroupBox.setStyleSheet("QGroupBox {font-weight: bold;}")
        self.startBtn = qtw.QPushButton("Start", clicked=self.startHandler)
        self.startBtn.setShortcut("Return")
        self.pauseBtn = qtw.QPushButton("Pause", clicked=self.pauseHandler)
        self.stopBtn = qtw.QPushButton("Stop", clicked=self.stopHandler)
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
        """Extracts all scan related parameters and returns them as a tuple

        Returns:
            tuple of parameters
        """
        pGain = float(self.pGainRow.children()[2].text())
        iGain = float(self.iGainRow.children()[2].text())
        zHeight = float(self.zHeightRow.children()[2].text())
        xStart = int(self.xStartRow.children()[2].text())
        yStart = int(self.yStartRow.children()[2].text())
        xEnd = int(self.xEndRow.children()[2].text())
        biasV = float(self.biasVoltageRow.children()[2].text())
        # yEnd = int(self.yEndRow.children()[2].text())
        yEnd = xEnd

        direction = 0 if self.directionRow.children()[2].isChecked() else 1
        # multiplier = int(self.multiplierRow.children()[2].text())
        velocity = float(self.scanVelocityRow.children()[2].text())

        return (pGain, iGain, zHeight, xStart, yStart, xEnd, yEnd, direction, velocity, biasV)

    def updateParametersHandler(self):
        """This function handles the PID-parameter update functionality
        """
        biasV = float(self.biasVoltageRow.children()[2].text())
        pGain = float(self.pGainRow.children()[2].text())
        iGain = float(self.iGainRow.children()[2].text())
        zHeight = float(self.zHeightRow.children()[2].text())

        if self.microscope != None:
            self.microscope.updateControlParameters(
                (biasV, pGain, iGain, zHeight))
            self.updateLog(f"{PID_PARAMETER_LABEL} aktualisiert.")
        else:
            self.updateLog(
                f"RTM auswählen um {PID_PARAMETER_LABEL} zu aktualisieren.")

    def setupLogDock(self):
        """ This function sets up the Log Dock and its styleing
        """
        self.spiDock = qtw.QDockWidget("Log")

        self.spiDock.setFeatures(qtw.QDockWidget.NoDockWidgetFeatures)
        self.addDockWidget(qtc.Qt.BottomDockWidgetArea, self.spiDock)

        self.logWidget = qtw.QWidget()
        self.logWidget.setLayout(qtw.QVBoxLayout())
        self.spiDock.setWidget(self.logWidget)

        self.logTextArea = qtw.QTextEdit("", readOnly=True) 
        self.logTextArea.setUndoRedoEnabled(False) # This disables the widgets history function
        self.logTextArea.setStyleSheet("""
                QTextEdit { 
                    background: black;
                    color: white;
                } 
            """)
        self.logWidget.layout().addWidget(self.logTextArea)

    def updateLog(self, update):
        """Slot function for updates to the logs

        Args:
            update ([type]): [description]
        """
        self.logTextArea.append(update)

    def createParameterRow(self, label: str, placeholder: str, unitLabel: str, double=False, bottom=0.1, top=5.0) -> qtw.QWidget:
        """Helper function which creates a parameter row with the given arguments

        Args:
            label (str): Label of field
            placeholder (str): Default value
            unitLabel (str): Unit of the Field
            double (bool, optional): Decimal or Integer Value. Defaults to False.
            bottom (float, optional): Lower end of allowed range. Defaults to 0.1.
            top (float, optional): Upper end of allowed range. Defaults to 5.0.

        """
        container = qtw.QWidget(self)
        container.setLayout(qtw.QHBoxLayout())
        container.layout().setAlignment(qtc.Qt.AlignCenter)
        rowLbl = qtw.QLabel(text=label, parent=self)
        rowEdit = qtw.QLineEdit(placeholder)
        rowEdit.setMaximumWidth(30)
        if double:
            validator = qtg.QDoubleValidator(bottom, top, 2, parent=self)
            validator.setNotation(qtg.QDoubleValidator.StandardNotation)
        else:
            validator = qtg.QIntValidator(self)
        rowEdit.setValidator(validator)
        unitLbl = qtw.QLabel(text=unitLabel, parent=self)

        container.layout().addStretch()
        container.layout().addWidget(rowLbl)
        container.layout().addWidget(rowEdit)
        container.layout().addWidget(unitLbl)

        return container

    def saveScan(self):
        """This function encases the save action functionality. 
        For use in QAction
        """

        if self.imgData != None:
            fileName = qtw.QFileDialog.getSaveFileName(
                self,
                "Datei speichern unter...",
                "",
                "TIFF Files (*.tif  *.ome.tif)")
            tifffile.imsave(
                fileName[0], data=self.imgData, photometric="minisblack")
            self.updateLog(f"Scan wurder unter {fileName} gespeichert")
        else:
            self.updateLog("Es ist noch kein Scan vorhanden")

    def showChooseSaveDirDialog(self):
        """This functoin encases the save direction functionality for the file tree widget.
        For use in QAction
        """
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
        """ This functions sets up all the tabs and connections
        """
        self.tabWidget = qtw.QTabWidget()

        self.setCentralWidget(self.tabWidget)

        self.tabWidget.setTabPosition(qtw.QTabWidget.North)

        self.prepContainer = qtw.QWidget()
        self.prepContainer.setLayout(qtw.QHBoxLayout())
        self.scanContainer = qtw.QWidget()
        
        self.prepTabWidget = PreparationTabWidget()
        self.prepTabWidget.rtmConnectBtn.clicked.connect(self.connectWithRTM)
        self.prepContainer.layout().addWidget(self.prepTabWidget)

        self.scanContainer.setLayout(qtw.QHBoxLayout())

        self.scanTabWidget = ScanTabWidget()
        self.scanContainer.layout().addWidget(self.scanTabWidget)
        self.scanTabWidget.logMessage.connect(self.updateLog)

        self.tabWidget.addTab(self.prepContainer, "Vorbereitung")

        self.tabWidget.addTab(self.scanContainer, "Scans")

    def updateScanCanvas(self, img):
        """Slot function to handle image updates to the Scan canvas

        Args:
            img: img data in 3d array
        """
        self.imgData = img
        self.scanTabWidget.updateImage(self.imgData)
        self.statusBar.showMessage("Scan aktualisiert", 1000)

    def connectWithRTM(self):
        """This function handles connecting to the chosen RTM

        """
        selected = self.prepTabWidget.rtmComboBox.currentIndex()
        if selected == 1: # if simulator is chosen
            self.updateLog("Verbindung wird aufgebaut...")
            qtc.QTimer.singleShot(2000, lambda: self.showSimulator())
        else:
            # TODO Add connection to hardware prototype code here
            # init rtm connection
            pass


    def showSimulator(self):
        """This function handles showing the simulator and connecting related signals
        """
        if self.microscope is None:
            self.microscope = SimulatorWindow()
            self.microscope.transmitTunnelCurrent.connect(self.prepTabWidget.updatePlot)
            self.microscope.logMessage.connect(self.updateLog)
            self.prepTabWidget.updateLED(True)
            self.microscope.scanFinished.connect(self.stopHandler)
            self.updateLog("Verbindung hergestellt!")
            self.microscope.show()
        else:
            self.microscope.show()

    def startHandler(self):
        """This function handles stop and resume button functionality
        """

        params = self.getExperimentParameters()

        if self.microscope is None:
            qtw.QMessageBox.warning(self,
                                    "Mikroskop Verbinden!",
                                    "Es muss eine Verbindung zu einem Rastertunnelmikroskop bestehen um einen Scan zu starten!")
        elif self.isMidScan:

            self.statusBar.showMessage("Scan fortgesetzt", 10)
            self.microscope.transmitScanImg.connect(self.updateScanCanvas)
            self.startBtn.setEnabled(False)
            self.stopBtn.setEnabled(True)
            self.microscope.resumeScan()

            self.updateLog(f"Scan wird fortgesetzt.")
        else:
            self.statusBar.showMessage("Scan gestarted", 10)
            self.microscope.transmitScanImg.connect(self.updateScanCanvas)

            self.startBtn.setEnabled(False)
            self.stopBtn.setEnabled(True)
            self.pauseBtn.setEnabled(True)
            self.microscope.startScan(params)
            self.isMidScan = True
            self.updateLog(f"Scan mit {params} gestartet")

            if self.tabWidget.currentIndex() == 0:
                self.updateLog(
                    "Scan wurde gestartet - bitte in den Scan Tab wechseln")

    def pauseHandler(self):
        """This function handles pause button functionality
        """
        self.microscope.pauseScan()
        self.startBtn.setEnabled(True)
        self.pauseBtn.setEnabled(False)
        self.microscope.transmitScanImg.disconnect(self.updateScanCanvas)
        self.stopBtn.setEnabled(True)

    def stopHandler(self):
        """This function handles stop button functionality
        """
        self.isMidScan = False
        self.startBtn.setEnabled(True)
        self.pauseBtn.setEnabled(False)
        self.stopBtn.setEnabled(False)
        self.microscope.stopScan()
        self.microscope.transmitScanImg.disconnect(self.updateScanCanvas)

###  functions below are used in current iteration

    def setupToolBar(self):
        """ DEPRECATED """

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

    def showFileDirScreen(self):
        """Sets up and displays the file dir select screen.
        """
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
        """Sets up and displays the beta screen. This is disabled as it was a constant source of consusion
        """
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
        """This function creates the File tree widget
        """
        self.fileTreeDock = FileTreeWidget()
        self.addDockWidget(qtc.Qt.LeftDockWidgetArea, self.fileTreeDock)

        


if __name__ == '__main__':

    app = qtw.QApplication(sys.argv)
    # it's required to save a reference to MainWindow.
    # if it goes out of scope, it will be destroyed.
    mw = MainWindow()

    sys.exit(app.exec_())
