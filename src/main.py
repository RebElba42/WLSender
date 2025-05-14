import sys
import os
from PyQt5 import QtWidgets, QtGui
import qdarkstyle
from src.config_dialog import load_config
from src.utils import load_translation
from src.qso_form import QSOForm
from src.utils import resource_path

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