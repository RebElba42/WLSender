"""
Module for the configuration dialog and config file handling, with language support.
"""

import json
import os
from PyQt5 import QtWidgets
from src.utils import load_translation

CONFIG_FILE = "wlsender_config.json"
LANGUAGES = [("en", "language_en"), ("de", "language_de")]

def load_config():
    """
    Load configuration from file or return default config.
    """
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        if "flrig_host" not in cfg:
            cfg["flrig_host"] = "127.0.0.1"
        if "flrig_port" not in cfg:
            cfg["flrig_port"] = 12345
        if "language" not in cfg:
            cfg["language"] = "en"
        return cfg
    return {
        "wlgate_host": "127.0.0.1",
        "wlgate_port": 2237,
        "qrz_username": "",
        "qrz_password": "",
        "station_callsign": "",
        "flrig_host": "127.0.0.1",
        "flrig_port": 12345,
        "language": "en"
    }

def save_config(cfg):
    """
    Save configuration to file.
    """
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

class ConfigDialog(QtWidgets.QDialog):
    """
    Dialog for editing application configuration, including language selection.
    """
    def __init__(self, parent=None, config=None, translation=None):
        super().__init__(parent)
        self.config = config or load_config()
        self.translation = translation or load_translation(self.config.get("language", "en"))
        self.setWindowTitle(self.translation["config_title"])
        self.setModal(True)
        self.resize(400, 350)
        layout = QtWidgets.QFormLayout(self)

        self.wlgate_host = QtWidgets.QLineEdit(self.config.get("wlgate_host", "127.0.0.1"))
        self.wlgate_port = QtWidgets.QSpinBox()
        self.wlgate_port.setRange(1, 65535)
        self.wlgate_port.setValue(self.config.get("wlgate_port", 2237))
        self.qrz_username = QtWidgets.QLineEdit(self.config.get("qrz_username", ""))
        self.qrz_password = QtWidgets.QLineEdit(self.config.get("qrz_password", ""))
        self.qrz_password.setEchoMode(QtWidgets.QLineEdit.Password)
        self.station_callsign = QtWidgets.QLineEdit(self.config.get("station_callsign", ""))
        self.flrig_host = QtWidgets.QLineEdit(self.config.get("flrig_host", "127.0.0.1"))
        self.flrig_port = QtWidgets.QSpinBox()
        self.flrig_port.setRange(1, 65535)
        self.flrig_port.setValue(self.config.get("flrig_port", 12345))

        # Language selection
        self.language_combo = QtWidgets.QComboBox()
        for code, label_key in LANGUAGES:
            self.language_combo.addItem(self.translation[label_key], code)
        idx = [code for code, _ in LANGUAGES].index(self.config.get("language", "en"))
        self.language_combo.setCurrentIndex(idx)

        layout.addRow(self.translation["wlgate_ip"], self.wlgate_host)
        layout.addRow(self.translation["wlgate_port"], self.wlgate_port)
        layout.addRow(self.translation["qrz_username"], self.qrz_username)
        layout.addRow(self.translation["qrz_password"], self.qrz_password)
        layout.addRow(self.translation["station_callsign"], self.station_callsign)
        layout.addRow(self.translation["flrig_host"], self.flrig_host)
        layout.addRow(self.translation["flrig_port"], self.flrig_port)
        layout.addRow(self.translation["language"], self.language_combo)

        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

        self.setLayout(layout)

    def get_config(self):
        """
        Return the config as a dict.
        """
        return {
            "wlgate_host": self.wlgate_host.text().strip(),
            "wlgate_port": self.wlgate_port.value(),
            "qrz_username": self.qrz_username.text().strip(),
            "qrz_password": self.qrz_password.text(),
            "station_callsign": self.station_callsign.text().strip(),
            "flrig_host": self.flrig_host.text().strip(),
            "flrig_port": self.flrig_port.value(),
            "language": self.language_combo.currentData()
        }