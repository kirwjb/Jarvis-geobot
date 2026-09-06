import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


# ANSI colors for the lightweight development console helpers.
GREEN = "\033[95m"
RED = "\033[31m"
PURPLE = "\033[35m"
RESET = "\033[0m"


def log(msg: str) -> None:
    print(f"{GREEN}[LOG] {msg}{RESET}", flush=True)


def error(msg: str) -> None:
    print(f"{RED}[ERROR] {msg}{RESET}", file=sys.stderr, flush=True)


def info(msg: str) -> None:
    print(f"{PURPLE}[INFO] {msg}{RESET}", flush=True)


BASE_DIR = Path(__file__).resolve().parents[2]
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
MAX_LOG_SIZE = 5 * 1024 * 1024
BACKUP_COUNT = 5


def _configure_file_logger(name: str, filename: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        handler = RotatingFileHandler(
            LOG_DIR / filename,
            mode="a",
            maxBytes=MAX_LOG_SIZE,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
        handler.setLevel(logging.INFO)
        logger.addHandler(handler)

    return logger


logger = _configure_file_logger("JARVIS_GEO", "bot.log")
admin_logger = _configure_file_logger("JARVIS_ADMIN", "admin.log")
