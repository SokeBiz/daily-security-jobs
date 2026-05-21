"""Lever job board scraper."""

import logging
from datetime import datetime, timezone
from typing import Any

from ..utils import fetch_json, strip_html, truncate_text

logger = logging.getLogger(__name__)


def fetch_lever_jobs(company: str) -> list[dict[str, Any]]:
    """Fetch jobs from Lever API for a given company token."""
    url = f"https://api.lever.co/v0/postings/{company}?mode=json"
    data = fetch_json(url)
    if not data or not isinstance(data, list):
        return []

    jobs = []
    for job in data:
        title = job.get("text", "")
        if not title:
            continue
        cats = job.get("categories", {}) or {}
        location = cats.get("location", "") or ""
        department = cats.get("team", "") or ""

        # Lever uses epoch MILLISECONDS
        created_ms = job.get("createdAt")
        published = None
        if created_ms:
            try:
                published = datetime.fromtimestamp(created_ms / 1000, tz=timezone.utc)
            except (ValueError, OSError):
                pass

        jobs.append({
            "company": company,
            "title": title,
            "location": location,
            "department": department,
            "published_at": published,
            "url": job.get("hostedUrl", ""),
            "apply_url": job.get("hostedUrl", ""),
            "description": truncate_text(strip_html(job.get("description", "")), 600),
            "workplace_type": "",
            "is_remote": "remote" in location.lower(),
            "source": "Lever",
        })
    return jobs
