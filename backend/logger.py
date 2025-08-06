# utils/logger.py
import os
import logging
from logging.handlers import TimedRotatingFileHandler

LOG_DIR = "storage/logs"
LOG_FILE = "app.log"

# Create logs directory if not exists
os.makedirs(LOG_DIR, exist_ok=True)

# Full path to log file
log_path = os.path.join(LOG_DIR, LOG_FILE)

# Configure the logger
logger = logging.getLogger("my_app_logger")
logger.setLevel(logging.INFO)

# Prevent duplicate handlers in case of multiple imports
if not logger.handlers:
    handler = TimedRotatingFileHandler(
        log_path, when="midnight", interval=1, backupCount=7, encoding='utf-8'
    )
    handler.suffix = "%Y-%m-%d"
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
