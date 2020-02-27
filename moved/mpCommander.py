import sys
from PyQt5.QtWidgets import QWidget, QApplication, QHBoxLayout, QInputDialog,\
    QLineEdit
from PyQt5.Qt import QVBoxLayout, QFrame, QFileSystemModel, QLabel, QToolButton
from commands import addCommands
from functools import partial
from treeModel import MicroPythonModel, FSView, MPView, TreeView

class Window(QWidget):
    def __init__(self, *args, **kwargs):
        QWidget.__init__(self, *args, **kwargs)
        self._build()


    def _onAction(self, sender):
        key = sender.shortcut().toString()
        print("Action:", sender.shortcut().toString())
        if key == "F1":
            self.mp.view.setFocus()
        elif key == "F2":
            self.renameCurrentItem()
        elif key == "F10":
            self.fs.view.setFocus()
        elif key == "F9":
            QApplication.quit()
        else:
            fw = self.focusedTree()
            if fw is not None:
                fw.handleKeypress(key)
    
     
    def focusedTree(self):   
        fw = self.focusWidget()
        return fw if isinstance(fw, TreeView) else None
            
            
    def execFocused(self, method, parameters = []):
        fw = self.focusWidget()
        if isinstance(fw, TreeView):
            return method(fw, *parameters)
        return None
    
    
    def renameCurrentItem(self):
        fn = lambda s: QInputDialog().getText(self, "rename", "new name:", QLineEdit.Normal, s)
        self.execFocused(TreeView.renameCurrentItem, [fn])        
    
    
    def pathChanged(self, current, previous):
        self.fs.label.setText(self.fsModel.filePath(current))

        
    def _microPythonTreeview(self):
        view = MPView()
        view.setModel(MicroPythonModel());
        return view

         
    def _fileSystemModel(self):
        self.fsModel = QFileSystemModel()
        self.fsModel.setRootPath('')
        self.fsModel.setReadOnly(False)
        return self.fsModel
    

    def _fileSystemTreeview(self):
        view = FSView()
        view.setModel(self._fileSystemModel());
        view.expandPath("d:/fablab/microPython")
        return view
    

    def _buildPane(self, view, caption = "LABEL"):
        result = QFrame()
        layout = QVBoxLayout(result)
        result.label    = QLabel(caption)
        layout.addWidget(result.label)
        result.view     = view
        layout.addWidget(result.view)
        return result
    
    
    def _build(self):
        layout  = QVBoxLayout(self); self.setLayout(layout)
        panes   = QFrame(); layout.addWidget(panes); 
        cli     = QFrame(); layout.addWidget(cli)
        buttons = QFrame(); layout.addWidget(buttons)
        
        layout  = QHBoxLayout(panes)
        left    = self._buildPane(self._microPythonTreeview(), "microController");         layout.addWidget(left)
        right   = self._buildPane(self._fileSystemTreeview(), "file system");   layout.addWidget(right)

        self.mp = left
        self.fs = right
        self.fs.view.selectionModel().currentChanged.connect(self.pathChanged)


        layout  = QHBoxLayout(buttons)
        
        actions = addCommands(self)
        for action in actions:
            action.triggered.connect(partial(self._onAction, action))
            l = QLabel(action.shortcut().toString()+":", buttons); layout.addWidget(l)
            b = QToolButton(self); b.setDefaultAction(action); layout.addWidget(b); b.setMinimumSize(70, 0)
            
        self.resize(500, 800)

    
        
if __name__ == '__main__':
    
    app = QApplication(sys.argv)
    win = Window()
    win.show()
    app.exec_()        
