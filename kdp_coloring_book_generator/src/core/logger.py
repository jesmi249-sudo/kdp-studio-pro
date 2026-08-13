"""
Logging module for KDP Coloring Book Generator.
Provides rotating file + console logging for all application modules.
"""

import logging
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler

# Determine log directory
_BASE_DIR = Path(__file__).resolve().parent.parent.parent
_LOG_DIR = _BASE_DIR / "data"
_LOG_DIR.mkdir(exist_ok=True)
_LOG_FILE = _LOG_DIR / "app.log"

# Module-level logger cache
_loggers = {}


def get_logger(name: str = "kdp_generator") -> logging.Logger:
    """
    Get or create a logger with the given name.
    
    Loggers write to both console (INFO+) and a rotating file (DEBUG+).
    Log file: data/app.log (max 5MB, 3 backups).
    
    Args:
        name: Logger name (typically module name).
        
    Returns:
        Configured logging.Logger instance.
    """
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Prevent duplicate handlers if logger already configured
    if logger.handlers:
        _loggers[name] = logger
        return logger

    # Console handler (INFO and above)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    console_handler.setFormatter(console_fmt)

    # File handler (DEBUG and above, rotating)
    try:
        file_handler = RotatingFileHandler(
            str(_LOG_FILE),
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_fmt = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_fmt)
        logger.addHandler(file_handler)
    except (OSError, PermissionError):
        # If file logging fails, continue with console only
        pass

    logger.addHandler(console_handler)
    _loggers[name] = logger
    return logger
