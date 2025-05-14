import sys
import os
from PyQt5 import QtWidgets, QtGui
import qdarkstyle
from src.config_dialog import load_config
from src.utils import load_translation
from src.qso_form import QSOForm

def resource_path(relative_path):
    """
    Get absolute path to resource, works for dev and for PyInstaller.
    """
    base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(base_path, relative_path)

def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    splash_pix = QtGui.QPixmap(resource_path("icons/wlgate.png"))
    splash = QtWidgets.QSplashScreen(splash_pix)
    splash.show()
    app.processEvents()

    config = load_config()
    translation = load_translation(config.get("language", "en"))
    window = QSOForm(config, translation)
    splash.finish(window)
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()