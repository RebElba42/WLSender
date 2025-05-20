import json
import sys
import os
from datetime import datetime, timezone
from PyQt5.QtCore import QTimer
from PyQt5 import QtWidgets

def load_translation(lang_code, i18n_path="i18n"):
    """
    Load translation dictionary for given language code.
    """
    file_path = resource_path(os.path.join(i18n_path, f"{lang_code}.json"))
    if not os.path.exists(file_path):
        file_path = resource_path(os.path.join(i18n_path, "en.json"))
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)
    
def now_utc_str():
    """
    Return current UTC time as string (HH:MM:SS).
    """
    return datetime.now(timezone.utc).strftime("%H:%M:%S")

def resource_path(relative_path):
    """
   Returns the path to a resource, regardless of whether running in a PyInstaller bundle, as an EXE, or in development mode.
    """
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller EXE
        return os.path.join(sys._MEIPASS, relative_path)
     # Development mode: base is the project directory (one level above src)
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(base, relative_path)

def user_data_path(filename):
    """
    Returns the path to a user data file in the data directory next to the EXE (or in the project directory in development mode).
    """
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller-EXE
        base = os.path.dirname(sys.argv[0])
    else:
        # Development mode: base is the project directory (one level above src)
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(base, "data", filename)

class AutoCloseInfoBox(QtWidgets.QMessageBox):
    def __init__(self, parent=None, title="", message="", timeout=3000):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setText(message)
        self.setIcon(QtWidgets.QMessageBox.Information)
        self.setStandardButtons(QtWidgets.QMessageBox.Ok)
        self.setModal(True)
        QTimer.singleShot(timeout, self.accept)  # Close after timeout ms