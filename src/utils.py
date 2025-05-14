import json
import os
from datetime import datetime, timezone

def load_translation(lang_code, i18n_path="i18n"):
    """
    Load translation dictionary for given language code.
    """
    file_path = os.path.join(i18n_path, f"{lang_code}.json")
    if not os.path.exists(file_path):
        file_path = os.path.join(i18n_path, "en.json")
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def now_utc_str():
    """
    Return current UTC time as string (HH:MM:SS).
    """
    return datetime.now(timezone.utc).strftime("%H:%M:%S")