import logging
from logging.handlers import RotatingFileHandler
import os

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_DIR = os.getenv("LOG_DIR", ".")
LOG_FILE = os.path.join(LOG_DIR, "bot.log")

os.makedirs(LOG_DIR, exist_ok=True)

_logger = logging.getLogger("shoesbot")
if not _logger.handlers:
    _logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    fmt = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    fh = RotatingFileHandler(LOG_FILE, maxBytes=2_000_000, backupCount=3)
    fh.setFormatter(fmt)
    _logger.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    _logger.addHandler(ch)

logger = _logger
