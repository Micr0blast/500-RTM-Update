
from PySide2 import QtWidgets as qtw
from PySide2 import QtGui as qtg
from PySide2 import QtCore as qtc
import numpy as np

from .resources import *

DIAL_TOOLTIP = "Schraube drehen, um die Scan-Spitze an die Probe anzunähern"
SLIDER_TOOLTIP = "Slider bewegen, um die Scan-Spitze an die Probe anzunähern"


class ValueRadioButton(qtw.QRadioButton):
    def __init__(self):
        super(ValueRadioButton, self).__init__()
        self.value = None

    def setValue(self, val):
        self.value = val

    def getValue(self):
        return self.value


class ValuePushButton(qtw.QPushButton):
    def __init__(self):
        super(ValuePushButton, self).__init__()
        self.value = None

    def setValue(self, val):
        self.value = val

    def getValue(self):
        return self.value


class QHLine(qtw.QFrame):
    def __init__(self):
        super(QHLine, self).__init__()
        self.setFrameShape(qtw.QFrame.HLine)
        self.setFrameShadow(qtw.QFrame.Sunken)


class SimulatorView(qtw.QWidget):

    valuesChanged = qtc.Signal(list)
    materialChosen = qtc.Signal(int)

    def __init__(self, screwMin: float = 0, screwMax: float = 100, stepSize: float = 0.1, default: float = 50, notchesVisible: bool = True):
        super().__init__()
        self.centralLayout = qtw.QVBoxLayout()
        self.dialLayout = qtw.QHBoxLayout()
        
        self.simulatorPxm = qtg.QPixmap(":/images/rtm_top.png").scaled(300,500,qtc.Qt.KeepAspectRatio, transformMode = qtc.Qt.SmoothTransformation)
        self.simulatorPxmLbl = qtw.QLabel("Simulator image")
        self.simulatorPxmLbl.setPixmap(self.simulatorPxm)

        self.materialChoiceContainer = qtw.QWidget()
        self.materialChoice = qtw.QHBoxLayout()
        self.materialChoiceContainer.setLayout(self.materialChoice)

        self.matButtonOne = ValuePushButton()
        self.matButtonOne.setText("Graphit")
        self.matButtonOne.setValue(0)

        self.matButtonTwo = ValuePushButton()
        self.matButtonTwo.setText("Platin")
        self.matButtonTwo.setValue(1)
        self.matButtonThree = ValuePushButton()
        self.matButtonThree.setText("Rhodium")
        self.matButtonThree.setValue(2)

        self.graphiteLabel = qtw.QLabel("Graphit")
        self.platinumLabel = qtw.QLabel("Platin")
        self.rhodiumLabel = qtw.QLabel("Rhodium")

        self.graphiteRadio = ValueRadioButton()
        self.graphiteRadio.setValue(0)
        self.graphiteRadio.setChecked(True)
        self.graphiteRadio.toggled.connect(self.changeMaterial)
        self.platinumRadio = ValueRadioButton()
        self.platinumRadio.toggled.connect(self.changeMaterial)
        self.platinumRadio.setValue(1)
        self.rhodiumRadio = ValueRadioButton()
        self.rhodiumRadio.setValue(2)
        
        self.rhodiumRadio.toggled.connect(self.changeMaterial)

        self.materialChoice.addWidget(self.graphiteLabel)
        self.materialChoice.addWidget(self.graphiteRadio)
        self.materialChoice.addWidget(self.platinumLabel)
        self.materialChoice.addWidget(self.platinumRadio)
        self.materialChoice.addWidget(self.rhodiumLabel)
        self.materialChoice.addWidget(self.rhodiumRadio)

        self.setLayout(self.centralLayout)
        self.materialChoiceLbl = qtw.QLabel("Material auswählen", self)
        self.materialChoiceLbl.setStyleSheet("QLabel {font-weight: bold;}")
        self.layout().addWidget(self.materialChoiceLbl)

        self.centralLayout.addWidget(self.materialChoiceContainer)

        self.rowLayout = qtw.QHBoxLayout()
        self.simulatorImgLbl = qtw.QLabel("Rastertunnelmikroskop (Draufsicht)")
        self.simulatorImgLbl.setStyleSheet("QLabel {font-weight: bold;}")
        self.toggleHelpBtn = qtw.QPushButton("Hilfe")
        self.toggleHelpBtn.setCheckable(True)

        self.simulatorExplanationLbl = qtw.QLabel("Das Bild zeigt den Prototypen in der Draufsicht.\nUm im Vorbereitungstab des Hauptfensters einen\nTunnelstrom zu sehen müssen alle 3 Schrauben in \ndie richtige Position gebracht werden")
        self.simulatorExplanationLbl.setHidden(True)
        self.toggleHelpBtn.clicked.connect(self.showHelp)
        self.centralLayout.addWidget(QHLine())
        self.rowLayout.addWidget(self.simulatorImgLbl)
        self.rowLayout.addWidget(self.toggleHelpBtn)
        self.centralLayout.addLayout(self.rowLayout)
        self.centralLayout.addWidget(self.simulatorExplanationLbl)
        self.centralLayout.addWidget(self.simulatorPxmLbl)
        self.centralLayout.addLayout(self.dialLayout)

        self.setupSlidersAndDials(
            screwMin, screwMax, stepSize, default, notchesVisible)

        self.screwDialOne.valueChanged.connect(self.submitValuesChanged)
        self.screwDialTwo.valueChanged.connect(self.submitValuesChanged)
        self.screwDialThree.valueChanged.connect(self.submitValuesChanged)


        self.setStyleSheet("""
            QPushButton {
                font-size: 14px;
            }
            QLabel {
                font-size: 12px;
            }
            QDial {
                font-size: 12px;
            }
        """)
        # End main UI codeF
        self.show()

    def showHelp(self):
        self.simulatorExplanationLbl.setHidden(self.toggleHelpBtn.isChecked())

    def changeMaterial(self, b):
        graphiteElement = self.materialChoiceContainer.children()[2]
        platinumElement = self.materialChoiceContainer.children()[4]
        rhodiumElement = self.materialChoiceContainer.children()[6]
        self.resetDialsAndSliders()
        if graphiteElement.isChecked():
            self.materialChosen.emit(graphiteElement.getValue())
            
        if platinumElement.isChecked():
            self.materialChosen.emit(platinumElement.getValue())
        
        if rhodiumElement.isChecked():
            self.materialChosen.emit(rhodiumElement.getValue())
    

    def resetDialsAndSliders(self):
        self.screwDialOne.setValue(0)
        self.screwDialTwo.setValue(0)
        self.screwDialThree.setValue(0)
        # self.screwSliderOne.setValue(0)
        # self.screwSliderTwo.setValue(0)
        # self.screwSliderThree.setValue(0)

    def setupSlidersAndDials(self, min: float, max: float, step: float, default: float, notches: bool):
        self.screwDialOne = self.createDial(
            min, max, step, default, notches)
        self.screwDialTwo = self.createDial(
            min, max, step, default, notches)
        self.screwDialThree = self.createDial(
            min, max, step, default, notches)

        self.screwSliderOne = self.createSlider(
            min, max, step, default)
        self.screwSliderTwo = self.createSlider(
            min, max, step, default)
        self.screwSliderThree = self.createSlider(
            min, max, step, default)

        self.screwSliderOne.valueChanged.connect(self.screwDialOne.setValue)

        self.screwSliderTwo.valueChanged.connect(self.screwDialTwo.setValue)
        self.screwSliderThree.valueChanged.connect(
            self.screwDialThree.setValue)

        self.screwDialOne.valueChanged.connect(self.screwSliderOne.setValue)
        self.screwDialTwo.valueChanged.connect(self.screwSliderTwo.setValue)
        self.screwDialThree.valueChanged.connect(
            self.screwSliderThree.setValue)

        self.subLayoutOne = qtw.QVBoxLayout()
        self.subLayoutTwo = qtw.QVBoxLayout()
        self.subLayoutThree = qtw.QVBoxLayout()

        self.subLayoutOne.addWidget(self.screwDialOne)
        self.subLayoutTwo.addWidget(self.screwDialTwo)
        self.subLayoutThree.addWidget(self.screwDialThree)

        self.subLayoutOne.addWidget(qtw.QLabel("Schraube 1"))
        self.subLayoutTwo.addWidget(qtw.QLabel("Schraube 2"))
        self.subLayoutThree.addWidget(qtw.QLabel("Schraube 3"))

        self.dialLayout.addLayout(self.subLayoutOne)
        self.dialLayout.addLayout(self.subLayoutTwo)
        self.dialLayout.addLayout(self.subLayoutThree)

        self.centralLayout.addWidget(self.screwSliderOne)
        self.centralLayout.addWidget(self.screwSliderTwo)
        self.centralLayout.addWidget(self.screwSliderThree)

    def createSlider(self, min: float, max: float, step: float, default: float) -> qtw.QSlider:
        """This function will return a QtSlider with the passed parameters set

        Args:
            min (float): min value of slider
            max (float): max value of
            step (float): step size for slider
            default (float): default start value for slider

        Returns:
            qtw.QSlider: A QtSlider object
        """

        slider = qtw.QSlider(qtc.Qt.Horizontal)
        slider.setToolTip(SLIDER_TOOLTIP)
        slider.setMinimum(min)
        slider.setMaximum(max)
        slider.setSingleStep(step)
        slider.setValue(default)

        return slider

    def createDial(self, min: float, max: float, step: float, default: float, notches: bool) -> qtw.QDial:
        """This function will return a QtDial with the passed parameters set

        Args:
            min (float): min value of dial
            max (float): max value of dial
            step (float): step size for dial
            default (float): default start value for dial

        Returns:
            qtw.QDial: A QDial object
        """

        dial = qtw.QDial()
        dial.setMinimum(min)
        dial.setToolTip(DIAL_TOOLTIP)
        dial.setMaximum(max)
        dial.setSingleStep(step)
        dial.setValue(default)
        dial.setNotchesVisible(notches)

        return dial

    def submitValuesChanged(self):
        values = tuple([self.screwDialOne.value(), self.screwDialTwo.value(),
                        self.screwDialThree.value()])
        self.valuesChanged.emit(values)



if __name__ == '__main__':
    # Do nothing
    print("Nothing to do")
