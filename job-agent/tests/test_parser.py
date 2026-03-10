"""Tests for the job parser and normalizer."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.parsers.job_parser import (
    normalize_title,
    normalize_company,
    parse_salary,
    normalize_location,
    classify_apply_type,
    extract_keywords,
    detect_seniority,
    parse_raw_job,
)
from src.collectors.base_collector import RawJob


class TestNormalizeTitle:
    def test_strips_hiring_prefix(self):
        assert "Senior AR Analyst" in normalize_title("Hiring - Senior AR Analyst")
        assert "Credit Controller" in normalize_title("URGENT: Credit Controller")

    def test_strips_location_suffix(self):
        result = normalize_title("Accounts Receivable Specialist - Dubai")
        assert "Dubai" not in result
        assert "Accounts Receivable Specialist" in result

    def test_normalizes_abbreviations(self):
        assert "Senior" in normalize_title("Sr. AR Analyst")
        assert "Manager" in normalize_title("Mgr. Credit Control")
        assert "Assistant" in normalize_title("Asst. Manager Collections")

    def test_handles_empty(self):
        assert normalize_title("") == ""
        assert normalize_title("  ") == ""


class TestParseSalary:
    def test_aed_range(self):
        min_s, max_s = parse_salary("AED 14,000 - 18,000")
        assert min_s == 14000
        assert max_s == 18000

    def test_single_value(self):
        min_s, max_s = parse_salary("AED 15000")
        assert min_s == 15000
        assert max_s == 15000

    def test_k_notation(self):
        min_s, max_s = parse_salary("AED 15K - 20K")
        assert min_s == 15000
        assert max_s == 20000

    def test_no_salary(self):
        assert parse_salary(None) == (None, None)
        assert parse_salary("") == (None, None)

    def test_non_aed_ignored(self):
        assert parse_salary("USD 5000") == (None, None)


class TestClassifyApplyType:
    def test_easy_apply(self):
        assert classify_apply_type("easy_apply", "https://linkedin.com/jobs/1") == "easy_apply"

    def test_internal(self):
        assert classify_apply_type("internal", "https://naukrigulf.com/jobs/1") == "internal"

    def test_complex_ats(self):
        result = classify_apply_type(None, "https://company.myworkdayjobs.com/en-US/jobs/1")
        assert result == "external_complex"

    def test_unknown(self):
        assert classify_apply_type(None, "https://random-company.com/careers/123") == "unknown"


class TestExtractKeywords:
    def test_ar_keywords(self):
        kw = extract_keywords("Senior Accounts Receivable Analyst", "Managing AR aging and reconciliation")
        assert "accounts_receivable" in kw
        assert "aging" in kw
        assert "reconciliation" in kw

    def test_o2c_keywords(self):
        kw = extract_keywords("Order to Cash Specialist", "")
        assert "order_to_cash" in kw

    def test_oracle_keywords(self):
        kw = extract_keywords("AR Analyst", "Experience with Oracle Fusion required")
        assert "oracle" in kw

    def test_credit_control(self):
        kw = extract_keywords("Credit Controller", "collections and dispute resolution")
        assert "credit_control" in kw
        assert "collections" in kw
        assert "dispute_resolution" in kw


class TestDetectSeniority:
    def test_senior(self):
        assert detect_seniority("Senior AR Analyst") == "senior"

    def test_manager(self):
        assert detect_seniority("Manager Credit Control") == "manager"

    def test_assistant_manager(self):
        assert detect_seniority("Assistant Manager Collections") == "assistant_manager"

    def test_intern(self):
        assert detect_seniority("Intern - Finance") == "intern"

    def test_specialist(self):
        assert detect_seniority("Collections Specialist") == "specialist"

    def test_unknown(self):
        assert detect_seniority("Accounts Receivable") is None


class TestNormalizeLocation:
    def test_dubai(self):
        assert normalize_location("Dubai, UAE") == "Dubai, UAE"

    def test_abbreviation(self):
        assert "Dubai" in normalize_location("DXB")

    def test_full_country_name(self):
        assert "UAE" in normalize_location("United Arab Emirates")


class TestNormalizeCompany:
    def test_strips_suffix(self):
        assert normalize_company("Acme Corp LLC") == "Acme Corp"
        assert normalize_company("Big Co Ltd.") == "Big Co"

    def test_none_input(self):
        assert normalize_company(None) is None


class TestParseRawJob:
    def test_full_parse(self):
        raw = RawJob(
            source="linkedin",
            title="Hiring - Senior Credit Controller - Dubai",
            url="https://linkedin.com/jobs/999",
            company="Finance Corp LLC",
            location="DXB, United Arab Emirates",
            salary_text="AED 15,000 - 20,000",
            description="Credit control and collections management. Oracle Fusion experience required.",
        )

        parsed = parse_raw_job(raw)
        assert parsed["source"] == "linkedin"
        assert "Senior Credit Controller" in parsed["normalized_title"]
        assert parsed["company"] == "Finance Corp"
        assert parsed["salary_min"] == 15000
        assert parsed["salary_max"] == 20000
        assert "credit_control" in parsed["metadata"]["keywords"]
        assert "oracle" in parsed["metadata"]["keywords"]
        assert parsed["metadata"]["seniority"] == "senior"
