import sys

from PySide2 import QtWidgets as qtw
from PySide2 import QtGui as qtg
from PySide2 import QtCore as qtc
from pathlib import Path
# TODO CHANGE IMAGE PATHS TO RESOURCES BUT WATCH OUT FOR CONVERSION OF DATA

import PIL
import numpy as np
import math
from simple_pid import PID

# https://stackoverflow.com/questions/47339044/pyqt5-timer-in-a-thread


class SimulatorModel(qtc.QObject):
    pid: PID
    currentImage: np.ndarray
    imgPaths: list
    tunnelCurrent: float = 0
    biasVoltage = 1.0

    lineFinished = qtc.Signal(list)
    scanFinished = qtc.Signal()

    def __init__(self, pathToImages=r"C:\Users\stpl\src\qtb\ScanUi\simulator\img"):
        super().__init__()
        self.imgPaths = self.getImgPaths(Path(pathToImages))
        self.setCurrentImage(0)
        self.pid = PID(2, .5, 0, setpoint=20e-9)
        self.pid.sample_time = 0.1 # time that passed to have pid give another output
        # self.pid.output_limits = (10e-10, 10e-5)

    def setPidParams(self, ki, kp, setpoint):
        self.pid.Ki = ki*1e-10
        self.pid.kp = kp*1e-10
        self.pid.setpoint = setpoint*1e-9

    def getTargetCurrent(self):
        # print(self.pid.setpoint)
        return self.pid.setpoint

    def setBiasVoltage(self, voltage):
        self.biasVoltage = voltage

    def getImgPaths(self, path: Path) -> list:
        return [img.resolve() for img in path.iterdir() if not img.is_dir()]

    def getBaseOscillation(self, xStart, xEnd, steps):

        return np.linspace(xStart,xEnd, steps), np.sin(np.linspace(xStart,xEnd, steps))

    def updateTunnelCurrent(self, screwVals: tuple):
        a, b, c = screwVals
        a = 100-a
        b = 100-b
        c = 100-c

        retVal = math.pow((math.exp(-(a+b+c))), self.biasVoltage)
        if retVal < 1e-10:
            self.tunnelCurrent = 0
        elif retVal > 1000e-8:
            self.tunnelCurrent = 1000e-8
        else:
            self.tunnelCurrent = retVal

    def getTunnelCurrent(self):
        # self.tunnelCurrent /= self.pid(self.tunnelCurrent)
        return self.tunnelCurrent

    def addNoise(self, Y, size):
        return np.add(Y, np.random.randint(0, (math.floor(
            abs(self.pid.setpoint*1e9 - self.getTunnelCurrent()*1e9))), size))

    def setCurrentImage(self, idx):
        if idx < len(self.imgPaths):

            self.currentImage = self.loadImgData(self.imgPaths[idx])
        else:
            print("IMG idx out of range")

    def getCurrentImage(self):
        return self.currentImage

    def loadImgData(self, path: str) -> np.ndarray:
        try:
            with PIL.Image.open(path) as IMGFile:
                rgb = IMGFile.point(lambda i: i*(1./256)).convert('L')
                return np.asarray(rgb)
        except Exception as e:
            print(e)

    def projectBreadthToInt(self, breadth):
        breadthToInt = 0
        if breadth < 0.1:
            breadthToInt = breadth * 100
        elif breadth < 1:
            breadthToInt = breadth * 10
        elif breadth < 3:
            breadthToInt = breadth 
        else:
            breadthToInt = 1
        
        return int(breadthToInt)

    # def emitCurrentLine(self, line):
    #     self.lineFinished.emit(line)

    def getScanImage(self, startX: int, startY: int, lengthX: int, lengthY: int, direction: int, maxY: int, breadth: int):
        img = np.zeros(shape=(lengthX, maxY))

        

        # will currently return non if img idx is out of range
        # in actual it should return a wall of black as an index out of range is equivalent
        # to no tunnel current ie v=0 => black value

        # If current is too low
        if  self.getTunnelCurrent() < 1e-9:
            return img
        
        # TESTING MEMORY LEAK PROBLEM, GENERATE NOISE ONCE - DOES NOT WORK
        # noise = np.random.randint(0, (math.floor(
        #     abs(self.pid.setpoint - self.getTunnelCurrent()*1e8))), length)
        for i in range(lengthY):
            line = self.getScanLine(
                startX, startY+i, lengthX, direction, breadth)

            img[i] = line
            # line = None
        # print(img)
        # if lengthX == lengthY:
            # self.scanFinished.emit()
        return img

    # construct black image with correct measurements
    # update line by line after each update call until image is filled
    # return everytime until reached


    
    def getScanLine(self, startX: int, startY: int, length: int, direction: int, breadth=0.1):
        line = None
        currentImage = self.getCurrentImage()

        # imageWidth = len(currentImage) - 1
        # imageHeight = len(currentImage[0]) -1
        # setup noise
        

        # length = number of points
        # breadth determines distance of points. Simulator images are 4096 x 4096
        breadthMultiplier = self.projectBreadthToInt(breadth)
        adjustedLength = length * breadthMultiplier
        endX = startX + adjustedLength

        # if Y is out of image bounds
        if startY < 0 or startY > len(currentImage[0]):
            return np.zeros(length)
        
        if direction == 1:  # right direction
            # if end is out of index of the image
            if endX > len(currentImage[startX:, 0]):
                # get data from image until the end
                line = currentImage[startX::breadthMultiplier,startY]
                # fill rest of line with black
                line = np.append(line, np.zeros(length - len(line)))
            else:
                line = currentImage[startX:endX:breadthMultiplier, startY]
        if direction == 0:  # left direction
            if startX - adjustedLength < 0:
                line = currentImage[:startX:breadthMultiplier, startY]
                line = np.append(np.zeros(length-len(line)), line)
            else:
                line = currentImage[startX-adjustedLength:startX:breadthMultiplier, startY]

        line = self.addNoise(line, length)
        line = np.where(line < 0, 0, line)
        line = np.where(line > 255, 255, line)

        # self.emitCurrentLine(line)

        return line

    
if __name__ == "__main__":
    simMod = SimulatorModel(sys.argv[1])
    start = -np.pi
    end = np.pi
    steps = 201
    # X, Y = simMod.getBaseOscillation(start, end, steps)
    # Y = simMod.addNoise(Y, np.random.normal(0,0.1,steps))
    # simMod.drawOscillation(X,Y)

    strPath = "../img"
    path = Path(strPath).resolve()
    paths = simMod.getImgPaths(path)
    print(paths)
    print(paths[0])
    simMod.setCurrentImage(0)
    # paths = simMod.getImgPaths(path)
    # imData = simMod.loadImgData(paths[0])
    # print(imData)
    # line = simMod.getScanLine(startX= 100, startY=5, length=1000, direction=1)
    # plt.plot(line)
    # scanIMG = simMod.getScanImage(
    #     startX=0, startY=0, lengthX=1000, lengthY=1000, direction=1)
    # plt.imshow(scanIMG, cmap="gray")
    # plt.imshow(imData, cmap="gray")

    # plt.show()

    input()
