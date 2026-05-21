"""Amazon Jobs scraper."""

import logging
from datetime import datetime, timezone
from typing import Any

from ..utils import fetch_json, strip_html, truncate_text

logger = logging.getLogger(__name__)

EU_COUNTRIES = [
    "DE", "NL", "IE", "FR", "IT", "ES", "PL", "AT",
    "CZ", "DK", "FI", "SE", "NO", "CH",
]


def fetch_amazon_jobs(company: str) -> list[dict[str, Any]]:
    """Fetch jobs from Amazon Jobs API searching across EU countries."""
    seen_ids: set[str] = set()
    all_jobs = []

    for country in EU_COUNTRIES:
        url = (
            f"https://www.amazon.jobs/en/search.json?"
            f"offset=0&result_limit=100&sort=recent"
            f"&country[]={country}"
        )
        data = fetch_json(url)
        if not data or "jobs" not in data:
            continue
        for job in data["jobs"]:
            job_id = job.get("id", "")
            if not job_id or job_id in seen_ids:
                continue
            seen_ids.add(job_id)

            title = job.get("title", "")
            if not title:
                continue
            location = job.get("location", "")
            posted_str = job.get("posted_date", "")
            description = strip_html(job.get("description_short", ""))

            published = None
            if posted_str:
                try:
                    published = datetime.strptime(posted_str, "%B %d, %Y").replace(tzinfo=timezone.utc)
                except ValueError:
                    pass

            apply_url = f"https://www.amazon.jobs/en/jobs/{job_id}" if job_id else ""

            all_jobs.append({
                "company": "amazon",
                "title": title,
                "location": location,
                "department": "",
                "published_at": published,
                "url": apply_url,
                "apply_url": apply_url,
                "description": truncate_text(description, 600),
                "workplace_type": "",
                "is_remote": "remote" in location.lower() or "virtual" in location.lower(),
                "source": "Amazon",
            })
    return all_jobs
