"""
Logger module for error and event logging.
"""

import os
import logging
import logging.handlers

LOGFILE = "wlsender.log"

logging.lastResort = None  # Disable emergency handler

# Completely silence root logger with real NullHandler
class NullHandler(logging.Handler):
    """
    Null handler to silence the root logger.
    """
    def emit(self, record):
        pass

root_logger = logging.getLogger()
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)
root_logger.addHandler(NullHandler())
root_logger.setLevel(logging.CRITICAL + 1)
root_logger.propagate = False

# Also silence noisy libraries
for noisy_logger in ["requests", "urllib3", "chardet", "charset_normalizer"]:
    l = logging.getLogger(noisy_logger)
    l.handlers.clear()
    l.addHandler(NullHandler())
    l.setLevel(logging.CRITICAL + 1)
    l.propagate = False

# Custom logger for the application
logger = logging.getLogger("wlsender")
logger.setLevel(logging.INFO)
logger.propagate = False  # WICHTIG!

# Rotating file handler for errors and info (max 25MB, 3 Backups)
file_handler = logging.handlers.RotatingFileHandler(
    LOGFILE, maxBytes=10 * 1024 * 1024, backupCount=10, encoding="utf-8"
)
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# DO NOT attach StreamHandler for console!

def log_error(msg):
    """
    Log an error message with timestamp.
    """
    logger.error(msg)

def log_info(msg):
    """
    Log an info message with timestamp.
    """
    logger.info(msg)

def read_log_history():
    """
    Read the log file and return its content.
    """
    if not os.path.exists(LOGFILE):
        return ""
    with open(LOGFILE, "r", encoding="utf-8") as f:
        return f.read()