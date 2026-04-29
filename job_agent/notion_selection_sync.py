"""Sync selected jobs into the Notion Auto Job Selection Tracker."""
from __future__ import annotations

import os
from datetime import date, timedelta
from typing import Any

import requests


NOTION_API_VERSION = "2022-06-28"


class NotionSyncError(RuntimeError):
    pass


def _headers() -> dict[str, str]:
    token = os.getenv("NOTION_API_KEY", "").strip()
    if not token:
        raise NotionSyncError("Missing NOTION_API_KEY secret.")
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_API_VERSION,
        "Content-Type": "application/json",
    }


def _database_id() -> str:
    database_id = os.getenv("NOTION_DATABASE_ID", "").strip()
    if not database_id:
        raise NotionSyncError("Missing NOTION_DATABASE_ID secret.")
    return database_id


def _rich_text(value: str, max_len: int = 1900) -> dict[str, Any]:
    return {"rich_text": [{"text": {"content": (value or "")[:max_len]}}]}


def _title(value: str) -> dict[str, Any]:
    return {"title": [{"text": {"content": value[:200] or "Untitled Job"}}]}


def _select(value: str | None) -> dict[str, Any]:
    return {"select": {"name": value} if value else None}


def _url(value: str | None) -> dict[str, Any]:
    return {"url": value or None}


def _number(value: int | float | None) -> dict[str, Any]:
    return {"number": value}


def _checkbox(value: bool) -> dict[str, Any]:
    return {"checkbox": value}


def _date(value: str | None) -> dict[str, Any]:
    return {"date": {"start": value} if value else None}


def build_notion_properties(job: Any, scored: dict[str, Any]) -> dict[str, Any]:
    today = date.today()
    follow_up = today + timedelta(days=3)
    return {
        "Job": _title(job.title),
        "Company": _rich_text(job.company),
        "Source": _select(job.source),
        "Location": _select(_normalize_location(job.location)),
        "Job Link": _url(job.link),
        "Real Role Type": _select(scored.get("real_role_type") or "Skip"),
        "Match Score": _number(scored.get("match_score")),
        "Priority": _select(scored.get("priority") or "Skip"),
        "Recommended CV": _select(scored.get("recommended_cv") or "Senior AR/O2C CV"),
        "Status": _select(scored.get("status") or "Scored"),
        "ATS Keywords": _rich_text(", ".join(scored.get("ats_keywords", []))),
        "Matched Skills": _rich_text(", ".join(scored.get("matched_skills", []))),
        "Missing Gaps": _rich_text(", ".join(scored.get("missing_gaps", []))),
        "Next Action": _select(scored.get("next_action") or "Apply"),
        "Applied": _checkbox(False),
        "date:Date Found:start": _date(today.isoformat()),
        "date:Follow Up Date:start": _date(follow_up.isoformat()),
    }


def _normalize_location(location: str) -> str:
    text = (location or "").lower()
    if "abu dhabi" in text:
        return "Abu Dhabi"
    if "sharjah" in text:
        return "Sharjah"
    if "dubai" in text:
        return "Dubai"
    if "gcc" in text:
        return "GCC"
    return "UAE"


def create_job_page(job: Any, scored: dict[str, Any]) -> str:
    payload = {
        "parent": {"database_id": _database_id()},
        "properties": build_notion_properties(job, scored),
        "children": [
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": [{"type": "text", "text": {"content": "AI Job Match Summary"}}]},
            },
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": _summary_text(job, scored)}}]},
            },
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Recruiter Message"}}]},
            },
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": scored.get("recruiter_message", "")[:1900]}}]},
            },
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Hiring Manager Message"}}]},
            },
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": scored.get("hiring_manager_message", "")[:1900]}}]},
            },
        ],
    }
    response = requests.post("https://api.notion.com/v1/pages", headers=_headers(), json=payload, timeout=30)
    if response.status_code >= 400:
        raise NotionSyncError(f"Notion create page failed: {response.status_code} {response.text}")
    return response.json().get("url", "")


def _summary_text(job: Any, scored: dict[str, Any]) -> str:
    return (
        f"Company: {job.company}\n"
        f"Source: {job.source}\n"
        f"Location: {job.location}\n"
        f"Match Score: {scored.get('match_score')}\n"
        f"Priority: {scored.get('priority')}\n"
        f"Recommended CV: {scored.get('recommended_cv')}\n"
        f"Decision: {scored.get('apply_decision')}\n"
        f"Job Link: {job.link}"
    )
