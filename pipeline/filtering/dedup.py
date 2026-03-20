"""Deduplication — removes jobs already seen in the tracker DB."""
from __future__ import annotations
import hashlib
import re

from pipeline.utils.logger import get_logger

log = get_logger(__name__)


def _canonical_id(company: str, title: str, url: str) -> str:
    """Stable fingerprint regardless of field ordering."""
    co = re.sub(r"\s+", " ", company.strip().lower())
    ti = re.sub(r"\s+", " ", title.strip().lower())
    # Normalise URL: strip query params and trailing slashes
    url_clean = re.sub(r"[?#].*", "", url.strip().rstrip("/"))
    key = f"{co}|{ti}|{url_clean}"
    return hashlib.md5(key.encode()).hexdigest()[:12]


def deduplicate(jobs: list[dict], seen_ids: set[str]) -> tuple[list[dict], int]:
    """Remove jobs whose canonical ID is already in *seen_ids*.

    Returns (unique_jobs, duplicate_count).
    """
    unique: list[dict] = []
    dupes = 0
    for job in jobs:
        cid = _canonical_id(
            job.get("company", ""),
            job.get("title", ""),
            job.get("url", ""),
        )
        job["id"] = cid
        if cid in seen_ids:
            dupes += 1
            continue
        seen_ids.add(cid)
        unique.append(job)

    log.info("Dedup: %d unique, %d duplicates removed.", len(unique), dupes)
    return unique, dupes
