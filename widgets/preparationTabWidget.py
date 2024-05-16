import matplotlib
matplotlib.use("Qt5Agg")


from PySide6 import QtCore as qtc
from PySide6 import QtGui as qtg
from PySide6 import QtWidgets as qtw

from .canvas import Canvas
from .resources import *
import numpy as np

class PreparationTabWidget(qtw.QWidget):
    logMessage = qtc.Signal(str)

    def __init__(self):
        super().__init__()

        
        self.redLEDPxm = qtg.QPixmap(
            ":/icons/led_red.png").scaled(16, 16, qtc.Qt.KeepAspectRatio)
        self.greenLEDPxm = qtg.QPixmap(
            ":/icons/led_green.png").scaled(16, 16, qtc.Qt.KeepAspectRatio)

        nData = 100

        self.xData = np.arange(nData)
        self.yData = np.zeros(nData)

        self.mainLayout = qtw.QVBoxLayout()
        self.setLayout(self.mainLayout)
        self.layout().setSpacing(36)
        self.prepCanvas = Canvas(self)

        self.prepAxe = self.prepCanvas.fig.add_subplot(111)
        self.prepAxe.plot(self.xData, self.yData, linewidth=4,
                          color="r", label="Tunnelstrom")
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


        self.prepCondDescrLbl = qtw.QLabel(
            "Nähern Sie die Spitze am Mikroskop an das eingelegte Material an, bis ein Tunnelstrom fließt")
        self.prepCondDescrLbl.setStyleSheet("margin-top:60px")

        self.prepCondDescrLbl.setFont(
            qtg.QFont("SansSerif", 14, qtg.QFont.Bold))


        self.mainLayout.addWidget(self.prepLbl)
        self.mainLayout.addLayout(self.rtmSelectRow)
        self.mainLayout.addWidget(self.prepCondDescrLbl)
        self.mainLayout.addWidget(self.prepCanvas)

        # self.rtmConnectBtn.clicked.connect(self.connectWithRTM)

    def updatePlot(self, tunnelCurrent, targetCurrent):
        if tunnelCurrent > 10e-8:
            tunnelCurrent = 10e-8
        self.yData = np.append(self.yData[1:], tunnelCurrent)
        self.prepAxe.cla()
        self.prepAxe.plot(self.xData, self.yData, lw="4",
                            color='g', label="Tunnelstrom")
        self.prepAxe.axhline(y=targetCurrent, linestyle="--", label="Zieltunnelstrom")
        self.prepAxe.legend()

        self.prepAxe.set_ylim(0, 1e-7)

        self.prepAxe.set_xlabel("t")
        self.prepAxe.set_ylabel("Tunnelstrom")
        self.prepCanvas.canvas.draw()


    def updateLED(self, isConnected):
        if isConnected:
            self.rtmStateLED.setPixmap(self.greenLEDPxm)
        else:
            self.rtmStateLED.setPixmap(self.redLEDPxm)
