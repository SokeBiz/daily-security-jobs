"""
Accenture Job Scraper

Accenture uses Workday (wd103) as their ATS with a custom AEM frontend.
Two-step approach:
  1. Workday CXS API -> job listings (title, ID, location)
  2. Accenture.com jobdetails pages -> JSON-LD structured data (full details)
"""

import json
import logging
import re
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────

WORKDAY_TENANT = "accenture"
WORKDAY_SITE = "AccentureCareers"
WORKDAY_SERVER = "wd103"
WORKDAY_URL = (
    f"https://{WORKDAY_TENANT}.{WORKDAY_SERVER}.myworkdayjobs.com"
    f"/wday/cxs/{WORKDAY_TENANT}/{WORKDAY_SITE}/jobs"
)

LOCALES = {
    "us-en": "https://www.accenture.com/us-en/careers/jobdetails?id={req_id}",
    "gb-en": "https://www.accenture.com/gb-en/careers/jobdetails?id={req_id}",
    "in-en": "https://www.accenture.com/in-en/careers/jobdetails?id={req_id}",
    "de-de": "https://www.accenture.com/de-de/careers/jobdetails?id={req_id}",
    "fr-fr": "https://www.accenture.com/fr-fr/careers/jobdetails?id={req_id}",
    "es-es": "https://www.accenture.com/es-es/careers/jobdetails?id={req_id}",
}

DEFAULT_LOCALE = "us-en"
REQUEST_TIMEOUT = 30
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Content-Type": "application/json",
}
MAX_CONSECUTIVE_FAILURES = 10
REQUEST_DELAY = 0.5


# ── Data Models ────────────────────────────────────────────────────────────

@dataclass
class AccentureJob:
    """Normalized Accenture job posting."""
    req_id: str
    title: str
    location: str
    posted_on: str
    external_path: str
    description: str = ""
    qualifications: str = ""
    responsibilities: str = ""
    employment_type: str = ""
    date_posted: str = ""
    valid_through: str = ""
    skills: list[str] = field(default_factory=list)
    locations_detailed: list[dict] = field(default_factory=list)
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: str = ""
    experience_months: str = ""
    raw_jsonld: dict = field(default_factory=dict)
    source: str = "accenture"
    scraped_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ── Workday Listings API ───────────────────────────────────────────────────

def fetch_job_listings(
    limit: int = 20,
    offset: int = 0,
    applied_facets: dict | None = None,
    search_text: str = "",
) -> dict:
    """Fetch a page of job listings from the Workday CXS API."""
    payload = {
        "limit": limit,
        "offset": offset,
        "appliedFacets": applied_facets or {},
        "searchText": search_text,
    }
    resp = requests.post(
        WORKDAY_URL,
        json=payload,
        headers=DEFAULT_HEADERS,
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def iter_all_jobs(
    limit: int = 20,
    applied_facets: dict | None = None,
    search_text: str = "",
    max_jobs: int = 2000,
) -> list[dict]:
    """Iterate over ALL job listings via pagination."""
    all_jobs = []
    offset = 0
    failures = 0

    while True:
        try:
            data = fetch_job_listings(
                limit=limit,
                offset=offset,
                applied_facets=applied_facets,
                search_text=search_text,
            )
            failures = 0
            job_postings = data.get("jobPostings", [])
            if not job_postings:
                break

            for job in job_postings:
                req_id = job.get("bulletFields", [None])[0]
                location = (
                    job.get("bulletFields", ["", ""])[1]
                    if len(job.get("bulletFields", [])) > 1
                    else ""
                )
                all_jobs.append({
                    "req_id": req_id,
                    "title": job.get("title", ""),
                    "location": location,
                    "posted_on": job.get("postedOn", ""),
                    "external_path": job.get("externalPath", ""),
                })
                if len(all_jobs) >= max_jobs:
                    return all_jobs

            if len(job_postings) < limit:
                break
            offset += limit

        except requests.RequestException as e:
            failures += 1
            logger.warning("Failed to fetch page at offset %d: %s", offset, e)
            if failures >= MAX_CONSECUTIVE_FAILURES:
                logger.error("Too many consecutive failures, aborting pagination")
                break
            continue

    return all_jobs


# ── JSON-LD Extraction ─────────────────────────────────────────────────────

def extract_job_jsonld(html: str) -> dict | None:
    """Extract the JobPosting JSON-LD from an Accenture job details page."""
    pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
    matches = re.findall(pattern, html, re.DOTALL)
    for match in matches:
        try:
            data = json.loads(match)
            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict) and item.get("@type") == "JobPosting":
                    return item
        except json.JSONDecodeError:
            continue
    return None


def parse_salary(jsonld: dict) -> tuple:
    """Extract salary info from JSON-LD."""
    try:
        base = jsonld.get("baseSalary", {})
        if base.get("@type") == "MonetaryAmount":
            currency = base.get("currency", "")
            value = base.get("value", {})
            if isinstance(value, dict) and value.get("@type") == "QuantitativeValue":
                min_val = value.get("minValue") or value.get("value")
                max_val = value.get("maxValue") or value.get("value")
                return (
                    float(min_val) if min_val and min_val != "unavailable" else None,
                    float(max_val) if max_val and max_val != "unavailable" else None,
                    currency if currency != "unavailable" else "",
                )
    except (TypeError, ValueError):
        pass
    return (None, None, "")


def fetch_job_details(
    req_id: str,
    locale: str = DEFAULT_LOCALE,
) -> AccentureJob | None:
    """Fetch full job details from Accenture's jobdetails page using JSON-LD."""
    url_variants = [
        LOCALES[locale].format(req_id=f"{req_id}_en"),
        LOCALES[locale].format(req_id=req_id),
    ]

    jsonld = None
    used_url = None

    for url in url_variants:
        try:
            resp = requests.get(
                url,
                headers={
                    "User-Agent": DEFAULT_HEADERS["User-Agent"],
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                },
                timeout=REQUEST_TIMEOUT,
            )
            if resp.status_code == 200:
                jsonld = extract_job_jsonld(resp.text)
                if jsonld:
                    used_url = url
                    break
        except requests.RequestException:
            continue

    if not jsonld:
        logger.debug("No JSON-LD found for job %s at %s", req_id, locale)
        return None

    identifier = jsonld.get("identifier", {})
    req_id_out = (
        identifier.get("value", req_id) if isinstance(identifier, dict) else req_id
    )

    locations = jsonld.get("jobLocation", [])
    if isinstance(locations, dict):
        locations = [locations]

    location_names = []
    for loc in locations:
        addr = loc.get("address", {})
        city = addr.get("addressLocality", "")
        region = addr.get("addressRegion", "")
        country = addr.get("addressCountry", "")
        parts = [p for p in [city, region, country] if p]
        location_names.append(", ".join(parts))

    salary_min, salary_max, salary_currency = parse_salary(jsonld)
    experience = jsonld.get("experienceRequirements", {})
    exp_months = (
        experience.get("monthsOfExperience", "")
        if isinstance(experience, dict)
        else ""
    )

    return AccentureJob(
        req_id=req_id_out,
        title=jsonld.get("title", ""),
        location=location_names[0] if location_names else "",
        posted_on=jsonld.get("datePosted", ""),
        external_path=used_url or "",
        description=jsonld.get("description", ""),
        qualifications=jsonld.get("qualifications", ""),
        responsibilities=jsonld.get("responsibilities", ""),
        employment_type=jsonld.get("employmentType", ""),
        date_posted=jsonld.get("datePosted", ""),
        valid_through=jsonld.get("validThrough", ""),
        skills=jsonld.get("skills", []),
        locations_detailed=locations,
        salary_min=salary_min,
        salary_max=salary_max,
        salary_currency=salary_currency,
        experience_months=str(exp_months),
        raw_jsonld=jsonld,
    )


# ── Full Scraping Pipeline ─────────────────────────────────────────────────

def scrape_accenture_jobs(
    locale: str = DEFAULT_LOCALE,
    max_listing_jobs: int = 100,
    max_detail_jobs: int = 30,
    search_text: str = "security",
    filter_skills: list[str] | None = None,
    filter_area: str | None = None,
    delay: float = REQUEST_DELAY,
) -> list[AccentureJob]:
    """Complete scraping pipeline: listings -> details."""
    applied_facets = {}
    if filter_area:
        facets_data = fetch_job_listings(limit=1, offset=0)
        for facet in facets_data.get("facets", []):
            if facet.get("descriptor") == "Area of Work":
                for val in facet.get("values", []):
                    if val.get("descriptor", "").lower() == filter_area.lower():
                        applied_facets["jobFamilyGroup"] = [val["id"]]
                        break

    logger.info("Fetching job listings from Workday API...")
    listings = iter_all_jobs(
        limit=20,
        applied_facets=applied_facets,
        search_text=search_text,
        max_jobs=max_listing_jobs,
    )
    logger.info("Found %d job listings", len(listings))

    listings = listings[:max_detail_jobs]
    results = []
    failures = 0

    for i, listing in enumerate(listings):
        req_id = listing["req_id"]
        if not req_id:
            continue

        try:
            job = fetch_job_details(req_id, locale=locale)
            if job:
                if not job.location:
                    job.location = listing.get("location", "")
                if not job.posted_on:
                    job.posted_on = listing.get("posted_on", "")
                if not job.external_path:
                    job.external_path = listing.get("external_path", "")

                if filter_skills:
                    job_skills_lower = [s.lower() for s in job.skills]
                    if not any(fs.lower() in job_skills_lower for fs in filter_skills):
                        continue

                results.append(job)
                failures = 0
            else:
                logger.warning("No details for %s, using listing data", req_id)
                results.append(AccentureJob(
                    req_id=req_id,
                    title=listing.get("title", ""),
                    location=listing.get("location", ""),
                    posted_on=listing.get("posted_on", ""),
                    external_path=listing.get("external_path", ""),
                ))
                failures = 0

        except Exception as e:
            failures += 1
            logger.warning("Error fetching details for %s: %s", req_id, e)
            if failures >= MAX_CONSECUTIVE_FAILURES:
                logger.error("Too many consecutive failures, aborting detail fetch")
                break
            continue

        time.sleep(delay)

    logger.info("Successfully scraped %d Accenture jobs", len(results))
    return results


def get_available_facets() -> list[dict]:
    """Get available filter facets from the Workday API."""
    data = fetch_job_listings(limit=1, offset=0)
    return data.get("facets", [])


def list_areas_of_work() -> list[tuple[str, int]]:
    """List available areas of work with job counts."""
    for facet in get_available_facets():
        if facet.get("descriptor") == "Area of Work":
            return [(v["descriptor"], v["count"]) for v in facet.get("values", [])]
    return []


# ── Wrapper for Main Pipeline ──────────────────────────────────────────────

def fetch_accenture_jobs(company: str) -> list[dict[str, Any]]:
    """Fetch Accenture jobs and return normalized dicts for the pipeline."""
    from ..utils import parse_iso_timestamp, strip_html, truncate_text

    try:
        results = scrape_accenture_jobs(
            locale="gb-en",
            max_listing_jobs=100,
            max_detail_jobs=30,
            search_text="security",
        )
    except Exception as e:
        logger.error("Accenture scraper error: %s", e)
        return []

    jobs = []
    for aj in results:
        title = aj.title if isinstance(aj.title, str) else getattr(aj, "title", "")
        if not title:
            continue

        published = None
        date_str = (
            aj.date_posted
            if hasattr(aj, "date_posted") and aj.date_posted
            else (aj.posted_on if hasattr(aj, "posted_on") and aj.posted_on else "")
        )
        if date_str:
            published = parse_iso_timestamp(date_str)

        location = aj.location if hasattr(aj, "location") and aj.location else ""
        location = re.sub(r",?\s*unavailable", "", location, flags=re.IGNORECASE).strip(", ")

        external_path = aj.external_path if hasattr(aj, "external_path") and aj.external_path else ""
        apply_url = (
            external_path
            or (
                f"https://www.accenture.com/gb-en/careers/jobdetails?id={aj.req_id}_en"
                if hasattr(aj, "req_id") and aj.req_id
                else ""
            )
        )

        description = ""
        if hasattr(aj, "description") and aj.description:
            description = strip_html(aj.description)
        if not description and hasattr(aj, "qualifications") and aj.qualifications:
            description = strip_html(aj.qualifications)

        jobs.append({
            "company": "accenture",
            "title": title,
            "location": location,
            "department": "",
            "published_at": published,
            "url": apply_url,
            "apply_url": apply_url,
            "description": truncate_text(description, 600),
            "workplace_type": "",
            "is_remote": "remote" in location.lower(),
            "source": "Accenture",
        })
    return jobs
