from __future__ import annotations

import os
import structlog
import logging
from typing import Any, Dict



def get_log_file() -> str:
    return os.environ.get("RAPTOR_LOG_FILE", os.path.join(os.getcwd(), "logs", "log_post.txt"))


def _mask(value: str) -> str:
    if value is None:
        return value
    if len(value) <= 4:
        return "***"  # too short, mask all
    return value[:2] + "***" + value[-2:]


def mask_value(value: str) -> str:
    return _mask(value)


def configure_logging() -> None:
    # Ensure directory exists
    log_file = get_log_file()
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter("%(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    # Avoid adding duplicate handlers for same file
    if not any(isinstance(h, logging.FileHandler) and getattr(h, 'baseFilename', None) == file_handler.baseFilename for h in root.handlers):
        root.addHandler(file_handler)

    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(**kwargs: Any):
    logger = structlog.get_logger()
    if kwargs:
        logger = logger.bind(**kwargs)
    return logger


def mask_sensitive(record: Dict[str, Any]) -> Dict[str, Any]:
    # Mask some fields
    for key in ("customer_id", "request_id", "appointment_id"):
        if key in record:
            record[key] = _mask(str(record[key]))
    return record
