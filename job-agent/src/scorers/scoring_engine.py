"""Weighted scoring engine for job relevance.

Evaluates each job against the target profile using configurable
weights across multiple dimensions: title relevance, keyword match,
location, salary, seniority, and ERP/skill match.
"""

import re
from typing import Optional

from src.utils.config_loader import load_profile, load_rules, get_scoring_weights
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ScoringEngine:
    """Weighted multi-factor scoring engine.

    Scores jobs on a 0-100 scale based on configurable weights.
    Each factor is scored 0-100, then multiplied by its weight
    and summed to produce the final score.
    """

    def __init__(self, profile: Optional[dict] = None, rules: Optional[dict] = None):
        """Initialize with profile and rules config.

        Args:
            profile: Candidate profile. Loaded from config if None.
            rules: Scoring rules. Loaded from config if None.
        """
        self.profile = profile or load_profile()
        self.rules = rules or load_rules()
        self.weights = get_scoring_weights()

        self.target_titles = [t.lower() for t in self.profile.get("target_titles", [])]
        self.excluded_titles = [t.lower() for t in self.profile.get("excluded_titles", [])]
        self.preferred_locations = [loc.lower() for loc in self.profile.get("preferred_locations", [])]
        self.salary_floor = self.rules.get("salary_floor", 14000)
        self.include_keywords = [k.lower() for k in self.rules.get("include_keywords", [])]
        self.exclude_keywords = [k.lower() for k in self.rules.get("exclude_keywords", [])]
        self.accepted_seniority = [s.lower() for s in self.rules.get("seniority_levels_accepted", [])]
        self.rejected_seniority = [s.lower() for s in self.rules.get("seniority_levels_rejected", [])]

        # Compile regex patterns from rules
        self.title_include_patterns = [
            re.compile(p) for p in self.rules.get("title_include_patterns", [])
        ]
        self.title_exclude_patterns = [
            re.compile(p) for p in self.rules.get("title_exclude_patterns", [])
        ]

    def score_job(self, job: dict) -> tuple[float, str]:
        """Score a job against the target profile.

        Args:
            job: Job dict with at minimum: title, normalized_title, location,
                 salary_min, salary_max, description, apply_type.
                 May include 'metadata' with 'keywords' and 'seniority'.

        Returns:
            Tuple of (score, reason_summary) where score is 0-100.
        """
        reasons = []
        scores = {}

        title = (job.get("normalized_title") or job.get("title", "")).lower()
        description = (job.get("description") or "").lower()
        location = (job.get("location") or "").lower()
        metadata = job.get("metadata", {})
        keywords = metadata.get("keywords", [])
        seniority = metadata.get("seniority")

        # 1. Title relevance (weight: title_relevance)
        title_score = self._score_title(title)
        scores["title_relevance"] = title_score
        if title_score >= 80:
            reasons.append(f"Strong title match ({title_score})")
        elif title_score >= 40:
            reasons.append(f"Partial title match ({title_score})")
        elif title_score == 0:
            reasons.append("No title match")

        # 2. Keyword match (weight: keyword_match)
        keyword_score = self._score_keywords(keywords, title, description)
        scores["keyword_match"] = keyword_score
        if keyword_score >= 60:
            reasons.append(f"Good keyword match ({len(keywords)} keywords)")
        elif keyword_score > 0:
            reasons.append(f"Some keywords matched ({len(keywords)})")

        # 3. Location match (weight: location_match)
        location_score = self._score_location(location)
        scores["location_match"] = location_score
        if location_score >= 80:
            reasons.append("Preferred location")
        elif location_score >= 40:
            reasons.append("Acceptable location")
        elif location_score == 0:
            reasons.append("Location mismatch or unknown")

        # 4. Salary fit (weight: salary_fit)
        salary_score = self._score_salary(job.get("salary_min"), job.get("salary_max"))
        scores["salary_fit"] = salary_score
        if salary_score >= 80:
            reasons.append("Salary meets threshold")
        elif salary_score == 50:
            reasons.append("Salary not disclosed")
        elif salary_score < 50:
            reasons.append("Salary below threshold")

        # 5. Seniority fit (weight: seniority_fit)
        seniority_score = self._score_seniority(seniority, title)
        scores["seniority_fit"] = seniority_score
        if seniority_score >= 80:
            reasons.append("Seniority level matches")
        elif seniority_score == 0:
            reasons.append("Wrong seniority level")

        # 6. ERP/skill match (weight: erp_skill_match)
        erp_score = self._score_erp_skills(keywords, description)
        scores["erp_skill_match"] = erp_score
        if erp_score >= 60:
            reasons.append("ERP/skill keywords present")

        # Calculate weighted total
        total = 0.0
        for factor, weight in self.weights.items():
            factor_score = scores.get(factor, 50)  # default 50 if missing
            total += (factor_score / 100) * weight

        # Apply penalty for excluded title patterns
        if self._matches_excluded_title(title):
            total = min(total, 20)
            reasons.append("EXCLUDED: title matches reject pattern")

        # Apply penalty for excluded keywords in description
        if self._has_excluded_keywords(title + " " + description):
            total = max(0, total - 20)
            reasons.append("Penalty: excluded keywords found")

        total = round(max(0, min(100, total)), 1)
        reason_summary = " | ".join(reasons)

        logger.debug(
            "Scored job: title='%s' score=%.1f factors=%s",
            job.get("title", "?"), total, scores,
        )

        return total, reason_summary

    def _score_title(self, title: str) -> float:
        """Score title relevance against target titles."""
        # Check for regex pattern matches first
        for pattern in self.title_include_patterns:
            if pattern.search(title):
                return 100

        # Direct match against target titles
        for target in self.target_titles:
            if target in title:
                return 100

        # Partial matching
        partial_score = 0
        title_words = set(title.split())
        for target in self.target_titles:
            target_words = set(target.split())
            overlap = title_words & target_words
            if overlap:
                match_ratio = len(overlap) / len(target_words)
                partial_score = max(partial_score, match_ratio * 70)

        return round(partial_score)

    def _score_keywords(self, extracted_keywords: list[str], title: str, description: str) -> float:
        """Score keyword presence in job data."""
        if not self.include_keywords:
            return 50

        text = title + " " + description
        matched = 0
        for kw in self.include_keywords:
            if kw in text:
                matched += 1

        # Also count pre-extracted keywords
        matched += len(extracted_keywords)

        # Normalize: 5+ matches = 100
        max_keywords = 5
        score = min(100, (matched / max_keywords) * 100)
        return round(score)

    def _score_location(self, location: str) -> float:
        """Score location preference match."""
        if not location:
            return 30  # Unknown location, small default

        for preferred in self.preferred_locations:
            if preferred in location:
                # Dubai gets top score
                if "dubai" in location:
                    return 100
                return 80

        # UAE general
        if "uae" in location or "united arab emirates" in location:
            return 60

        # Remote
        if "remote" in location:
            return 50

        return 10  # Other location

    def _score_salary(self, salary_min: Optional[float], salary_max: Optional[float]) -> float:
        """Score salary against the threshold."""
        if salary_min is None and salary_max is None:
            return 50  # No salary info – neutral

        effective_salary = salary_max or salary_min or 0

        if effective_salary >= self.salary_floor:
            # Higher salary = better score
            ratio = effective_salary / self.salary_floor
            return min(100, round(60 + ratio * 20))

        # Below floor
        ratio = effective_salary / self.salary_floor if self.salary_floor > 0 else 0
        return max(0, round(ratio * 50))

    def _score_seniority(self, seniority: Optional[str], title: str) -> float:
        """Score seniority level fit."""
        if not seniority:
            # Try to infer from title
            for level in self.rejected_seniority:
                if level in title:
                    return 0
            return 50  # Unknown, neutral

        if seniority in [s.replace(" ", "_") for s in self.accepted_seniority]:
            return 100

        if seniority in [s.replace(" ", "_") for s in self.rejected_seniority]:
            return 0

        return 50  # Neutral

    def _score_erp_skills(self, keywords: list[str], description: str) -> float:
        """Score ERP and collections skill match."""
        erp_keywords = {"oracle", "sap", "erp"}
        collections_keywords = {
            "reconciliation", "aging", "dunning", "dso",
            "dispute_resolution", "cash_application", "collections",
            "credit_control", "bad_debt",
        }

        keyword_set = set(keywords)
        erp_match = bool(keyword_set & erp_keywords)
        collections_match = keyword_set & collections_keywords

        score = 0
        if erp_match:
            score += 50
        if collections_match:
            score += min(50, len(collections_match) * 15)

        # Also check description directly
        if "oracle" in description or "sap" in description:
            score = max(score, 40)

        return min(100, score)

    def _matches_excluded_title(self, title: str) -> bool:
        """Check if title matches any exclusion pattern."""
        for pattern in self.title_exclude_patterns:
            if pattern.search(title):
                return True

        for excluded in self.excluded_titles:
            if excluded in title:
                return True

        return False

    def _has_excluded_keywords(self, text: str) -> bool:
        """Check if text contains excluded keywords."""
        text_lower = text.lower()
        for kw in self.exclude_keywords:
            if kw in text_lower:
                return True
        return False


def score_job(job: dict, profile: Optional[dict] = None, rules: Optional[dict] = None) -> tuple[float, str]:
    """Convenience function to score a single job.

    Args:
        job: Job dict with standard fields.
        profile: Optional profile override.
        rules: Optional rules override.

    Returns:
        Tuple of (score, reason_summary).
    """
    engine = ScoringEngine(profile=profile, rules=rules)
    return engine.score_job(job)
