"""Base applier – Abstract interface for browser-based job applications.

All source-specific appliers inherit from BaseApplier and implement
the apply() method. Provides common utilities for screenshot capture,
form filling, and result logging.
"""

import abc
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from src.utils.logger import get_logger, get_screenshot_path

logger = get_logger(__name__)


@dataclass
class ApplicationResult:
    """Result of an application attempt."""
    job_id: int
    source: str
    success: bool
    confirmation_text: Optional[str] = None
    screenshot_path: Optional[str] = None
    resume_used: Optional[str] = None
    failure_reason: Optional[str] = None
    applied_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "source": self.source,
            "success": self.success,
            "confirmation_text": self.confirmation_text,
            "screenshot_path": self.screenshot_path,
            "resume_used": self.resume_used,
            "failure_reason": self.failure_reason,
            "applied_at": self.applied_at,
        }


class BaseApplier(abc.ABC):
    """Abstract base class for job application engines.

    Subclasses must implement apply() which attempts to submit
    an application for a single job.
    """

    def __init__(self, answers: dict, source_name: str):
        """Initialize with pre-filled answers and source name.

        Args:
            answers: Pre-filled form answers from answers.json.
            source_name: Name of the source platform.
        """
        self.answers = answers
        self.source_name = source_name
        self.logger = get_logger(f"applier.{source_name}")

    @abc.abstractmethod
    def apply(self, job: dict, page, resume_path: Optional[str] = None) -> ApplicationResult:
        """Attempt to apply to a single job.

        Args:
            job: Job dict with url, title, apply_type, etc.
            page: Playwright page instance.
            resume_path: Optional path to resume file.

        Returns:
            ApplicationResult with outcome details.
        """
        ...

    def _take_screenshot(self, page, stage: str, job_id: Optional[int] = None) -> str:
        """Capture a screenshot and return the file path.

        Args:
            page: Playwright page instance.
            stage: Name of the stage (e.g., 'apply_button', 'confirmation').
            job_id: Optional job ID for tracing.

        Returns:
            Screenshot file path as string.
        """
        screenshot_path = get_screenshot_path(
            stage, job_id=str(job_id) if job_id else None, source=self.source_name
        )
        try:
            page.screenshot(path=str(screenshot_path))
            self.logger.debug("Screenshot saved: %s", screenshot_path)
        except Exception as e:
            self.logger.warning("Failed to save screenshot: %s", str(e))
            return ""
        return str(screenshot_path)

    def _fill_field(self, page, selector: str, value: str, field_name: str = "") -> bool:
        """Safely fill a form field.

        Args:
            page: Playwright page.
            selector: CSS selector for the input.
            value: Value to fill.
            field_name: Human name for logging.

        Returns:
            True if field was found and filled.
        """
        try:
            el = page.query_selector(selector)
            if el:
                el.fill(value)
                self.logger.debug("Filled field '%s' with value", field_name or selector)
                return True
            else:
                self.logger.debug("Field not found: %s", field_name or selector)
                return False
        except Exception as e:
            self.logger.warning("Error filling field '%s': %s", field_name or selector, str(e))
            return False

    def _click_button(self, page, selector: str, button_name: str = "", timeout: int = 5000) -> bool:
        """Safely click a button.

        Args:
            page: Playwright page.
            selector: CSS selector for the button.
            button_name: Human name for logging.
            timeout: Wait timeout in ms.

        Returns:
            True if button was found and clicked.
        """
        try:
            el = page.query_selector(selector)
            if el and el.is_visible():
                el.click()
                page.wait_for_timeout(1000)
                self.logger.debug("Clicked '%s'", button_name or selector)
                return True
            else:
                self.logger.debug("Button not found or not visible: %s", button_name or selector)
                return False
        except Exception as e:
            self.logger.warning("Error clicking '%s': %s", button_name or selector, str(e))
            return False

    def _upload_resume(self, page, selector: str, resume_path: str) -> bool:
        """Upload a resume file to a file input.

        Args:
            page: Playwright page.
            selector: CSS selector for file input.
            resume_path: Path to resume file.

        Returns:
            True if upload succeeded.
        """
        try:
            file_input = page.query_selector(selector)
            if file_input:
                file_input.set_input_files(resume_path)
                self.logger.info("Resume uploaded: %s", resume_path)
                return True
            else:
                self.logger.debug("File input not found: %s", selector)
                return False
        except Exception as e:
            self.logger.warning("Failed to upload resume: %s", str(e))
            return False

    def _detect_confirmation(self, page, patterns: list[str]) -> Optional[str]:
        """Check page for confirmation text.

        Args:
            page: Playwright page.
            patterns: List of CSS selectors to check for confirmation.

        Returns:
            Confirmation text if found, else None.
        """
        for selector in patterns:
            try:
                el = page.query_selector(selector)
                if el:
                    text = el.inner_text().strip()
                    if text:
                        return text
            except Exception:
                continue

        # Fallback: check page text content
        try:
            body_text = page.inner_text("body")
            confirmation_keywords = [
                "application submitted",
                "successfully applied",
                "application received",
                "thank you for applying",
                "application complete",
            ]
            for keyword in confirmation_keywords:
                if keyword.lower() in body_text.lower():
                    return keyword
        except Exception:
            pass

        return None
