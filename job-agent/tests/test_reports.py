"""Tests for report generation and notifications."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestReportGenerator:
    def test_get_summary_stats(self, temp_db):
        """Summary stats returns expected structure."""
        from src.reports.report_generator import get_summary_stats

        stats = get_summary_stats()
        assert "total_jobs" in stats
        assert "route_counts" in stats
        assert "source_counts" in stats
        assert "score_brackets" in stats
        assert "total_applied" in stats
        assert "top_jobs" in stats
        assert "recent_applications" in stats
        assert stats["total_jobs"] == 0  # Empty DB

    def test_get_summary_with_data(self, temp_db):
        """Summary stats reflect inserted data."""
        from src.storage.jobs_repo import insert_job, update_job_score, update_job_route
        from src.reports.report_generator import get_summary_stats

        job_id = insert_job(
            source="linkedin",
            title="Senior AR Analyst",
            url="https://test.com/1",
            company="Test Corp",
            location="Dubai",
        )
        update_job_score(job_id, 85.0, "Strong match")
        update_job_route(job_id, "auto_apply")

        stats = get_summary_stats()
        assert stats["total_jobs"] == 1
        assert stats["route_counts"].get("auto_apply", 0) == 1
        assert len(stats["top_jobs"]) == 1

    def test_generate_html_report(self, temp_db):
        """HTML report generates a valid file."""
        from src.reports.report_generator import generate_html_report

        report_path = generate_html_report()
        assert report_path.exists()
        content = report_path.read_text()
        assert "<html" in content
        assert "Job Agent Report" in content

    def test_terminal_report_no_crash(self, temp_db, capsys):
        """Terminal report prints without error."""
        from src.reports.report_generator import print_terminal_report

        print_terminal_report()  # Should not raise
        captured = capsys.readouterr()
        assert "RUN SUMMARY REPORT" in captured.out


class TestNotifier:
    def test_notify_console(self, capsys):
        """Console notification prints formatted output."""
        from src.notifications.notifier import notify

        notify(
            title="Test Notification",
            message="This is a test",
            level="info",
        )
        captured = capsys.readouterr()
        assert "Test Notification" in captured.out

    def test_notify_application_result(self, capsys):
        """Application result notification prints correctly."""
        from src.notifications.notifier import notify_application_result

        notify_application_result(
            job_title="Senior AR Analyst",
            company="Test Corp",
            success=True,
            job_url="https://test.com/1",
        )
        captured = capsys.readouterr()
        assert "Application Submitted" in captured.out

    def test_notify_failure(self, capsys):
        """Failure notification includes reason."""
        from src.notifications.notifier import notify_application_result

        notify_application_result(
            job_title="Credit Controller",
            company="Finance Co",
            success=False,
            failure_reason="Apply button not found",
        )
        captured = capsys.readouterr()
        assert "Application Failed" in captured.out

    def test_notify_log_file(self, tmp_path, monkeypatch):
        """Notification is appended to JSONL log."""
        import src.notifications.notifier as notifier_mod
        log_file = tmp_path / "notifications.jsonl"
        monkeypatch.setattr(notifier_mod, "NOTIFICATIONS_LOG", log_file)

        notifier_mod.notify(title="Log Test", message="Testing log", level="info")

        assert log_file.exists()
        content = log_file.read_text()
        assert "Log Test" in content
