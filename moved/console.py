#include "console.h"
from PyQt5.Qt import QPlainTextEdit, QPalette, Qt

#include <QScrollBar>
class Console(QPlainTextEdit):

    def __init__(self, parent):
        super().__init__(parent)

        self.document().setMaximumBlockCount(100)
        p = QPalette()
        p.setColor(QPalette.Base, Qt.black)
        p.setColor(QPalette.Text, Qt.green)
        self.setPalette(p)


    def putData(self, data):
        self.insertPlainText(data)
        bar = self.verticalScrollBar()
        bar.setValue(bar.maximum())


    def setLocalEchoEnabled(self, flag):
        self.m_localEchoEnabled = flag


    def keyPressEvent(self, e):

        if (e.key() not in [Qt.Key_Backspace,
                        Qt.Key_Left,    Qt.Key_Right,
                        Qt.Key_Up,      Qt.Key_Down]):
            if (self.m_localEchoEnabled):
                super().keyPressEvent(e)
#             emit getData(e.text().toLocal8Bit())
    


    def mousePressEvent(self, e):
        self.setFocus()


    def mouseDoubleClickEvent(self, e):
        pass


    def contextMenuEvent(self, e):
        pass
