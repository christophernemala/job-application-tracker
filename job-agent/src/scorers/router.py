"""Job routing logic.

Determines the action path for each job based on its score,
apply type, and other factors. Routes to:
- auto_apply: High score + simple apply flow
- semi_auto: Good score + moderate complexity
- manual_review: Needs human review
- reject: Poor fit
"""

from src.utils.config_loader import load_rules
from src.utils.logger import get_logger

logger = get_logger(__name__)


def route_job(job: dict, rules: dict | None = None) -> str:
    """Determine the routing action for a scored job.

    Args:
        job: Job dict with score, apply_type, and metadata.
        rules: Optional rules override. Loaded from config if None.

    Returns:
        Route status: 'auto_apply', 'semi_auto', 'manual_review', or 'reject'.
    """
    if rules is None:
        rules = load_rules()

    score = job.get("score", 0)
    apply_type = job.get("apply_type", "unknown")
    metadata = job.get("metadata", {})
    seniority = metadata.get("seniority")
    score_reason = job.get("score_reason", "")

    min_auto = rules.get("min_score_for_auto_apply", 80)
    min_semi = rules.get("min_score_for_semi_auto", 60)
    min_review = rules.get("min_score_for_manual_review", 40)

    # Reject: low score or excluded
    if score < min_review:
        logger.info(
            "REJECT: score=%.1f below min_review=%d title='%s'",
            score, min_review, job.get("title", "?"),
        )
        return "reject"

    if "EXCLUDED" in score_reason:
        logger.info(
            "REJECT: excluded pattern in title='%s'", job.get("title", "?"),
        )
        return "reject"

    # Manual review: manager+ roles, complex ATS, or borderline scores
    if score < min_semi:
        logger.info(
            "MANUAL_REVIEW: score=%.1f below semi threshold title='%s'",
            score, job.get("title", "?"),
        )
        return "manual_review"

    # Manager-level roles always get manual review
    if seniority in ("manager", "director"):
        logger.info(
            "MANUAL_REVIEW: seniority=%s title='%s'",
            seniority, job.get("title", "?"),
        )
        return "manual_review"

    # Complex ATS always gets manual review
    if apply_type == "external_complex":
        logger.info(
            "MANUAL_REVIEW: complex ATS apply_type=%s title='%s'",
            apply_type, job.get("title", "?"),
        )
        return "manual_review"

    # Unknown apply type gets manual review
    if apply_type == "unknown":
        logger.info(
            "MANUAL_REVIEW: unknown apply type title='%s'",
            job.get("title", "?"),
        )
        return "manual_review"

    # Auto-apply: high score + simple apply flow
    if score >= min_auto and apply_type in ("easy_apply", "internal"):
        logger.info(
            "AUTO_APPLY: score=%.1f apply_type=%s title='%s'",
            score, apply_type, job.get("title", "?"),
        )
        return "auto_apply"

    # Semi-auto: good score, some complexity
    if score >= min_semi:
        if apply_type in ("easy_apply", "internal"):
            # Good score but not quite auto threshold
            logger.info(
                "SEMI_AUTO: score=%.1f apply_type=%s title='%s'",
                score, apply_type, job.get("title", "?"),
            )
            return "semi_auto"

        if apply_type == "external_simple":
            logger.info(
                "SEMI_AUTO: score=%.1f external_simple title='%s'",
                score, job.get("title", "?"),
            )
            return "semi_auto"

    # Default to manual review
    return "manual_review"


def route_jobs(jobs: list[dict], rules: dict | None = None) -> dict[str, list[dict]]:
    """Route a batch of scored jobs.

    Args:
        jobs: List of job dicts with scores.
        rules: Optional rules override.

    Returns:
        Dict with route_status keys mapping to lists of jobs.
    """
    if rules is None:
        rules = load_rules()

    routed = {
        "auto_apply": [],
        "semi_auto": [],
        "manual_review": [],
        "reject": [],
    }

    for job in jobs:
        route = route_job(job, rules)
        job["route_status"] = route
        routed[route].append(job)

    logger.info(
        "Routing results: auto_apply=%d semi_auto=%d manual_review=%d reject=%d",
        len(routed["auto_apply"]),
        len(routed["semi_auto"]),
        len(routed["manual_review"]),
        len(routed["reject"]),
    )

    return routed
