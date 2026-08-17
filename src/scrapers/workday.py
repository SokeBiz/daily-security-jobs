"""Workday job board scraper (PwC, Deloitte, etc.)."""

import json
import logging
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any

from ..utils import strip_html, truncate_text

logger = logging.getLogger(__name__)

# Workday career site config: subdomain, wd_number, career_site_path
WORKDAY_SITES: dict[str, dict[str, str]] = {
    "pwc":      {"subdomain": "pwc",       "wd": "wd3",  "path": "Global_Experienced_Careers"},
    "deloitte": {"subdomain": "deloitteie", "wd": "wd3",  "path": "experienced_professionals"},
}


def _parse_workday_posted_on(posted_on: str | None):
    """Convert Workday's relative 'postedOn' text ('Posted Today',
    'Posted 2 Days Ago') to an approximate UTC datetime, or None."""
    if not posted_on:
        return None
    text = posted_on.strip().lower()
    now = datetime.now(timezone.utc)
    if "today" in text:
        return now
    if "yesterday" in text:
        return now - timedelta(days=1)
    m = re.search(r"(\d+)\s*\+?\s*days?\s+ago", text)
    if m:
        return now - timedelta(days=int(m.group(1)))
    if "this week" in text:
        return now - timedelta(days=3)
    if "last week" in text:
        return now - timedelta(days=10)
    if "month" in text:
        return now - timedelta(days=30)
    return None


def fetch_workday_jobs(company: str) -> list[dict[str, Any]]:
    """Fetch jobs from Workday CXS API for a given company."""
    config = WORKDAY_SITES.get(company)
    if not config:
        return []

    url = (
        f"https://{config['subdomain']}.{config['wd']}.myworkdayjobs.com/"
        f"wday/cxs/{config['subdomain']}/{config['path']}/jobs"
    )

    all_jobs = []
    offset = 0
    limit = 20  # Workday CXS API rejects limit > 20 with HTTP 400
    max_pages = 250

    for _ in range(max_pages):
        payload = {"limit": limit, "offset": offset}
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode(),
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": "DailySecurityJobs/1.0",
                },
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode())
        except Exception:
            break

        jobs = data.get("jobPostings", data.get("jobs", []))
        if not jobs:
            break

        for job in jobs:
            title = job.get("title", "")
            if not title:
                continue

            location = job.get("locationsText", "") or ""
            dept = job.get("jobFamilyText", "") or ""
            external_path = job.get("externalPath", "") or ""
            apply_url = (
                f"https://{config['subdomain']}.{config['wd']}.myworkdayjobs.com/"
                f"en-US/{config['path']}{external_path}"
            )
            description = strip_html(job.get("jobDescription", job.get("description", "")))
            published = _parse_workday_posted_on(job.get("postedOn", ""))

            all_jobs.append({
                "company": company,
                "title": title,
                "location": location,
                "department": dept,
                "published_at": published,
                "url": apply_url,
                "apply_url": apply_url,
                "description": truncate_text(description, 600),
                "workplace_type": "",
                "is_remote": "remote" in location.lower(),
                "source": "Workday",
            })

        # Early stop once we reach jobs posted 30+ days ago (API is newest-first)
        last_posted = (jobs[-1].get("postedOn") or "").lower()
        if "30+" in last_posted or "month" in last_posted:
            break

        total = data.get("total", 0)
        offset += limit
        if offset >= total:
            break

    return all_jobs
