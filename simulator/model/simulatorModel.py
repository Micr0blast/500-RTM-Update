
from PySide2 import QtCore as qtc
from pathlib import Path


import PIL
import numpy as np
import math
from simple_pid import PID

# https://stackoverflow.com/questions/47339044/pyqt5-timer-in-a-thread

PATH_TO_IMAGES = "simulator/img"

LOWER_CURRENT_BOUND = 0
UPPER_CURRENT_BOUND = 1e-6

PID_ENABLED = False
PID_ENABLE_LIMIT = False
PID_LIMIT_BOTTOM =10e-10
PID_LIMIT_TOP = 10e-5
PID_SAMPLE_TIME = 0.1

SCREW_TARGET = 100


NANO = 1e-9
INITIAL_PK = 2
INITIAL_IK = 0.5
INITIAL_DK = 0
INITIAL_SETPOINT = 20
INITIAL_BIASVOLTAGE = 1.0
MINIMUM_IMG_DATA_VAL = 0
MAXIMUM_IMG_DATA_VAL = 255

class SimulatorModel(qtc.QObject):
    pid: PID
    currentImage: np.ndarray
    imgPaths: list
    tunnelCurrent: float = 0

    lineFinished = qtc.Signal(list)
    scanFinished = qtc.Signal()

    def __init__(self, pathToImages=PATH_TO_IMAGES, lowerCurrentBound=LOWER_CURRENT_BOUND, upperCurrentBound=UPPER_CURRENT_BOUND):
        super().__init__()
        self.imgPaths = self.getImgPaths(Path(pathToImages))
        self.setCurrentImage(0)

        self.lowerCurrentBound = lowerCurrentBound
        self.upperCurrentBound = upperCurrentBound

        self.biasVoltage = INITIAL_BIASVOLTAGE

        self.pid = PID(INITIAL_PK, INITIAL_IK, INITIAL_DK, setpoint=INITIAL_SETPOINT * NANO)
        self.pid.sample_time = PID_SAMPLE_TIME
        if PID_ENABLE_LIMIT:
            self.pid.output_limits = (PID_LIMIT_BOTTOM, PID_LIMIT_TOP )

    def setPidParams(self, ki, kp, setpoint):
        self.pid.Ki = ki
        self.pid.kp = kp
        self.pid.setpoint = setpoint*NANO

    def getTargetCurrent(self):
        return self.pid.setpoint

    def setBiasVoltage(self, voltage):
        self.biasVoltage = voltage

    def getImgPaths(self, path: Path) -> list:
        return [img.resolve() for img in path.iterdir() if not img.is_dir()]

    def updateTunnelCurrent(self, screwVals: tuple):
        a, b, c = screwVals
        a = SCREW_TARGET-a
        b = SCREW_TARGET-b
        c = SCREW_TARGET-c

        retVal = math.pow((math.exp(-(a+b+c))), self.biasVoltage)
        if PID_ENABLED:
            self.tunnelCurrent = retVal
        else:
            self.tunnelCurrent = self.constrainedTunnelCurrent(retVal, self.lowerCurrentBound, self.upperCurrentBound)
            
    def constrainedTunnelCurrent(self, value, lowerBound, upperBound):
        constrainedValue = value
        if value < lowerBound:
            constrainedValue = lowerBound
        elif value > upperBound:
            constrainedValue = upperBound
        
        return constrainedValue

    def getTunnelCurrent(self):
        if PID_ENABLED:
            self.tunnelCurrent /= self.pid(self.tunnelCurrent)
        return self.tunnelCurrent

    def addNoise(self, Y, size):
        return np.add(Y, np.random.randint(0, math.ceil(abs(self.pid.setpoint - self.getTunnelCurrent())), size))

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
                # constrains data points in image to 0 and 
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
        elif breadth:
            breadthToInt = breadth 
        
        return int(breadthToInt)

    # def emitCurrentLine(self, line):
    #     self.lineFinished.emit(line)

    def getScanImage(self, startX: int, startY: int, lengthX: int, lengthY: int, direction: int, maxY: int, breadth: int):
        img = np.zeros(shape=(lengthX, maxY))

        
        if  self.getTunnelCurrent() < self.lowerCurrentBound:
            return img
    
        for i in range(lengthY):
            line = self.getScanLine(
                startX, startY+i, lengthX, direction, breadth)

            img[i] = line
        return img



    
    def getScanLine(self, startX: int, startY: int, length: int, direction: int, breadth=0.1):
        line = None
        currentImage = self.getCurrentImage()

        
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
                # get data from image until the end of of the image
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
        
        line = np.where(line < MINIMUM_IMG_DATA_VAL, MINIMUM_IMG_DATA_VAL, line) # if values below 0 are in the line set them to 0
        line = np.where(line > MAXIMUM_IMG_DATA_VAL, MAXIMUM_IMG_DATA_VAL, line) # if values higher than 255 are in the line set them to 255

        return line

    
if __name__ == "__main__":
   print("This is the simulator model please run from GUI")