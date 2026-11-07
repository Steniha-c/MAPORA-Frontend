"""Structured logging configuration with automatic redaction of sensitive data."""

import logging
import re
import sys
from typing import Any, Dict


REDACTED = "[REDACTED]"
SENSITIVE_PATTERNS = [
    re.compile(r'(password["\']?\s*[:=]\s*["\'])([^"\']+)(["\'])', re.IGNORECASE),
    re.compile(r'(token["\']?\s*[:=]\s*["\'])([^"\']+)(["\'])', re.IGNORECASE),
    re.compile(r'(secret["\']?\s*[:=]\s*["\'])([^"\']+)(["\'])', re.IGNORECASE),
    re.compile(r'(authorization["\']?\s*[:=]\s*["\']Bearer\s+)([^"\']+)(["\'])', re.IGNORECASE),
]


class SensitiveDataFilter(logging.Filter):
    """Filter that strips out sensitive keys and values from log messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            msg = record.msg
            for pattern in SENSITIVE_PATTERNS:
                msg = pattern.sub(rf"\g<1>{REDACTED}\g<3>", msg)
            record.msg = msg
        return True


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure system logger with sensitive data redaction."""
    logger = logging.getLogger("mapora")
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        handler.addFilter(SensitiveDataFilter())
        logger.addHandler(handler)

    return logger


logger = setup_logging()
