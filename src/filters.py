"""
Location and keyword filters for cybersecurity jobs in Europe/Remote.

Location filter priority chain:
  1. UK/London → EXCLUDE
  2. Explicit non-EU countries (US, India, Canada, etc.) → EXCLUDE
  3. EU/EEA/EMEA/Europe or any EU country/city → INCLUDE
  4. Remote (without non-EU location context) → INCLUDE
  5. Otherwise → EXCLUDE
"""

import re
from datetime import datetime, timedelta, timezone

# ── Cybersecurity Keywords ─────────────────────────────────────────────────

CYBER_KEYWORDS = [
    "security", "cyber", "cybersecurity", "grc", "soc analyst",
    "soc", "penetration test", "pentest", "ethical hack",
    "cloud security", "appsec", "application security",
    "software security", "network security", "network engineer",
    "vulnerability", "threat", "incident response", "forensic",
    "digital forensic", "cryptograph", "cryptography",
    "it admin", "sysadmin", "system administrator",
    "it support", "linux admin", "linux engineer",
    "information security", "infosec", "security analyst",
    "security engineer", "security architect", "security consultant",
    "security audit", "security compliance", "compliance officer",
    "risk analyst", "risk management", "privacy",
    "security operator", "security operations",
    "malware", "reverse engineer", "exploit",
    "devsecops", "secops", "blue team", "red team",
    "identity security", "iam", "access management",
    "security intern", "cybersecurity intern",
    "it engineer", "infrastructure engineer",
    "site reliability", "sre",
    "security software", "security tool",
    "detection engineer", "detection and response",
    "security researcher", "security research",
    "security manager", "security director", "ciso",
    "data protection", "security specialist",
    "it security", "cyber defense",
    "junior security", "graduate security",
    "security associate", "security officer",
    "security advisor", "security lead",
    "forward deployed engineer", "forward deployed",
    "fde",
    # ── Role expansion (vuln mgmt, threat intel, fraud, GRC, tooling) ──
    "forward deployed architect",
    "vulnerability manager", "vulnerability management",
    "vulnerability analyst", "vulnerability researcher",
    "threat intelligence", "threat hunter", "threat hunting",
    "offensive security", "purple team",
    "siem", "edr", "xdr", "mdr", "soar", "dlp",
    "cspm", "sast", "dast", "waf",
    "endpoint security", "endpoint detection",
    "zero trust", "privileged access", "identity and access",
    "fraud", "fraud analyst", "fraud detection",
    "trust and safety", "trust & safety", "abuse",
    "incident responder",
    "third party risk", "vendor risk", "supply chain security",
    "security governance", "governance and compliance",
    "iso 27001", "iso27001", "nist", "gdpr",
    "compliance manager", "compliance analyst", "compliance specialist",
    "it auditor", "security auditor", "internal auditor",
    "bug bounty", "smart contract",
]

# ── Location Lists ─────────────────────────────────────────────────────────

UK_TERMS = [
    "uk", "london", "united kingdom", "england", "scotland",
    "wales", "northern ireland", "britain", "british",
    "manchester", "birmingham", "edinburgh", "glasgow",
    "leeds", "liverpool", "bristol", "sheffield",
]

NON_EU_TERMS = [
    "united states", "usa", "india", "canada",
    "australia", "japan", "china", "brazil",
    "mexico", "argentina", "singapore",
    "south korea", "taiwan", "hong kong",
    "new zealand", "south africa", "turkey",
    "israel", "uae", "dubai",
    "san francisco", "new york", "seattle", "austin",
    "boston", "chicago", "los angeles", "denver",
    "miami", "atlanta", "portland", "phoenix",
    "washington dc", "dallas", "houston", "san jose",
    "san diego", "philadelphia", "raleigh",
    "delhi", "bangalore", "mumbai", "pune",
    "hyderabad", "chennai", "sydney", "melbourne",
    "tokyo", "shanghai", "beijing",
]

EU_TERMS = [
    "europe", "eea", "emea", "schengen",
    "lithuania", "latvia", "estonia", "netherlands",
    "germany", "greece", "france", "spain", "italy", "portugal",
    "poland", "czech", "austria", "switzerland", "sweden",
    "norway", "denmark", "finland", "belgium", "ireland",
    "hungary", "romania", "bulgaria", "slovakia", "slovenia",
    "croatia", "cyprus", "malta", "luxembourg", "iceland",
    "liechtenstein", "monaco", "andorra", "czechia",
    "berlin", "amsterdam", "athens", "paris", "dublin", "munich",
    "hamburg", "copenhagen", "stockholm", "oslo", "helsinki",
    "barcelona", "madrid", "lisbon", "milan", "rome",
    "warsaw", "prague", "budapest", "vienna", "zurich",
    "brussels", "rotterdam", "utrecht",
    "vilnius", "riga", "tallinn",
]


# ── Filter Functions ───────────────────────────────────────────────────────

def is_recent(published_at: datetime | None, lookback_hours: int = 24) -> bool:
    """Check if a timestamp is within the lookback period."""
    if not published_at:
        return False
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    return published_at > cutoff


def is_location_match(location_text: str | None) -> bool:
    """Check if location matches EU/Remote criteria (excludes UK, US, India, etc.)."""
    if not location_text:
        return False

    text_lower = location_text.lower()

    # 1. Exclude UK/London
    for excl in UK_TERMS:
        if excl in text_lower:
            return False

    # 2. Exclude non-EU countries (word-boundary for "us")
    if re.search(r"\bus\b", text_lower) or re.search(r"\bu\.s\b", text_lower):
        return False
    for term in NON_EU_TERMS:
        if term in text_lower:
            return False

    # 3. Include EU/EEA/EMEA/Europe
    for incl in EU_TERMS:
        if incl in text_lower:
            return True

    # 4. Include Remote (reached only if no non-EU/UK exclusion fired)
    if "remote" in text_lower:
        return True

    return False


def is_cyber_match(title: str, department: str = "") -> bool:
    """Check if job title or department matches cybersecurity keywords."""
    text = f"{title} {department}".lower()
    for kw in CYBER_KEYWORDS:
        if kw in text:
            return True
    return False
