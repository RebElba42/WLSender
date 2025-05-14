"""
QRZ.com lookup with error handling and logging.
"""

import requests
from src.logger import log_error, log_info

def lookup_qrz(call, username, password, session_key=None):
    """
    Lookup call data from QRZ.com.
    Returns (data_dict, session_key) or (None, session_key) on error.
    """
    try:
        if not session_key:
            url = f"https://xmldata.qrz.com/xml/current/?username={username};password={password}"
            r = requests.get(url, timeout=10)
            if "<Key>" in r.text:
                session_key = r.text.split("<Key>")[1].split("</Key>")[0]
            else:
                log_error("QRZ.com login failed.")
                return None, None
        url = f"https://xmldata.qrz.com/xml/current/?s={session_key};callsign={call}"
        r = requests.get(url, timeout=10)
        def extract(tag):
            if f"<{tag}>" in r.text:
                return r.text.split(f"<{tag}>")[1].split(f"</{tag}>")[0]
            return ""
        data = {
            "name": (extract("fname") + " " + extract("name")).strip(),
            "qth": extract("addr2"),
            "country": extract("country"),
            "gridsquare": extract("grid"),
        }
        if not any(data.values()):
            log_error(f"QRZ.com: No data TESTLOG found for {call}.")
            return None, session_key
        log_info(f"QRZ.com data for {call} received.")
        return data, session_key
    except Exception as e:
        log_error(f"QRZ.com error: {e}")
        return None, session_key