"""Ashby job board scraper."""

import logging
from typing import Any

from ..utils import fetch_json, parse_iso_timestamp, strip_html

logger = logging.getLogger(__name__)


def fetch_ashby_jobs(company: str) -> list[dict[str, Any]]:
    """Fetch jobs from Ashby API for a given company token."""
    url = f"https://api.ashbyhq.com/posting-api/job-board/{company}?includeCompensation=true"
    data = fetch_json(url)
    if not data or "jobs" not in data:
        return []

    jobs = []
    for job in data["jobs"]:
        if not job.get("isListed", True):
            continue

        published = parse_iso_timestamp(job.get("publishedAt"))
        title = job.get("title", "")
        location = job.get("location", "")

        # Handle secondaryLocations (strings or dicts)
        sec_locs_raw = job.get("secondaryLocations", [])
        sec_strs = []
        for sl in sec_locs_raw:
            if isinstance(sl, str):
                sec_strs.append(sl)
            elif isinstance(sl, dict):
                sec_strs.append(sl.get("name", str(sl)))
            else:
                sec_strs.append(str(sl))
        full_location = location
        if sec_strs:
            full_location += "; " + ", ".join(sec_strs)

        workplace = (job.get("workplaceType") or "").lower()
        is_remote = job.get("isRemote", False) or workplace == "remote"
        if is_remote and "remote" not in full_location.lower():
            full_location = "Remote, " + full_location

        department = job.get("department", "")
        team = job.get("team", "")
        dept_text = f"{department} {team}".strip()

        jobs.append({
            "company": company,
            "title": title,
            "location": full_location,
            "department": dept_text,
            "published_at": published,
            "url": job.get("jobUrl", ""),
            "apply_url": job.get("applyUrl", ""),
            "description": strip_html(job.get("descriptionHtml", "")),
            "workplace_type": job.get("workplaceType", ""),
            "is_remote": is_remote,
            "source": "Ashby",
        })
    return jobs
