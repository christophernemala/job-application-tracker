"""Human-like scheduler for job scraping and auto-apply to avoid platform detection."""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable

logger = logging.getLogger(__name__)


class ActivityState(Enum):
    """Human activity states throughout the day."""
    SLEEPING = "sleeping"
    MORNING_COFFEE = "morning_coffee"
    ACTIVE_BROWSING = "active_browsing"
    LUNCH_BREAK = "lunch_break"
    AFTERNOON_WORK = "afternoon_work"
    EVENING_WIND_DOWN = "evening_wind_down"
    SHORT_BREAK = "short_break"


@dataclass
class RateLimits:
    """Platform-specific rate limits to avoid detection."""
    # LinkedIn is stricter - fewer actions per day
    linkedin_jobs_per_day: int = 15
    linkedin_min_delay_seconds: int = 45
    linkedin_max_delay_seconds: int = 180
    linkedin_page_view_delay: tuple[int, int] = (8, 25)

    # Naukri Gulf is slightly more lenient
    naukri_jobs_per_day: int = 25
    naukri_min_delay_seconds: int = 30
    naukri_max_delay_seconds: int = 120
    naukri_page_view_delay: tuple[int, int] = (5, 15)

    # Global limits
    max_applications_per_hour: int = 4
    min_break_between_platforms_minutes: int = 15
    long_break_every_n_applications: int = 5
    long_break_duration_minutes: tuple[int, int] = (10, 30)


@dataclass
class DailySchedule:
    """Configurable daily activity windows (24h format, local time)."""
    # Active hours - when the bot can work
    start_hour: int = 8
    end_hour: int = 22

    # Mandatory break periods (hour ranges)
    lunch_break: tuple[int, int] = (12, 13)
    evening_break: tuple[int, int] = (18, 19)

    # Weekend behavior
    work_on_weekends: bool = True
    weekend_start_hour: int = 10
    weekend_end_hour: int = 20


@dataclass
class SessionState:
    """Track current session state for human-like behavior."""
    applications_today: dict[str, int] = field(default_factory=lambda: {"linkedin": 0, "naukri": 0})
    applications_this_hour: int = 0
    last_application_time: datetime | None = None
    last_platform: str | None = None
    consecutive_applications: int = 0
    session_start: datetime = field(default_factory=datetime.now)
    total_breaks_taken: int = 0
    is_taking_break: bool = False


class HumanScheduler:
    """
    Mimics human browsing patterns for job applications.

    Features:
    - Random delays between actions (not uniform)
    - Respects active hours and break times
    - Platform rotation to avoid detection
    - Daily application limits per platform
    - Simulated "thinking time" when viewing jobs
    - Random mouse movements and scroll patterns (via automation layer)
    """

    def __init__(
        self,
        rate_limits: RateLimits | None = None,
        schedule: DailySchedule | None = None,
    ):
        self.limits = rate_limits or RateLimits()
        self.schedule = schedule or DailySchedule()
        self.state = SessionState()
        self._callbacks: dict[str, list[Callable]] = {
            "on_break_start": [],
            "on_break_end": [],
            "on_daily_limit_reached": [],
            "on_application_complete": [],
        }

    def register_callback(self, event: str, callback: Callable) -> None:
        """Register callbacks for scheduler events."""
        if event in self._callbacks:
            self._callbacks[event].append(callback)

    def _trigger_callbacks(self, event: str, **kwargs) -> None:
        for cb in self._callbacks.get(event, []):
            try:
                cb(**kwargs)
            except Exception as e:
                logger.warning("Callback error for %s: %s", event, e)

    def get_current_state(self) -> ActivityState:
        """Determine current activity state based on time of day."""
        now = datetime.now()
        hour = now.hour

        # Check if within active hours
        is_weekend = now.weekday() >= 5
        if is_weekend and not self.schedule.work_on_weekends:
            return ActivityState.SLEEPING

        start = self.schedule.weekend_start_hour if is_weekend else self.schedule.start_hour
        end = self.schedule.weekend_end_hour if is_weekend else self.schedule.end_hour

        if hour < start or hour >= end:
            return ActivityState.SLEEPING

        # Check break periods
        if self.schedule.lunch_break[0] <= hour < self.schedule.lunch_break[1]:
            return ActivityState.LUNCH_BREAK
        if self.schedule.evening_break[0] <= hour < self.schedule.evening_break[1]:
            return ActivityState.EVENING_WIND_DOWN

        # Morning vs afternoon activity
        if hour < 12:
            return ActivityState.MORNING_COFFEE if hour < 9 else ActivityState.ACTIVE_BROWSING
        return ActivityState.AFTERNOON_WORK

    def can_apply_now(self, platform: str) -> tuple[bool, str]:
        """Check if we can apply to a job right now."""
        state = self.get_current_state()

        # Not during sleep or breaks
        if state == ActivityState.SLEEPING:
            return False, "Outside active hours"
        if state in (ActivityState.LUNCH_BREAK, ActivityState.EVENING_WIND_DOWN):
            return False, f"Currently on {state.value}"
        if self.state.is_taking_break:
            return False, "Taking a short break"

        # Check daily limits
        platform_key = platform.lower()
        daily_limit = (
            self.limits.linkedin_jobs_per_day
            if platform_key == "linkedin"
            else self.limits.naukri_jobs_per_day
        )

        if self.state.applications_today.get(platform_key, 0) >= daily_limit:
            self._trigger_callbacks("on_daily_limit_reached", platform=platform)
            return False, f"Daily limit reached for {platform} ({daily_limit})"

        # Check hourly rate
        if self.state.applications_this_hour >= self.limits.max_applications_per_hour:
            return False, "Hourly application limit reached"

        # Check platform switching cooldown
        if (
            self.state.last_platform
            and self.state.last_platform != platform_key
            and self.state.last_application_time
        ):
            elapsed = (datetime.now() - self.state.last_application_time).total_seconds()
            min_wait = self.limits.min_break_between_platforms_minutes * 60
            if elapsed < min_wait:
                return False, f"Platform switch cooldown ({int(min_wait - elapsed)}s remaining)"

        return True, "Ready to apply"

    def get_delay_before_action(self, platform: str, action: str = "apply") -> int:
        """
        Calculate human-like delay before next action.
        Uses weighted randomness to simulate natural behavior.
        """
        platform_key = platform.lower()

        if platform_key == "linkedin":
            base_min = self.limits.linkedin_min_delay_seconds
            base_max = self.limits.linkedin_max_delay_seconds
        else:
            base_min = self.limits.naukri_min_delay_seconds
            base_max = self.limits.naukri_max_delay_seconds

        # Add variability based on time of day
        state = self.get_current_state()
        multiplier = 1.0

        if state == ActivityState.MORNING_COFFEE:
            multiplier = 1.3  # Slower in early morning
        elif state == ActivityState.AFTERNOON_WORK:
            multiplier = 0.9  # Slightly faster mid-afternoon

        # Add fatigue factor - slower after many applications
        consecutive = self.state.consecutive_applications
        if consecutive > 3:
            multiplier += 0.1 * (consecutive - 3)

        # Calculate final delay with some randomness
        # Use beta distribution for more natural variation (peaked in middle)
        alpha, beta = 2, 5
        random_factor = random.betavariate(alpha, beta)

        delay = int(base_min + (base_max - base_min) * random_factor * multiplier)

        # Add occasional "distraction" delays (simulating checking phone, etc.)
        if random.random() < 0.15:  # 15% chance of distraction
            delay += random.randint(30, 120)
            logger.debug("Adding distraction delay")

        return delay

    def get_page_view_delay(self, platform: str) -> int:
        """Delay for viewing a job posting (reading time)."""
        platform_key = platform.lower()

        if platform_key == "linkedin":
            min_d, max_d = self.limits.linkedin_page_view_delay
        else:
            min_d, max_d = self.limits.naukri_page_view_delay

        # Simulate reading - normal distribution centered slightly above middle
        mean = min_d + (max_d - min_d) * 0.6
        std_dev = (max_d - min_d) / 4
        delay = int(random.gauss(mean, std_dev))

        return max(min_d, min(max_d, delay))

    def should_take_break(self) -> tuple[bool, int]:
        """
        Check if a break should be taken. Returns (should_break, duration_seconds).
        """
        # Mandatory break after N consecutive applications
        if self.state.consecutive_applications >= self.limits.long_break_every_n_applications:
            min_break, max_break = self.limits.long_break_duration_minutes
            duration = random.randint(min_break, max_break) * 60
            return True, duration

        # Random short breaks (10% chance after each application)
        if random.random() < 0.10:
            return True, random.randint(60, 180)

        return False, 0

    def record_application(self, platform: str, success: bool) -> None:
        """Record a completed application attempt."""
        platform_key = platform.lower()
        now = datetime.now()

        if success:
            self.state.applications_today[platform_key] = (
                self.state.applications_today.get(platform_key, 0) + 1
            )
            self.state.applications_this_hour += 1
            self.state.consecutive_applications += 1

        self.state.last_application_time = now
        self.state.last_platform = platform_key

        self._trigger_callbacks(
            "on_application_complete",
            platform=platform,
            success=success,
            total_today=self.state.applications_today,
        )

        logger.info(
            "Application recorded: platform=%s, success=%s, today_total=%s",
            platform,
            success,
            self.state.applications_today,
        )

    def take_break(self, duration_seconds: int) -> None:
        """Execute a break period."""
        self.state.is_taking_break = True
        self.state.total_breaks_taken += 1
        self._trigger_callbacks("on_break_start", duration=duration_seconds)

        logger.info("Taking break for %d seconds", duration_seconds)
        time.sleep(duration_seconds)

        self.state.is_taking_break = False
        self.state.consecutive_applications = 0  # Reset after break
        self._trigger_callbacks("on_break_end")

    def reset_hourly_counter(self) -> None:
        """Reset the hourly application counter (call this every hour)."""
        self.state.applications_this_hour = 0

    def reset_daily_counters(self) -> None:
        """Reset all daily counters (call at start of new day)."""
        self.state.applications_today = {"linkedin": 0, "naukri": 0}
        self.state.applications_this_hour = 0
        self.state.consecutive_applications = 0
        self.state.total_breaks_taken = 0
        self.state.session_start = datetime.now()
        logger.info("Daily counters reset")

    def get_next_active_window(self) -> datetime:
        """Calculate when the next active window starts."""
        now = datetime.now()
        is_weekend = now.weekday() >= 5

        if is_weekend and not self.schedule.work_on_weekends:
            # Find next Monday
            days_until_monday = (7 - now.weekday()) % 7
            if days_until_monday == 0:
                days_until_monday = 7
            next_active = now.replace(
                hour=self.schedule.start_hour,
                minute=0,
                second=0,
                microsecond=0,
            ) + timedelta(days=days_until_monday)
            return next_active

        start = self.schedule.weekend_start_hour if is_weekend else self.schedule.start_hour
        end = self.schedule.weekend_end_hour if is_weekend else self.schedule.end_hour

        if now.hour < start:
            return now.replace(hour=start, minute=0, second=0, microsecond=0)
        elif now.hour >= end:
            # Next day
            tomorrow = now + timedelta(days=1)
            next_is_weekend = tomorrow.weekday() >= 5
            next_start = (
                self.schedule.weekend_start_hour
                if next_is_weekend
                else self.schedule.start_hour
            )
            return tomorrow.replace(hour=next_start, minute=0, second=0, microsecond=0)

        return now  # Already in active window

    def get_status_summary(self) -> dict:
        """Get current scheduler status for monitoring."""
        state = self.get_current_state()
        return {
            "current_state": state.value,
            "applications_today": dict(self.state.applications_today),
            "applications_this_hour": self.state.applications_this_hour,
            "consecutive_applications": self.state.consecutive_applications,
            "is_taking_break": self.state.is_taking_break,
            "breaks_taken_today": self.state.total_breaks_taken,
            "last_platform": self.state.last_platform,
            "session_duration_minutes": (
                (datetime.now() - self.state.session_start).total_seconds() / 60
            ),
            "limits": {
                "linkedin_daily": self.limits.linkedin_jobs_per_day,
                "naukri_daily": self.limits.naukri_jobs_per_day,
                "hourly": self.limits.max_applications_per_hour,
            },
        }
