"""Workday job board scraper (PwC, Deloitte, etc.)."""

import json
import logging
import urllib.request
from typing import Any

from ..utils import strip_html, truncate_text

logger = logging.getLogger(__name__)

# Workday career site config: subdomain, wd_number, career_site_path
WORKDAY_SITES: dict[str, dict[str, str]] = {
    "pwc":      {"subdomain": "pwc",       "wd": "wd3",  "path": "Global_Experienced_Careers"},
    "deloitte": {"subdomain": "deloitteie", "wd": "wd3",  "path": "experienced_professionals"},
}


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
    limit = 100
    max_pages = 50

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

            all_jobs.append({
                "company": company,
                "title": title,
                "location": location,
                "department": dept,
                "published_at": None,  # Workday API doesn't expose date
                "url": apply_url,
                "apply_url": apply_url,
                "description": truncate_text(description, 600),
                "workplace_type": "",
                "is_remote": "remote" in location.lower(),
                "source": "Workday",
            })

        total = data.get("total", 0)
        offset += limit
        if offset >= total:
            break

    return all_jobs
