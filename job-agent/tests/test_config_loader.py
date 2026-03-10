"""Tests for configuration loading."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils.config_loader import (
    load_profile,
    load_rules,
    load_answers,
    load_sources,
    get_enabled_sources,
    get_scoring_weights,
)


class TestConfigLoader:
    """Test configuration file loading."""

    def test_load_profile(self):
        """Profile config loads with expected fields."""
        profile = load_profile()
        assert profile["candidate_name"] == "Christopher Nemala"
        assert "Dubai" in profile["preferred_locations"]
        assert profile["salary_floor_aed"] == 14000
        assert len(profile["target_titles"]) > 0
        assert len(profile["core_skills"]) > 0

    def test_load_rules(self):
        """Rules config loads with scoring weights and thresholds."""
        rules = load_rules()
        assert rules["min_score_for_auto_apply"] == 80
        assert rules["min_score_for_semi_auto"] == 60
        assert rules["salary_floor"] == 14000
        assert "scoring_weights" in rules
        weights = rules["scoring_weights"]
        assert sum(weights.values()) == 100

    def test_load_answers(self):
        """Answers config loads with required fields."""
        answers = load_answers()
        assert "notice_period" in answers
        assert "visa_status" in answers
        assert "expected_salary" in answers
        assert "oracle_fusion_experience" in answers
        assert "screening_question_defaults" in answers

    def test_load_sources(self):
        """Sources config loads with source list."""
        sources = load_sources()
        assert "sources" in sources
        assert len(sources["sources"]) > 0

        # Check structure of first source
        first = sources["sources"][0]
        assert "name" in first
        assert "enabled" in first
        assert "search_urls" in first

    def test_get_enabled_sources(self):
        """Only enabled sources are returned."""
        enabled = get_enabled_sources()
        for s in enabled:
            assert s["enabled"] is True

    def test_scoring_weights_sum_to_100(self):
        """Scoring weights should sum to 100."""
        weights = get_scoring_weights()
        assert sum(weights.values()) == 100

    def test_target_titles_not_empty(self):
        """Profile has target titles for matching."""
        profile = load_profile()
        titles = profile["target_titles"]
        assert len(titles) >= 10  # We defined 17 titles
        assert "Senior AR" in titles
        assert "Credit Controller" in titles
