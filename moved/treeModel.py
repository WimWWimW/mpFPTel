#!/usr/bin/env python


from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QTreeView
from PyQt5.Qt import QFont, QAbstractItemModel, QModelIndex,\
    QKeySequence, QShortcut, pyqtSlot, QSortFilterProxyModel, QUrl, QDir
from pyBoardEx import Microterm
from PyQt5 import QtCore
from functools import partial
from fs.osfs import OSFS
import os


class TreeView(QTreeView):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.setSortingEnabled(True)
        self.setDragDropMode(QTreeView.DragDrop)
        self.setSelectionMode(QTreeView.ExtendedSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)

        
    def getSelection(self, asString = False):
        def itemFromIndex(index):
            return index.internalPointer().fileDescriptor.fullName()
        fmt = lambda s:  str(s) if asString else QUrl.fromLocalFile(s) 
        return [fmt(itemFromIndex(i)) for i in self.selectionModel().selectedRows()]


    def showEvent(self, event):
        super().showEvent(event)
        self.sortByColumn(0, Qt.AscendingOrder)
        self.setColumnWidth(0, 240)

        
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and event.source() is not self:
            print("accept")
            event.acceptProposedAction()
        else:
            event.ignore()
            print("accept NOT", self.model())

    def getDropTarget(self, event):
        return "/"
    
    
    def dropEvent(self, event):
        target = self.getDropTarget(event)
        files  = [u.toLocalFile() for u in event.mimeData().urls()]
        source = event.source()
        self.handleDropEvent(source, files, target)
            
            
    def dragMoveEvent(self, event):
        pass

    
    def renameCurrentItem(self, uiFunction):
        selection = self.getSelection(asString = True)
        if len(selection) == 1:
            fileName    = os.path.split(selection[0])[1]
            newName, ok = uiFunction(fileName)
            if ok:
                print(self.getSelection(), newName)
    
    



class FSView(TreeView):

    def getDropTarget(self, event):
        index = self.indexAt(event.pos())
        path  = self.model().filePath(index)
        return super().getDropTarget(event) if path == "" else path


    def expandPath(self, path):
        QDir.setCurrent(path)
        node = self.model().index(QDir.currentPath())
        try:
            while node != QModelIndex():
                self.expand(node);
                node = node.parent()
        except:
            pass
        

    def handleDropEvent(self, source, files, target):
        if source is target is self:
            super.handleDropEvent(self, files, self)
        else:
            source.handleDropEvent(source, files, self)
        
        
    def handleKeypress(self, key):
        pass


class MPView(TreeView):


    def dragEnterEvent(self, event):
        if event.source() == self:
            print("addFiles")
            urls = self.getSelection()
            event.mimeData().setUrls(urls)
            
        else:
            super().dragEnterEvent(event)
        

    def getDropTarget(self, event):
        index = self.indexAt(event.pos())
        item  = index.internalPointer()
        if item is not None:
            item  = item.fileDescriptor
            return item.fullName() if item.isDir else item.path
        else:
            return super().getDropTarget(event)
    
    def handleDropEvent(self, source, files, target):
        if source is target is self:
            super.handleDropEvent(self, files, self)
        elif source is self:
            for f in files:
                self.model().board.copyFileFromBoard(f, target)
        else:
            for f in files:
                self.model().board.copyFileToBoard(f, target)
                self.model().update()
                
                
    def handleKeypress(self, key):
        if key == "F8":
            self.model().deleteFile(self.selectionModel().selectedRows())
                

class TreeItem(object):
    def __init__(self, data, parent=None):
        self.parent         = parent
        self.fileDescriptor = data
        self.children = []

    def appendChild(self, item):
        self.children.append(item)

    def child(self, row):
        return self.children[row]

    def childCount(self):
        return len(self.children)

    def row(self):
        if self.parent:
            return self.parent.children.index(self)
        return 0


    def key(self, column, direction):
        item    = self.fileDescriptor
        prefix  = "A" if (item.isDir == (direction == Qt.AscendingOrder)) else "Z"

        if column == 0:
            return  "%s %s" % (prefix, item.name)
         
        elif column == 1:
            return "%s %7d %s" % (prefix, item.size(), item.name) 
            
        else:
            return "%s %s %s" % (prefix, item.type, item.name) 
        
        
        
class MicroPythonModel(QAbstractItemModel):
    
    def __init__(self, parent = None, speed = 115200, port = -1):
        super().__init__(parent)
        self.board = Microterm()
        self.update()
        
        
    def __del__(self):
        if hasattr(self, "board") and self.board is not None:
            self.board.close()
        
        
    def update(self):
        def addModelData(files, parent):
            for f in files:
                node = TreeItem(f, parent)
                if f.hasChildren():
                    addModelData(f.children, node)
                parent.appendChild(node)
    
        self.rootItem   = TreeItem("\\")
        data            = self.board.getFiles(recurse = True)
        addModelData(data, self.rootItem)
        self.layoutChanged.emit()
        

    def columnCount(self, parent):
        return 3


    def data(self, index, role):
        if not index.isValid():
            return None

        item = index.internalPointer().fileDescriptor
        col  = index.column()  
        
        if role == Qt.DisplayRole:
            if col == 0:
                return item.name
            elif col == 1:
                return ("%6d" % item.size()) if not item.isDir else ""
            elif col == 2:
                return item.type

        elif role == Qt.FontRole:
            if item.isDir:
                font = QFont()
                font.setItalic(True)
                return font
            
        elif role == Qt.TextAlignmentRole:
            if col == 1:
                return Qt.AlignRight
        return QtCore.QVariant()


    def flags(self, index):
        if not index.isValid():
            return Qt.ItemIsDropEnabled

        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled | Qt.ItemIsEditable 


    def headerData(self, section, orientation, role):
        if (role == Qt.DisplayRole) and (orientation == Qt.Horizontal):
            return ("Name Size Type Age".split()[section])
        return QtCore.QVariant()
#         if orientation == Qt.Horizontal and role == Qt.DisplayRole:
#             return self.rootItem.data(section)

        return None


    def index(self, row, column, parent):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()

        childItem = parentItem.child(row)
        if childItem:
            return self.createIndex(row, column, childItem)
        else:
            return QModelIndex()


    def parent(self, index):
        if not index.isValid():
            return QModelIndex()

        item = index.internalPointer()

        if item.parent == self.rootItem:
            return QModelIndex()

        return self.createIndex(item.parent.row(), 0, item.parent)


    def rowCount(self, parent):
        if parent.column() > 0:
            return 0

        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()

        return parentItem.childCount()


    def sort(self, column, order = Qt.AscendingOrder):
        keyFunc = partial(TreeItem.key, column = column, direction = order) # lambda f: f.key(column, order)
        self.rootItem.children = sorted(self.rootItem.children, key=keyFunc, reverse = (order != Qt.AscendingOrder))
        self.layoutChanged.emit()
        

    def dropMimeData(self, *args, **kwargs):
        print(args, kwargs)
    
    
    def deleteFile(self, rows):
        for row in rows:
            fileName = self.data(row, Qt.DisplayRole)
            print("DELETE", fileName)
            self.board.rm(fileName)
        self.update()        
    
    
class PyFileSystemModel(QAbstractItemModel):
    
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.fs         = OSFS("r:/")
        self.setPwd("/")


    def setPwd(self, path):
        self.pwd        = path
        self.files      = self.fs.listdir(path)


    def columnCount(self, parent):
        return 3


    def data(self, index, role):
        if not index.isValid():
            return None

        item = index.internalPointer().fileDescriptor
        col  = index.column()  
        
        if role == Qt.DisplayRole:
            if col == 0:
                return item.name
            elif col == 1:
                return ("%6d" % item.size()) if not item.isDir else ""
            elif col == 2:
                return item.type

        elif role == Qt.FontRole:
            if item.isDir:
                font = QFont()
                font.setItalic(True)
                return font
            
        elif role == Qt.TextAlignmentRole:
            if col == 1:
                return Qt.AlignRight
        return QtCore.QVariant()


    def flags(self, index):
        if not index.isValid():
            return Qt.ItemIsDropEnabled

        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled | Qt.ItemIsEditable 


    def headerData(self, section, orientation, role):
        if (role == Qt.DisplayRole) and (orientation == Qt.Horizontal):
            return ("Name Size Type Age".split()[section])
        return QtCore.QVariant()
#         if orientation == Qt.Horizontal and role == Qt.DisplayRole:
#             return self.rootItem.data(section)

        return None


    def index(self, row, column, parent):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
 
        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()
 
        childItem = parentItem.child(row)
        if childItem:
            return self.createIndex(row, column, childItem)
        else:
            return QModelIndex()


#     def parent(self, index):
#         if not index.isValid():
#             return QModelIndex()
# 
#         item = index.internalPointer()
# 
#         if item.parent == self.rootItem:
#             return QModelIndex()
# 
#         return self.createIndex(item.parent.row(), 0, item.parent)


    def rowCount(self, parent):
        if parent.column() > 0:
            return 0

        return len(self.files)





    def sort(self, column, order = Qt.AscendingOrder):
#         keyFunc = partial(TreeItem.key, column = column, direction = order) # lambda f: f.key(column, order)
#         self.rootItem.children = sorted(self.rootItem.children, key=keyFunc, reverse = (order != Qt.AscendingOrder))
        self.layoutChanged.emit()
        

    def dropMimeData(self, *args, **kwargs):
        print(args, kwargs)
    
    def fileName (self, index):
        return index.internalPointer().fileDescriptor.name

    def filePath (self, index):
        return index.internalPointer().fileDescriptor.path

    def isDir (self, index):
        return index.internalPointer().fileDescriptor.isDir

    def isReadOnly (self):
        return False

    def mkdir (self, parent, name):
        self.board.mkdir(name)


    def remove (self, index):
        self.board.rm(self.fileName(index))

    def rmdir (self, index):
        self.board.rmdir(self.fileName(index))
#     def rootDirectory ()
# 
#     def rootPath ()

    def setReadOnly (self, enable):
        pass

    def size (self, index):
        return index.internalPointer().fileDescriptor.size()
    
    def type (self, index):
        return index.internalPointer().fileDescriptor.type

        
             
if __name__ == '__main__':

    import sys
    @pyqtSlot()
    def on_open(sender):
        print("Opening!", sender.key().toString())

    app  = QApplication(sys.argv)
    repl = Microterm("Com9:", 115200)
    
    try:
        model = MicroPythonModel(repl.getFiles(recurse = True))
        sorter = QSortFilterProxyModel(model)
        view = QTreeView()
        view.setModel(model)
        view.setSortingEnabled(True)
        view.setWindowTitle("Simple Tree Model")
        view.shortcut = QShortcut(QKeySequence("Ctrl+O"), view)
        view.shortcut.activated.connect(partial(on_open, view.shortcut))
        view.show()
        app.exec_()
    finally:
        repl.stop()



