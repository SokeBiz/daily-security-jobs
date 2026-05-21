#!/usr/bin/env python3
"""
Daily Security Jobs — Scrapes cybersecurity jobs from major ATS platforms.

Scrapes: Ashby, Greenhouse, Lever, Personio, Recruitee, Amazon, Workday, Accenture
Filters: posted in last N hours, EU/EMEA/Remote locations (excl. UK, US, India, etc.),
         cybersecurity-related keywords.
Outputs: .docx report with job summaries and apply links.

Usage:
    python -m src.main --hours 24
    python -m src.main --hours 6 --output /tmp/jobs.docx
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from .filters import is_recent, is_location_match, is_cyber_match
from .docx_generator import generate_docx
from .scrapers.ashby import fetch_ashby_jobs
from .scrapers.greenhouse import fetch_greenhouse_jobs
from .scrapers.lever import fetch_lever_jobs
from .scrapers.personio import fetch_personio_jobs
from .scrapers.recruitee import fetch_recruitee_jobs
from .scrapers.amazon import fetch_amazon_jobs
from .scrapers.workday import fetch_workday_jobs
from .scrapers.accenture import fetch_accenture_jobs

logger = logging.getLogger(__name__)

# Default config
SCRIPT_DIR = Path(__file__).resolve().parent.parent
COMPANIES_FILE = SCRIPT_DIR / "companies.json"
OUTPUT_DIR = Path("/tmp")
LOOKBACK_HOURS = 24

# Platform fetch function map
PLATFORMS = [
    ("Ashby",       fetch_ashby_jobs),
    ("Greenhouse",  fetch_greenhouse_jobs),
    ("Lever",       fetch_lever_jobs),
    ("Amazon",      fetch_amazon_jobs),
    ("Workday",     fetch_workday_jobs),
    ("Personio",    fetch_personio_jobs),
    ("Recruitee",   fetch_recruitee_jobs),
    ("Accenture",   fetch_accenture_jobs),
]


def load_companies() -> dict[str, list[str]]:
    """Load company list from JSON file."""
    if not COMPANIES_FILE.exists():
        print(f"❌ Companies file not found: {COMPANIES_FILE}")
        print("   Create it from companies.json or copy the example.")
        sys.exit(1)
    with open(COMPANIES_FILE) as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(
        description="Daily Security Jobs — scrape and filter cybersecurity jobs"
    )
    parser.add_argument(
        "--hours", type=int, default=24,
        help="Lookback window in hours (default: 24)"
    )
    parser.add_argument(
        "--output", type=str, default="",
        help="Output .docx path (default: /tmp/security-jobs-{timestamp}.docx)"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable debug logging"
    )
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")
    else:
        logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(levelname)s] %(message)s")

    lookback = args.hours
    if args.output:
        output_path = Path(args.output)
    else:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_path = OUTPUT_DIR / f"security-jobs-{timestamp}.docx"

    print(f"\U0001f50d Security Jobs Scraper \u2014 looking back {lookback} hours")
    print(f"   Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    companies = load_companies()

    all_fetched = []
    errors = []
    platform_counts = {}

    for platform_name, fetch_func in PLATFORMS:
        company_key = platform_name.lower()
        company_list = companies.get(company_key, [])
        if not company_list:
            continue

        platform_counts[platform_name] = len(company_list)
        print(f"\n\U0001f4e1 Fetching from {platform_name} ({len(company_list)} companies)...")

        for idx, company in enumerate(company_list, 1):
            sys.stdout.write(f"   [{idx}/{len(company_list)}] {company}... ")
            sys.stdout.flush()
            try:
                jobs = fetch_func(company)
                print(f"{len(jobs)} jobs")
                all_fetched.extend([(j, platform_name.lower()) for j in jobs])
            except Exception as e:
                print(f"ERROR: {e}")
                errors.append(f"{platform_name}/{company}: {e}")
            time.sleep(0.3)  # Rate limiting

    print(f"\n\U0001f4ca Total jobs fetched: {len(all_fetched)}")

    # ── Filter Pipeline ──
    matched = []
    time_skip = 0
    cyber_skip = 0
    location_skip = 0

    for job, source in all_fetched:
        if not is_recent(job["published_at"], lookback):
            time_skip += 1
            continue
        if not is_cyber_match(job["title"], job.get("department", "")):
            cyber_skip += 1
            continue
        if not is_location_match(job["location"]):
            location_skip += 1
            continue
        matched.append(job)

    print(f"\n\U0001f4cb Filter results:")
    print(f"   - Too old: {time_skip}")
    print(f"   - Not security: {cyber_skip}")
    print(f"   - Wrong location: {location_skip}")
    print(f"   \u2705 Matched: {len(matched)}")

    # ── Generate DOCX ──
    docx_path = generate_docx(
        matched,
        lookback,
        output_dir=output_path.parent,
        platform_counts=platform_counts,
    )
    size_kb = os.path.getsize(docx_path) / 1024
    print(f"\n\U0001f4c4 DOCX generated: {docx_path}")
    print(f"   Size: {size_kb:.1f} KB")
    print(f"\n\U0001f4ce MEDIA:{docx_path}")

    if errors:
        print(f"\n\u26a0\ufe0f Errors ({len(errors)}):")
        for err in errors[:5]:
            print(f"   - {err}")


if __name__ == "__main__":
    main()
