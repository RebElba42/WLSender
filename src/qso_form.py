"""
Main QSO form window with statusbar, splashscreen, debug field, and error handling.
"""

from PyQt5 import QtWidgets, QtCore, QtGui
from src.logger import log_error, log_info, read_log_history
from src.utils import now_utc_str

class QSOForm(QtWidgets.QMainWindow):
    """
    Main window for QSO entry and sending.
    """
    def __init__(self, config, translation):
        super().__init__()
        self.config = config
        self.translation = translation
        self.status_history = []
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(self.translation["app_title"])
        # ... weitere UI-Elemente ...
        self.statusbar = QtWidgets.QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.messageChanged.connect(self.on_status_message_changed)
        self.statusbar.mousePressEvent = self.show_status_history

        # Debug-Feld (optional sichtbar)
        self.debug_field = QtWidgets.QTextEdit()
        self.debug_field.setVisible(self.config.get("show_debug", False))
        # ... Layout hinzufügen ...

    def on_status_message_changed(self, msg):
        timestamp = now_utc_str()
        entry = f"{timestamp} {msg}"
        self.status_history.append(entry)
        log_info(msg)

    def show_status_history(self, event):
        """
        Show statusbar history in a dialog and allow copying to clipboard.
        """
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle(self.translation.get("status_history", "Status History"))
        layout = QtWidgets.QVBoxLayout(dlg)
        text = QtWidgets.QTextEdit("\n".join(self.status_history))
        text.setReadOnly(True)
        layout.addWidget(text)
        btn_copy = QtWidgets.QPushButton(self.translation.get("copy_to_clipboard", "Copy to clipboard"))
        btn_copy.clicked.connect(lambda: QtWidgets.QApplication.clipboard().setText(text.toPlainText()))
        layout.addWidget(btn_copy)
        dlg.exec_()