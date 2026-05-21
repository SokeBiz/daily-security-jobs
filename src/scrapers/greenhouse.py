"""Greenhouse job board scraper."""

import logging
from typing import Any

from ..utils import fetch_json, parse_iso_timestamp, strip_html, truncate_text

logger = logging.getLogger(__name__)


def fetch_greenhouse_jobs(company: str) -> list[dict[str, Any]]:
    """Fetch jobs from Greenhouse API for a given company board token."""
    url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true"
    data = fetch_json(url)
    if not data or "jobs" not in data:
        return []

    jobs = []
    for job in data["jobs"]:
        published = parse_iso_timestamp(job.get("first_published"))
        if not published:
            published = parse_iso_timestamp(job.get("updated_at"))

        location = (
            job.get("location", {}).get("name", "")
            if isinstance(job.get("location"), dict)
            else str(job.get("location", ""))
        )
        title = job.get("title", "")
        dept_list = job.get("departments", [])
        dept_names = [d.get("name", "") for d in dept_list if isinstance(d, dict)]
        department = " / ".join(dept_names)

        offices = job.get("offices", [])
        office_names = [o.get("name", "") for o in offices if isinstance(o, dict)]
        if office_names:
            location = f"{location}; {', '.join(office_names)}" if location else ", ".join(office_names)

        content = strip_html(job.get("content", ""))

        jobs.append({
            "company": company,
            "title": title,
            "location": location,
            "department": department,
            "published_at": published,
            "url": job.get("absolute_url", ""),
            "apply_url": job.get("absolute_url", ""),
            "description": truncate_text(content, 600),
            "workplace_type": "",
            "is_remote": "remote" in location.lower(),
            "source": "Greenhouse",
        })
    return jobs
