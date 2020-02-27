from functools import partial
from PyQt5.Qt import QAction, QKeySequence



def _addCommand(owner, shortcut, hint):
    action = QAction(hint, owner)
    action.setShortcuts(list(shortcut))
    return action


def addCommands(owner):
    addCommand = partial(_addCommand, owner)
    actions = [
              addCommand(["F1"],            "left"),
              addCommand(["F2"],            "Rename"),
              addCommand(["F3"],            "View"),
              addCommand(["F4"],            "----"),
              addCommand(["F5"],            "Copy"),
              addCommand(["F6"],            "CLI"),
              addCommand(["F7"],            "MkDir"),
              addCommand(["F8", "Del"],     "Delete"),
              addCommand(["F9", "alt-F4"],  "Quit"),
              addCommand(["F10"],           "right"),
              ]
    return actions
