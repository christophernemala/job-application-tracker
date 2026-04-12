"""Daemon runner for continuous day-long job application automation."""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

from job_agent.auto_apply import AutoApplyRunner
from job_agent.database import init_database, log_event
from job_agent.human_scheduler import DailySchedule, RateLimits

logger = logging.getLogger(__name__)

# Graceful shutdown flag
_shutdown_requested = False


def _signal_handler(signum, frame):
    global _shutdown_requested
    logger.info("Shutdown signal received, finishing current task...")
    _shutdown_requested = True


class JobAgentDaemon:
    """
    Long-running daemon that manages job applications throughout the day.

    Features:
    - Runs continuously within configured hours
    - Respects platform rate limits
    - Takes breaks to appear human
    - Resets counters daily
    - Graceful shutdown on SIGTERM/SIGINT
    """

    def __init__(
        self,
        linkedin_limit: int = 15,
        naukri_limit: int = 25,
        start_hour: int = 8,
        end_hour: int = 22,
        headless: bool = True,
    ):
        self.limits = RateLimits(
            linkedin_jobs_per_day=linkedin_limit,
            naukri_jobs_per_day=naukri_limit,
            # Conservative defaults for slow, human-like behavior
            linkedin_min_delay_seconds=60,
            linkedin_max_delay_seconds=300,
            naukri_min_delay_seconds=45,
            naukri_max_delay_seconds=180,
            max_applications_per_hour=3,
            long_break_every_n_applications=4,
            long_break_duration_minutes=(15, 45),
        )

        self.schedule = DailySchedule(
            start_hour=start_hour,
            end_hour=end_hour,
        )

        self.headless = headless
        self.runner: AutoApplyRunner | None = None
        self._last_date: str = ""

    def _check_new_day(self) -> bool:
        """Check if it's a new day and reset counters if needed."""
        today = datetime.now().strftime("%Y-%m-%d")
        if today != self._last_date:
            self._last_date = today
            if self.runner:
                self.runner.scheduler.reset_daily_counters()
            logger.info("New day detected: %s - counters reset", today)
            log_event("new_day", "info", f"Daily reset: {today}")
            return True
        return False

    def _is_active_hours(self) -> bool:
        """Check if within active operating hours."""
        now = datetime.now()
        is_weekend = now.weekday() >= 5

        if is_weekend and not self.schedule.work_on_weekends:
            return False

        start = self.schedule.weekend_start_hour if is_weekend else self.schedule.start_hour
        end = self.schedule.weekend_end_hour if is_weekend else self.schedule.end_hour

        return start <= now.hour < end

    def _wait_for_active_hours(self) -> bool:
        """Wait until active hours. Returns False if shutdown requested."""
        global _shutdown_requested

        while not self._is_active_hours():
            if _shutdown_requested:
                return False

            now = datetime.now()
            is_weekend = now.weekday() >= 5
            start = self.schedule.weekend_start_hour if is_weekend else self.schedule.start_hour

            # Calculate wait time
            if now.hour >= self.schedule.end_hour:
                # Wait until tomorrow
                tomorrow = now + timedelta(days=1)
                next_start = tomorrow.replace(hour=start, minute=0, second=0, microsecond=0)
            else:
                next_start = now.replace(hour=start, minute=0, second=0, microsecond=0)

            wait_seconds = (next_start - now).total_seconds()
            logger.info("Outside active hours. Sleeping until %s (%d minutes)", next_start, wait_seconds / 60)

            # Sleep in chunks to check for shutdown
            while wait_seconds > 0 and not _shutdown_requested:
                sleep_chunk = min(300, wait_seconds)  # 5 minute chunks
                time.sleep(sleep_chunk)
                wait_seconds -= sleep_chunk
                self._check_new_day()

        return not _shutdown_requested

    def run(self) -> None:
        """Main daemon loop."""
        global _shutdown_requested

        # Set up signal handlers
        signal.signal(signal.SIGTERM, _signal_handler)
        signal.signal(signal.SIGINT, _signal_handler)

        logger.info("Job Agent Daemon starting...")
        logger.info("LinkedIn limit: %d/day, Naukri limit: %d/day",
                   self.limits.linkedin_jobs_per_day, self.limits.naukri_jobs_per_day)
        logger.info("Active hours: %d:00 - %d:00", self.schedule.start_hour, self.schedule.end_hour)

        init_database()
        log_event("daemon_start", "success", "Job agent daemon started")

        self.runner = AutoApplyRunner(
            rate_limits=self.limits,
            schedule=self.schedule,
            headless=self.headless,
        )

        try:
            while not _shutdown_requested:
                # Wait for active hours
                if not self._wait_for_active_hours():
                    break

                # Check for new day
                self._check_new_day()

                # Run a batch of applications
                logger.info("Starting application batch...")
                try:
                    stats = self.runner.run_daily_session()
                    logger.info("Batch complete: LinkedIn=%d, Naukri=%d",
                               stats["linkedin_applied"], stats["naukri_applied"])
                except Exception as e:
                    logger.error("Batch failed: %s", e)
                    log_event("batch_error", "error", str(e))

                # Long pause between batches (1-2 hours)
                if not _shutdown_requested:
                    pause = 3600 + (3600 * (0.5 + 0.5 * time.time() % 1))  # 1-2 hours
                    logger.info("Pausing for %.0f minutes before next batch", pause / 60)
                    time.sleep(pause)

        finally:
            logger.info("Shutting down daemon...")
            if self.runner:
                self.runner.cleanup()
            log_event("daemon_stop", "success", "Job agent daemon stopped")
            logger.info("Daemon stopped gracefully")


def main():
    parser = argparse.ArgumentParser(description="Job Application Automation Daemon")
    parser.add_argument("--linkedin-limit", type=int, default=15, help="LinkedIn daily limit")
    parser.add_argument("--naukri-limit", type=int, default=25, help="Naukri daily limit")
    parser.add_argument("--start-hour", type=int, default=8, help="Start hour (24h format)")
    parser.add_argument("--end-hour", type=int, default=22, help="End hour (24h format)")
    parser.add_argument("--visible", action="store_true", help="Show browser windows")
    parser.add_argument("--log-file", type=str, help="Log to file instead of stdout")

    args = parser.parse_args()

    # Configure logging
    log_config = {
        "level": logging.INFO,
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    }
    if args.log_file:
        log_config["filename"] = args.log_file
    logging.basicConfig(**log_config)

    daemon = JobAgentDaemon(
        linkedin_limit=args.linkedin_limit,
        naukri_limit=args.naukri_limit,
        start_hour=args.start_hour,
        end_hour=args.end_hour,
        headless=not args.visible,
    )

    daemon.run()


if __name__ == "__main__":
    main()
