"""NaukriGulf application engine.

Handles the NaukriGulf application flow:
1. Navigate to job page
2. Click Apply button
3. Fill form fields (screening questions, profile details)
4. Upload resume if required
5. Submit and capture confirmation
"""

from typing import Optional

from src.appliers.base_applier import BaseApplier, ApplicationResult
from src.utils.logger import get_logger

logger = get_logger(__name__)

SELECTORS = {
    "apply_btn": (
        "button.apply-btn, a.apply-btn, button.chatbot-apply-btn, "
        "button[class*='apply'], a[class*='apply'], "
        "button:has-text('Apply'), a:has-text('Apply Now')"
    ),
    "submit_btn": (
        "button[type='submit'], button:has-text('Submit'), "
        "button:has-text('Apply'), input[type='submit']"
    ),
    "next_btn": "button:has-text('Next'), button:has-text('Continue')",
    "file_upload": "input[type='file']",
    "text_input": "input[type='text'], input[type='number'], input[type='tel']",
    "select_field": "select",
    "textarea": "textarea",
    "confirmation": (
        "div.success-message, div[class*='success'], "
        "div.apply-success, div.confirmation, "
        "h2:has-text('applied'), p:has-text('submitted')"
    ),
    "error_msg": "div.error-message, div[class*='error'], span.error",
    # Pre-filled profile fields on NaukriGulf
    "experience_years": "input[name*='experience'], select[name*='experience']",
    "salary_field": "input[name*='salary'], input[name*='ctc']",
    "notice_field": "select[name*='notice'], input[name*='notice']",
    "location_field": "input[name*='location'], select[name*='location']",
}

MAX_FORM_STEPS = 5


class NaukriGulfApplier(BaseApplier):
    """NaukriGulf application engine."""

    def __init__(self, answers: dict):
        super().__init__(answers, "naukrigulf")

    def apply(self, job: dict, page, resume_path: Optional[str] = None) -> ApplicationResult:
        """Apply to a job on NaukriGulf.

        Args:
            job: Job dict with url, title, id, etc.
            page: Playwright page (must be logged into NaukriGulf).
            resume_path: Path to resume PDF.

        Returns:
            ApplicationResult with outcome details.
        """
        job_id = job.get("id", 0)
        job_url = job.get("url", "")
        job_title = job.get("title", "Unknown")

        self.logger.info("Applying to: %s at %s", job_title, job.get("company", "?"))

        try:
            # Step 1: Navigate to job page
            page.goto(job_url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)
            self._take_screenshot(page, "job_page", job_id)

            # Step 2: Click Apply button
            if not self._click_apply(page):
                screenshot = self._take_screenshot(page, "no_apply_btn", job_id)
                return ApplicationResult(
                    job_id=job_id,
                    source="naukrigulf",
                    success=False,
                    failure_reason="Apply button not found or not clickable",
                    screenshot_path=screenshot,
                )

            page.wait_for_timeout(3000)
            self._take_screenshot(page, "after_apply_click", job_id)

            # Step 3: Check if we were redirected to an external site
            if "naukrigulf.com" not in page.url:
                self.logger.warning(
                    "Redirected to external site: %s", page.url
                )
                screenshot = self._take_screenshot(page, "external_redirect", job_id)
                return ApplicationResult(
                    job_id=job_id,
                    source="naukrigulf",
                    success=False,
                    failure_reason=f"Redirected to external ATS: {page.url}",
                    screenshot_path=screenshot,
                )

            # Step 4: Fill form fields
            for step in range(MAX_FORM_STEPS):
                self.logger.debug("Processing form step %d", step + 1)

                # Upload resume if input appears
                if resume_path:
                    self._upload_resume(page, SELECTORS["file_upload"], resume_path)

                # Fill form fields
                self._fill_form_fields(page)

                # Check for errors
                error_el = page.query_selector(SELECTORS["error_msg"])
                if error_el:
                    error_text = error_el.inner_text().strip()
                    self.logger.warning("Form error: %s", error_text)

                # Try submit
                if self._click_button(page, SELECTORS["submit_btn"], "Submit"):
                    page.wait_for_timeout(3000)
                    break

                # Try next
                if self._click_button(page, SELECTORS["next_btn"], "Next"):
                    page.wait_for_timeout(2000)
                    continue

                # No more buttons
                self.logger.debug("No navigation buttons at step %d", step + 1)
                break

            # Step 5: Check confirmation
            page.wait_for_timeout(2000)
            confirmation = self._detect_confirmation(
                page, SELECTORS["confirmation"].split(", ")
            )
            screenshot = self._take_screenshot(page, "final_state", job_id)

            if confirmation:
                self.logger.info(
                    "Successfully applied to '%s': %s", job_title, confirmation
                )
                return ApplicationResult(
                    job_id=job_id,
                    source="naukrigulf",
                    success=True,
                    confirmation_text=confirmation,
                    screenshot_path=screenshot,
                    resume_used=resume_path,
                )
            else:
                # Check if already applied
                body = page.inner_text("body").lower()
                if "already applied" in body:
                    self.logger.info("Already applied to '%s'", job_title)
                    return ApplicationResult(
                        job_id=job_id,
                        source="naukrigulf",
                        success=False,
                        failure_reason="Already applied to this job",
                        screenshot_path=screenshot,
                    )

                self.logger.warning("No confirmation for '%s'", job_title)
                return ApplicationResult(
                    job_id=job_id,
                    source="naukrigulf",
                    success=False,
                    failure_reason="No confirmation detected after submission",
                    screenshot_path=screenshot,
                    resume_used=resume_path,
                )

        except Exception as e:
            self.logger.error("Application error for '%s': %s", job_title, str(e))
            screenshot = self._take_screenshot(page, "error", job_id)
            return ApplicationResult(
                job_id=job_id,
                source="naukrigulf",
                success=False,
                failure_reason=str(e),
                screenshot_path=screenshot,
            )

    def _click_apply(self, page) -> bool:
        """Find and click the Apply button."""
        for selector in SELECTORS["apply_btn"].split(", "):
            selector = selector.strip()
            try:
                btn = page.query_selector(selector)
                if btn and btn.is_visible():
                    btn.click()
                    self.logger.debug("Clicked Apply via: %s", selector)
                    return True
            except Exception:
                continue
        return False

    def _fill_form_fields(self, page) -> None:
        """Fill visible form fields with saved answers."""
        # Experience
        self._fill_field(
            page,
            SELECTORS["experience_years"],
            str(self.answers.get("total_experience_years", "")),
            "experience",
        )

        # Salary
        self._fill_field(
            page,
            SELECTORS["salary_field"],
            str(self.answers.get("expected_salary_aed", "")),
            "salary",
        )

        # Generic text inputs
        text_inputs = page.query_selector_all(SELECTORS["text_input"])
        for text_input in text_inputs:
            try:
                current_value = text_input.input_value()
                if current_value:
                    continue

                name = text_input.get_attribute("name") or ""
                placeholder = text_input.get_attribute("placeholder") or ""
                context = (name + " " + placeholder).lower()

                value = self._match_answer_to_context(context)
                if value:
                    text_input.fill(value)
            except Exception:
                continue

        # Select dropdowns
        selects = page.query_selector_all(SELECTORS["select_field"])
        for select in selects:
            try:
                name = select.get_attribute("name") or ""
                context = name.lower()

                if "notice" in context:
                    # Try to select option matching notice period
                    self._select_best_option(select, "1 month")
                elif "experience" in context:
                    self._select_best_option(select, "5")
            except Exception:
                continue

    def _match_answer_to_context(self, context: str) -> Optional[str]:
        """Match form field to saved answers."""
        mapping = {
            "experience": str(self.answers.get("total_experience_years", "")),
            "salary": str(self.answers.get("expected_salary_aed", "")),
            "notice": self.answers.get("notice_period", ""),
            "location": self.answers.get("current_location", ""),
            "phone": "",  # Don't auto-fill phone without explicit config
        }

        for keyword, value in mapping.items():
            if keyword in context and value:
                return value

        return None

    def _select_best_option(self, select_element, target_text: str) -> bool:
        """Select the option that best matches the target text."""
        try:
            options = select_element.query_selector_all("option")
            target_lower = target_text.lower()

            for opt in options:
                opt_text = opt.inner_text().strip().lower()
                if target_lower in opt_text or opt_text in target_lower:
                    select_element.select_option(label=opt.inner_text().strip())
                    return True

            # Fall back to selecting second option (first is usually placeholder)
            if len(options) > 1:
                select_element.select_option(index=1)
                return True
        except Exception:
            pass
        return False
