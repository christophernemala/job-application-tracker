"""Scheduler — runs the pipeline daily at a configurable time.

Usage (blocking loop):
    python -m pipeline.scheduler.runner

Or import and embed in a larger process:
    from pipeline.scheduler.runner import start_scheduler
    start_scheduler()
"""
from __future__ import annotations
import signal
import sys
import time

try:
    import schedule  # type: ignore
    _HAS_SCHEDULE = True
except ImportError:
    _HAS_SCHEDULE = False

from pipeline.config import SCHEDULE_HOUR, SCHEDULE_MINUTE
from pipeline.main import run_pipeline
from pipeline.utils.logger import get_logger

log = get_logger("pipeline.scheduler")


def _job():
    log.info("Scheduler triggered — starting pipeline run.")
    try:
        summary = run_pipeline(auto_submit=False)
        log.info("Scheduler run complete: %s", summary)
    except Exception as exc:  # pylint: disable=broad-except
        log.error("Scheduler run failed: %s", exc, exc_info=True)


def start_scheduler() -> None:
    if not _HAS_SCHEDULE:
        log.error(
            "'schedule' package not installed. Run: pip install schedule"
        )
        sys.exit(1)

    run_time = f"{SCHEDULE_HOUR:02d}:{SCHEDULE_MINUTE:02d}"
    schedule.every().day.at(run_time).do(_job)
    log.info("Scheduler started — will run daily at %s UTC.", run_time)

    # Graceful shutdown on SIGTERM / SIGINT
    def _shutdown(signum, frame):  # type: ignore
        log.info("Scheduler shutting down.")
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    start_scheduler()
