"""
Worker for FLRig communication with error handling.
"""

from PyQt5 import QtCore
from src.logger import log_error, log_info

class FLRigWorker(QtCore.QThread):
    """
    Worker thread for polling FLRig data.
    Emits signals for new data or errors.
    """
    data_received = QtCore.pyqtSignal(dict)
    error_occurred = QtCore.pyqtSignal(str)

    def __init__(self, host, port):
        super().__init__()
        self.host = host
        self.port = port
        self.running = True

    def run(self):
        while self.running:
            try:
                # ... Kommunikation mit FLRig ...
                # Beispiel: daten = poll_flrig(self.host, self.port)
                # self.data_received.emit(daten)
                pass
            except Exception as e:
                msg = f"FLRig error: {e}"
                log_error(msg)
                self.error_occurred.emit(msg)
            self.msleep(1000)

    def stop(self):
        self.running = False