"""Recruitee job board scraper."""

import logging
from typing import Any

from ..utils import fetch_json, parse_iso_timestamp, strip_html, truncate_text

logger = logging.getLogger(__name__)


def fetch_recruitee_jobs(company: str) -> list[dict[str, Any]]:
    """Fetch jobs from Recruitee API for a given company."""
    url = f"https://{company}.recruitee.com/api/offers"
    data = fetch_json(url)
    if not data or "offers" not in data:
        return []

    jobs = []
    for offer in data["offers"]:
        title = offer.get("title", "")
        if not title:
            continue

        published = None
        published_str = offer.get("published_at")
        if published_str:
            published = parse_iso_timestamp(published_str)

        location = offer.get("office", "") or ""
        if isinstance(location, dict):
            location = location.get("name", "")
        elif isinstance(location, list):
            location = ", ".join(str(l) for l in location)

        department = offer.get("department", "") or ""
        if isinstance(department, dict):
            department = department.get("name", "")

        description = strip_html(offer.get("description", ""))

        apply_url = f"https://{company}.recruitee.com"
        for link in offer.get("links", []):
            if isinstance(link, dict) and link.get("type") == "apply":
                apply_url = link.get("url", apply_url)
                break

        jobs.append({
            "company": company,
            "title": title,
            "location": str(location),
            "department": str(department),
            "published_at": published,
            "url": apply_url,
            "apply_url": apply_url,
            "description": truncate_text(description, 600),
            "workplace_type": "",
            "is_remote": "remote" in str(location).lower(),
            "source": "Recruitee",
        })
    return jobs
