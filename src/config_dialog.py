"""
Module for the configuration dialog and config file handling, with language support.
"""

import json
import os
from PyQt5 import QtWidgets
from src.utils import load_translation
from src.utils import resource_path, user_data_path
from cryptography.fernet import Fernet

KEY_FILE = user_data_path("wlsender_key")
CONFIG_FILE = "wlsender_config.json"
LANGUAGES = [("en", "language_en"), ("de", "language_de")]

def get_crypto_key():
    if not os.path.exists(KEY_FILE):
        key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as f:
            f.write(key)
    else:
        with open(KEY_FILE, "rb") as f:
            key = f.read()
    return key

def encrypt_password(password):
    key = get_crypto_key()
    f = Fernet(key)
    return f.encrypt(password.encode("utf-8")).decode("utf-8")

def decrypt_password(token):
    key = get_crypto_key()
    f = Fernet(key)
    try:
        return f.decrypt(token.encode("utf-8")).decode("utf-8")
    except Exception:
        return ""
    

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
        # Passwort entschlüsseln, falls vorhanden
        if cfg.get("qrz_password"):
            try:
                cfg["qrz_password"] = decrypt_password(cfg["qrz_password"])
            except Exception:
                cfg["qrz_password"] = ""
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
    Dialog for editing application configuration, including language selection and debug field.
    """
    def __init__(self, parent=None, config=None, translation=None):
        super().__init__(parent)
        self.config = config or load_config()
        self.translation = translation or load_translation(self.config.get("language", "en"))
        self.setWindowTitle(self.translation["config_title"])
        self.setFixedSize(420, 360)
        font = self.font()
        font.setPointSize(font.pointSize() + 2)  # Increase font size
        self.setFont(font)
        self.setModal(True)
        self.resize(420, 360)
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

        # Set font for all widgets
        for widget in [self.wlgate_host, self.qrz_username, self.qrz_password,
                       self.station_callsign, self.flrig_host]:
            widget.setMinimumHeight(32)
            widget.setFont(font)
        self.wlgate_port.setFont(font)
        self.flrig_port.setFont(font)

        
        self.debug_checkbox = QtWidgets.QCheckBox(self.translation.get("show_debug", "Show FLRig debug field"))
        self.debug_checkbox.setChecked(self.config.get("show_debug", False))
        self.debug_checkbox.setFont(font)

        # Language selection
        self.language_combo = QtWidgets.QComboBox()
        for code, label_key in LANGUAGES:
            self.language_combo.addItem(self.translation[label_key], code)
        idx = [code for code, _ in LANGUAGES].index(self.config.get("language", "en"))
        self.language_combo.setCurrentIndex(idx)
        self.language_combo.setFont(font)

        layout.addRow(self.translation["wlgate_ip"], self.wlgate_host)
        layout.addRow(self.translation["wlgate_port"], self.wlgate_port)
        layout.addRow(self.translation["qrz_username"], self.qrz_username)
        layout.addRow(self.translation["qrz_password"], self.qrz_password)
        layout.addRow(self.translation["station_callsign"], self.station_callsign)
        layout.addRow(self.translation["flrig_host"], self.flrig_host)
        layout.addRow(self.translation["flrig_port"], self.flrig_port)
        layout.addRow(self.translation.get("show_debug", "Show FLRig debug field"), self.debug_checkbox)
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
            "qrz_password": encrypt_password(self.qrz_password.text()),
            "station_callsign": self.station_callsign.text().strip(),
            "flrig_host": self.flrig_host.text().strip(),
            "flrig_port": self.flrig_port.value(),
            "show_debug": self.debug_checkbox.isChecked(),
            "language": self.language_combo.currentData()
        }