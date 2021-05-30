from PySide2 import QtCore as qtc
from PySide2 import QtWidgets as qtw

FILE_TREE_TITLE = "Projektordner"

class FileTreeWidget(qtw.QDockWidget):
    """This class encapsulates a custom File tree Widget

    
    """
    def __init__(self, name=FILE_TREE_TITLE):
        super().__init__(name)

        
        self.setFeatures(
            qtw.QDockWidget.DockWidgetClosable
        )

        # filetree
        self.fileTreeWidget = qtw.QWidget()
        self.fileTreeWidget.setLayout(qtw.QHBoxLayout())
        self.setWidget(self.fileTreeWidget)

        self.fileModel = qtw.QFileSystemModel()
        self.fileModel.setResolveSymlinks(False)
        self.fileModel.setRootPath(qtc.QDir.homePath())
        self.fileModel.setNameFilters(
            ['*.ome.tif', '*.ome.tiff', 'ome.tf2', 'ome.tf8', 'ome.btf'])
        self.treeView = qtw.QTreeView()
        self.treeView.setModel(self.fileModel)
        self.treeView.setIndentation(10)
        self.treeView.setSortingEnabled(True)
        self.treeView.setWindowTitle(name)

        self.fileTreeWidget.layout().addWidget(self.treeView)