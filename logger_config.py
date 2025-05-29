"""Logging configuration module for the Email Testing Server application."""

import os
import platform
import logging
from logging.handlers import RotatingFileHandler
import sys


def setup_logging():
    """Configure logging for the application"""
    # Determine log directory based on platform
    if platform.system().lower() == "windows":
        # Windows: Use AppData/Local/EmailTestingServer/logs
        log_dir = os.path.join(
            os.environ.get("LOCALAPPDATA", ""), "EmailTestingServer", "logs"
        )
    else:
        # Linux: Use /var/log/email-testing-server
        log_dir = "/var/log/email-testing-server"

    # Create log directory if it doesn't exist
    try:
        os.makedirs(log_dir, exist_ok=True)
    except PermissionError:
        # Fallback to user's home directory if system directory is not accessible
        log_dir = os.path.join(os.path.expanduser("~"), ".email-testing-server", "logs")
        os.makedirs(log_dir, exist_ok=True)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create formatters
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_formatter = logging.Formatter("%(levelname)s: %(message)s")

    # File handler (rotating log files)
    log_file = os.path.join(log_dir, "email-server.log")
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"  # 5MB
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(file_formatter)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)

    # Add handlers to root logger
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Create specific loggers
    loggers = {
        "email_server": logging.getLogger("email_server"),
        "smtp": logging.getLogger("mail.log"),
        "app": logging.getLogger("__main__"),
    }

    # Configure each logger
    for logger in loggers.values():
        logger.setLevel(logging.INFO)
        # Don't propagate to root logger to avoid duplicate messages
        logger.propagate = False
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return loggers


def get_log_path():
    """Get the path to the log directory"""
    if platform.system().lower() == "windows":
        return os.path.join(
            os.environ.get("LOCALAPPDATA", ""), "EmailTestingServer", "logs"
        )
    else:
        return "/var/log/email-testing-server"
