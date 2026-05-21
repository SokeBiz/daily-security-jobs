"""Personio job board scraper."""

import logging
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any

from ..utils import parse_iso_timestamp, strip_html, truncate_text

logger = logging.getLogger(__name__)


def fetch_personio_jobs(company: str) -> list[dict[str, Any]]:
    """Fetch jobs from Personio XML feed for a given company."""
    url = f"https://{company}.jobs.personio.de/xml?language=en"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "DailySecurityJobs/1.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            xml_data = resp.read().decode()
    except Exception:
        return []

    jobs = []
    try:
        root = ET.fromstring(xml_data)
        for pos in root.findall("position"):
            title_el = pos.find("name")
            if title_el is None or not title_el.text:
                continue
            title = title_el.text
            office = pos.findtext("office", "")
            dept = pos.findtext("department", "")
            created_str = pos.findtext("createdAt", "")
            published = parse_iso_timestamp(created_str) if created_str else None

            description = ""
            descs = pos.find("jobDescriptions")
            if descs is not None:
                parts = []
                for jd in descs.findall("jobDescription"):
                    val = jd.findtext("value", "")
                    if val:
                        parts.append(strip_html(val))
                description = " ".join(parts)

            apply_url = f"https://{company}.jobs.personio.de"
            jobs.append({
                "company": company,
                "title": title,
                "location": office,
                "department": dept,
                "published_at": published,
                "url": apply_url,
                "apply_url": apply_url,
                "description": truncate_text(description, 600),
                "workplace_type": "",
                "is_remote": "remote" in office.lower(),
                "source": "Personio",
            })
    except ET.ParseError:
        pass

    return jobs
