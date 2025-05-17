from PyQt5 import QtWidgets, QtCore

class FocusAwareLineEdit(QtWidgets.QLineEdit):
    """
    QLineEdit that emits a signal when it receives focus.
    This can be used to stop automatic updates as soon as the user selects the field.
    """
    focused = QtCore.pyqtSignal()

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.focused.emit()