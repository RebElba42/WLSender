"""
Logger module for error and event logging.
"""

import logging
from datetime import datetime

LOGFILE = "wlsender.log"

def setup_logger():
    """
    Set up the logger for the application.
    """
    logging.basicConfig(
        filename=LOGFILE,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s"
    )

def log_error(msg):
    """
    Log an error message with timestamp.
    """
    logging.error(msg)

def log_info(msg):
    """
    Log an info message with timestamp.
    """
    logging.info(msg)

def read_log_history():
    """
    Read the log file and return its content.
    """
    if not os.path.exists(LOGFILE):
        return ""
    with open(LOGFILE, "r", encoding="utf-8") as f:
        return f.read()