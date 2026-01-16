import logging
import sys
from enum import Enum


class LogColors(str, Enum):
    """ANSI color codes for terminal output formatting."""
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors and emojis to log messages."""
    
    FORMATS = {
        logging.DEBUG: (
            f"🔍 {LogColors.OKCYAN.value}DEBUG{LogColors.ENDC.value}\t%(message)s"
        ),
        logging.INFO: (
            f"ℹ️  {LogColors.OKBLUE.value}INFO{LogColors.ENDC.value}\t%(message)s"
        ),
        logging.WARNING: (
            f"⚠️  {LogColors.WARNING.value}WARNING{LogColors.ENDC.value}\t"
            "%(message)s"
        ),
        logging.ERROR: (
            f"❌ {LogColors.FAIL.value}ERROR{LogColors.ENDC.value}\t%(message)s"
        ),
        logging.CRITICAL: (
            f"🔥 {LogColors.FAIL.value}{LogColors.BOLD.value}CRITICAL"
            f"{LogColors.ENDC.value}\t%(message)s"
        ),
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno, "%(message)s")
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


class StdoutFilter(logging.Filter):
    """Filter that only allows INFO and DEBUG levels to stdout."""
    def filter(self, record):
        return record.levelno <= logging.INFO


def setup_logging(level=logging.INFO):
    """
    Configure the logging system with proper handlers and formatters.
    
    Args:
        level: The minimum logging level (default: INFO)
    """
    logger = logging.getLogger()
    logger.setLevel(level)
    
    # Remove any existing handlers
    logger.handlers.clear()
    
    # Create stdout handler for INFO and DEBUG messages
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.DEBUG)
    stdout_handler.addFilter(StdoutFilter())
    stdout_handler.setFormatter(ColoredFormatter())
    
    # Create stderr handler for WARNING, ERROR, and CRITICAL messages
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.setFormatter(ColoredFormatter())
    
    # Add both handlers to the logger
    logger.addHandler(stdout_handler)
    logger.addHandler(stderr_handler)


def log_debug(message: str):
    """Log a debug message with 🔍 emoji."""
    logging.debug(message)


def log_info(message: str):
    """Log an informational message with ℹ️ emoji."""
    logging.info(message)


def log_success(message: str):
    """Log a success message with ✅ emoji."""
    logging.info(
        f"✅ {LogColors.OKGREEN.value}SUCCESS{LogColors.ENDC.value}\t{message}"
    )


def log_warning(message: str):
    """Log a warning message with ⚠️ emoji."""
    logging.warning(message)


def log_error(message: str):
    """Log an error message with ❌ emoji."""
    logging.error(message)


def log_critical(message: str):
    """Log a critical error message with 🔥 emoji."""
    logging.critical(message)
