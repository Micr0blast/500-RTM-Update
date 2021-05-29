import matplotlib
matplotlib.use("Qt5Agg")
from PySide2 import QtWidgets as qtw

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import numpy as np



class Canvas(qtw.QWidget):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        super().__init__(parent)
        self.fig = Figure(figsize=(width, height), dpi=dpi)

        self.canvas = FigureCanvasQTAgg(self.fig)

        self.layout = qtw.QVBoxLayout(self)
        self.layout.addWidget(self.canvas)
        
