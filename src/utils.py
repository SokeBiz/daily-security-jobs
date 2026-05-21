"""
Utility functions for the job scraper: HTTP fetching, timestamp parsing,
HTML stripping, text truncation.
"""

import json
import logging
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def fetch_json(url: str, max_retries: int = 2) -> dict | list | None:
    """Fetch JSON from a URL with retries."""
    for attempt in range(max_retries + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "DailySecurityJobs/1.0"},
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode())
        except (
            urllib.error.HTTPError,
            urllib.error.URLError,
            json.JSONDecodeError,
            TimeoutError,
        ) as e:
            if attempt < max_retries:
                time.sleep(1)
                continue
            logger.debug("Failed to fetch %s: %s", url, e)
            return None


def parse_iso_timestamp(ts: str | None) -> datetime | None:
    """Parse ISO 8601 timestamp string to datetime.

    Handles:
      - '2024-08-14T20:21:56.895+00:00'
      - '2026-04-30T18:34:50-04:00'    (negative offset!)
      - '2026-05-12T10:00:00Z'
      - '2025-11-28T12:53:58+00:00'
    """
    if not ts:
        return None
    try:
        ts = ts.replace("Z", "+00:00")
        # Check for timezone offset (+ or -) after the date portion
        rest = ts[10:]
        has_tz = "+" in rest or "-" in rest
        if has_tz:
            return datetime.fromisoformat(ts)
        return datetime.fromisoformat(ts + "+00:00")
    except (ValueError, TypeError):
        return None


def strip_html(html_text: str | None) -> str:
    """Remove HTML tags from text."""
    if not html_text:
        return ""
    clean = re.sub(r"<[^>]+>", " ", html_text)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def truncate_text(text: str, max_chars: int = 500) -> str:
    """Truncate text to max_chars, breaking at word boundaries."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + "..."
