import json
import sys
import os
from datetime import datetime, timezone

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
    Gibt den Pfad zu einer Resource zurück, egal ob im PyInstaller-Bundle, als EXE oder im Entwicklermodus.
    """
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller-EXE
        return os.path.join(sys._MEIPASS, relative_path)
    # Entwicklermodus: Basis ist das Projektverzeichnis (eine Ebene über src)
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(base, relative_path)

def user_data_path(filename):
    """
    Gibt den Pfad zu einer Nutzerdaten-Datei im data-Verzeichnis neben der EXE (oder im Projektverzeichnis) zurück.
    """
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller-EXE
        base = os.path.dirname(sys.argv[0])
    else:
        # Entwicklermodus: Basis ist das Projektverzeichnis (eine Ebene über src)
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(base, "data", filename)