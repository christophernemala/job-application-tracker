"""LinkedIn Easy Apply engine.

Handles the LinkedIn Easy Apply flow:
1. Navigate to job page
2. Click Easy Apply button
3. Fill form fields from saved answers
4. Upload resume if needed
5. Click through multi-step form
6. Submit and capture confirmation
"""

from typing import Optional

from src.appliers.base_applier import BaseApplier, ApplicationResult
from src.utils.logger import get_logger

logger = get_logger(__name__)

SELECTORS = {
    "easy_apply_btn": "button.jobs-apply-button, button[aria-label*='Easy Apply']",
    "next_btn": "button[aria-label='Continue to next step'], button[aria-label='Next']",
    "review_btn": "button[aria-label='Review your application'], button[aria-label='Review']",
    "submit_btn": "button[aria-label='Submit application'], button[aria-label='Submit']",
    "dismiss_btn": "button[aria-label='Dismiss'], button.artdeco-modal__dismiss",
    "file_upload": "input[type='file']",
    "phone_input": "input[name*='phone'], input[id*='phone']",
    "confirmation": "div.jpac-modal-content, h2.t-bold, div[data-test-modal-header]",
    "error_banner": "div.artdeco-inline-feedback--error, div[role='alert']",
    # Screening question fields
    "text_input": "input[type='text']:not([name*='phone'])",
    "select_field": "select",
    "radio_yes": "label[for*='yes'], input[value='Yes']",
    "textarea": "textarea",
}

MAX_FORM_STEPS = 6


class LinkedInApplier(BaseApplier):
    """LinkedIn Easy Apply application engine."""

    def __init__(self, answers: dict):
        super().__init__(answers, "linkedin")

    def apply(self, job: dict, page, resume_path: Optional[str] = None) -> ApplicationResult:
        """Apply to a job via LinkedIn Easy Apply.

        Args:
            job: Job dict with url, title, id, etc.
            page: Playwright page (must be logged into LinkedIn).
            resume_path: Path to resume PDF.

        Returns:
            ApplicationResult with success/failure details.
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

            # Step 2: Click Easy Apply button
            if not self._click_easy_apply(page):
                screenshot = self._take_screenshot(page, "no_easy_apply", job_id)
                return ApplicationResult(
                    job_id=job_id,
                    source="linkedin",
                    success=False,
                    failure_reason="Easy Apply button not found",
                    screenshot_path=screenshot,
                )

            page.wait_for_timeout(2000)
            self._take_screenshot(page, "apply_modal_open", job_id)

            # Step 3: Process multi-step form
            for step in range(MAX_FORM_STEPS):
                self.logger.debug("Processing form step %d", step + 1)

                # Try to upload resume if file input appears
                if resume_path:
                    self._upload_resume(page, SELECTORS["file_upload"], resume_path)

                # Fill any visible form fields
                self._fill_form_fields(page)

                # Check for errors
                error = page.query_selector(SELECTORS["error_banner"])
                if error:
                    error_text = error.inner_text().strip()
                    self.logger.warning("Form error at step %d: %s", step + 1, error_text)

                # Try submit button first (final step)
                if self._click_button(page, SELECTORS["submit_btn"], "Submit"):
                    page.wait_for_timeout(3000)
                    break

                # Try review button
                if self._click_button(page, SELECTORS["review_btn"], "Review"):
                    page.wait_for_timeout(2000)
                    continue

                # Try next button
                if self._click_button(page, SELECTORS["next_btn"], "Next"):
                    page.wait_for_timeout(2000)
                    continue

                # No buttons found – might be stuck
                self.logger.warning("No form navigation button found at step %d", step + 1)
                self._take_screenshot(page, f"stuck_step_{step}", job_id)
                break

            # Step 4: Check for confirmation
            page.wait_for_timeout(2000)
            confirmation = self._detect_confirmation(
                page,
                [SELECTORS["confirmation"]],
            )
            screenshot = self._take_screenshot(page, "final_state", job_id)

            # Dismiss any modal
            self._click_button(page, SELECTORS["dismiss_btn"], "Dismiss")

            if confirmation:
                self.logger.info(
                    "Successfully applied to '%s': %s", job_title, confirmation,
                )
                return ApplicationResult(
                    job_id=job_id,
                    source="linkedin",
                    success=True,
                    confirmation_text=confirmation,
                    screenshot_path=screenshot,
                    resume_used=resume_path,
                )
            else:
                self.logger.warning("No confirmation detected for '%s'", job_title)
                return ApplicationResult(
                    job_id=job_id,
                    source="linkedin",
                    success=False,
                    failure_reason="No confirmation text detected after submission",
                    screenshot_path=screenshot,
                    resume_used=resume_path,
                )

        except Exception as e:
            self.logger.error("Application error for '%s': %s", job_title, str(e))
            screenshot = self._take_screenshot(page, "error", job_id)
            return ApplicationResult(
                job_id=job_id,
                source="linkedin",
                success=False,
                failure_reason=str(e),
                screenshot_path=screenshot,
            )

    def _click_easy_apply(self, page) -> bool:
        """Find and click the Easy Apply button."""
        for selector in SELECTORS["easy_apply_btn"].split(", "):
            try:
                btn = page.query_selector(selector)
                if btn and btn.is_visible():
                    btn.click()
                    self.logger.debug("Clicked Easy Apply via: %s", selector)
                    return True
            except Exception:
                continue
        return False

    def _fill_form_fields(self, page) -> None:
        """Fill visible form fields with saved answers."""
        screening_defaults = self.answers.get("screening_question_defaults", {})

        # Phone number
        self._fill_field(
            page,
            SELECTORS["phone_input"],
            self.answers.get("phone", ""),
            "phone",
        )

        # Text inputs – try to match by label/placeholder
        text_inputs = page.query_selector_all(SELECTORS["text_input"])
        for text_input in text_inputs:
            try:
                current_value = text_input.input_value()
                if current_value:
                    continue  # Already filled

                placeholder = text_input.get_attribute("placeholder") or ""
                label = self._get_label_for_input(page, text_input)
                field_context = (placeholder + " " + label).lower()

                value = self._match_answer(field_context)
                if value:
                    text_input.fill(value)
                    self.logger.debug("Filled text field: %s", field_context[:50])
            except Exception:
                continue

        # Textareas (e.g., cover letter)
        textareas = page.query_selector_all(SELECTORS["textarea"])
        for textarea in textareas:
            try:
                current = textarea.input_value()
                if current:
                    continue
                label = self._get_label_for_input(page, textarea)
                if "cover letter" in label.lower():
                    # Skip cover letter – manual review territory
                    self.logger.debug("Skipping cover letter textarea")
                    continue
            except Exception:
                continue

        # Select dropdowns
        selects = page.query_selector_all(SELECTORS["select_field"])
        for select in selects:
            try:
                label = self._get_label_for_input(page, select)
                # Try to select the first non-placeholder option
                options = select.query_selector_all("option")
                if len(options) > 1:
                    # Select Yes if it's a yes/no question
                    for opt in options:
                        opt_text = opt.inner_text().strip().lower()
                        if opt_text == "yes":
                            select.select_option(label=opt.inner_text().strip())
                            break
            except Exception:
                continue

    def _match_answer(self, field_context: str) -> Optional[str]:
        """Match a form field context to saved answers.

        Args:
            field_context: Combined placeholder + label text.

        Returns:
            Matching answer value or None.
        """
        context = field_context.lower()

        field_mapping = {
            "experience": str(self.answers.get("total_experience_years", "")),
            "years": str(self.answers.get("total_experience_years", "")),
            "salary": str(self.answers.get("expected_salary_aed", "")),
            "notice": self.answers.get("notice_period", ""),
            "visa": self.answers.get("visa_status", ""),
            "location": self.answers.get("current_location", ""),
            "city": self.answers.get("current_location", ""),
        }

        for keyword, value in field_mapping.items():
            if keyword in context and value:
                return str(value)

        return None

    def _get_label_for_input(self, page, element) -> str:
        """Try to find the label for a form input."""
        try:
            element_id = element.get_attribute("id")
            if element_id:
                label = page.query_selector(f'label[for="{element_id}"]')
                if label:
                    return label.inner_text().strip()

            # Try parent container
            parent = element.evaluate_handle("el => el.parentElement")
            if parent:
                label = parent.as_element().query_selector("label, span.t-bold, p.t-bold")
                if label:
                    return label.inner_text().strip()
        except Exception:
            pass
        return ""
