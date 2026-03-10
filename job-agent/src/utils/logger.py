"""Structured logging setup for the job agent.

Provides file + console logging with rotating log files,
run-specific log directories, and screenshot path helpers.
"""

import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

# Resolve project root (job-agent/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"
RUN_LOGS_DIR = LOGS_DIR / "run_logs"
SCREENSHOTS_DIR = LOGS_DIR / "screenshots"

# Ensure directories exist at import time
LOGS_DIR.mkdir(parents=True, exist_ok=True)
RUN_LOGS_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Get a configured logger instance.

    Args:
        name: Logger name, typically __name__ of the calling module.
        level: Logging level. Defaults to INFO.

    Returns:
        Configured logger with console and file handlers.
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(level)
    logger.propagate = False

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Rotating file handler – main log
    main_log_path = LOGS_DIR / "job_agent.log"
    file_handler = RotatingFileHandler(
        main_log_path,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def create_run_log(source: str) -> Path:
    """Create a log file for a specific run.

    Args:
        source: The source being processed (e.g., 'linkedin', 'naukrigulf').

    Returns:
        Path to the run-specific log file.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_log_path = RUN_LOGS_DIR / f"run_{source}_{timestamp}.log"

    handler = logging.FileHandler(run_log_path, encoding="utf-8")
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))

    run_logger = logging.getLogger(f"run.{source}.{timestamp}")
    run_logger.setLevel(logging.DEBUG)
    run_logger.addHandler(handler)
    run_logger.propagate = False

    run_logger.info("Run log created for source=%s at %s", source, timestamp)
    return run_log_path


def get_screenshot_path(
    stage: str, job_id: Optional[str] = None, source: Optional[str] = None
) -> Path:
    """Generate a unique screenshot file path.

    Args:
        stage: Screenshot stage name (e.g., 'apply_button', 'confirmation', 'error').
        job_id: Optional job identifier for traceability.
        source: Optional source name.

    Returns:
        Path object for the screenshot file.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    parts = [stage]
    if source:
        parts.insert(0, source)
    if job_id:
        parts.append(str(job_id))
    parts.append(timestamp)

    filename = "_".join(parts) + ".png"
    return SCREENSHOTS_DIR / filename


def log_action(
    logger: logging.Logger,
    action: str,
    status: str,
    details: Optional[str] = None,
    job_url: Optional[str] = None,
    error: Optional[str] = None,
) -> dict:
    """Log a structured action entry.

    Args:
        logger: Logger instance.
        action: Action name (e.g., 'collect', 'score', 'apply').
        status: Outcome status (e.g., 'success', 'failure', 'skipped').
        details: Optional detail string.
        job_url: Optional job URL for traceability.
        error: Optional error message.

    Returns:
        Dict of the logged entry for further use.
    """
    entry = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "status": status,
        "details": details,
        "job_url": job_url,
        "error": error,
    }

    msg_parts = [f"action={action}", f"status={status}"]
    if details:
        msg_parts.append(f"details={details}")
    if job_url:
        msg_parts.append(f"url={job_url}")
    if error:
        msg_parts.append(f"error={error}")

    message = " | ".join(msg_parts)

    if status == "failure":
        logger.error(message)
    elif status == "skipped":
        logger.warning(message)
    else:
        logger.info(message)

    return entry
