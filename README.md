# Daily Security Jobs

Scrapes cybersecurity-related job listings from major ATS platforms (Ashby, Greenhouse, Lever, Personio, Recruitee, Amazon, Workday, Accenture) and delivers a `.docx` report.

Filters for **EU/EMEA/Remote** positions (excludes UK, US, India, Canada, Australia, Japan, Singapore, and other non-EU locations) matching **cybersecurity keywords**.

## Features

-   **8 platform scrapers** — Ashby, Greenhouse, Lever, Personio, Recruitee, Amazon, Workday (PwC, Deloitte), Accenture (Workday + JSON-LD)
-   **Location filtering** — EU/EEA/EMEA + Remote only; excludes UK, US, India, CA, AU, JP, SG
-   **Keyword matching** — 125+ security/cyber keywords (SOC, pentest, cloud security, devsecops, GRC, IAM, vulnerability management, threat intel, fraud, trust & safety, zero trust, SIEM/EDR/XDR, compliance, audit, etc.)
-   **Time filter** — configurable lookback window (default 24h)
-   **DOCX output** — formatted report with job title, company, location, description, and apply link
-   **Add companies easily** — just edit `companies.json` with the company's ATS board token
-   **Cron-ready** — includes `run.sh` wrapper for Telegram/cron delivery (outputs `MEDIA:<path>`)

## Quick Start

```bash
# 1. Clone and enter
git clone https://github.com/SokeBiz/daily-security-jobs.git
cd daily-security-jobs

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the scraper
python -m src.main --hours 24
```

The output file is saved to `/tmp/security-jobs-{timestamp}.docx` by default.

### Options

```
python -m src.main --hours 24          # Look back 24 hours
python -m src.main --hours 6           # Look back 6 hours
python -m src.main --output report.docx  # Custom output path
python -m src.main --verbose           # Debug logging
```

## Adding Companies

Edit `companies.json` and add the company's ATS board token under the correct platform.

### Finding a company's ATS token

Each platform uses a company-specific token/identifier:

| Platform | API URL Pattern | Example |
|---|---|---|
| **Ashby** | `https://api.ashbyhq.com/posting-api/job-board/{token}` | `cursor`, `notion`, `openai` |
| **Greenhouse** | `https://boards-api.greenhouse.io/v1/boards/{token}/jobs` | `cloudflare`, `stripe`, `gitlab` |
| **Lever** | `https://api.lever.co/v0/postings/{token}?mode=json` | `spotify`, `atlassian` |
| **Personio** | `https://{token}.jobs.personio.de/xml?language=en` | `xempus` |
| **Recruitee** | `https://{token}.recruitee.com/api/offers` | `duckduckgo` |

**Verify a token before adding it:**

```bash
# Ashby
curl -s -o /dev/null -w "%{http_code}" "https://api.ashbyhq.com/posting-api/job-board/cursor"
# → 200 = valid

# Greenhouse
curl -s -o /dev/null -w "%{http_code}" "https://boards-api.greenhouse.io/v1/boards/cloudflare/jobs"
# → 200 = valid

# Lever
curl -s -o /dev/null -w "%{http_code}" "https://api.lever.co/v0/postings/spotify?mode=json"
# → 200 = valid
```

### JSON structure

```json
{
  "greenhouse": ["token1", "token2"],
  "ashby": ["token3", "token4"],
  "lever": ["token5"],
  "amazon": ["amazon"],
  "workday": ["pwc", "deloitte"],
  "personio": ["company-name"],
  "recruitee": ["company-name"],
  "accenture": ["accenture"]
}
```

For **Workday** companies, you may need to add the site configuration to `src/scrapers/workday.py` in the `WORKDAY_SITES` dict:

```python
WORKDAY_SITES = {
    "pwc": {"subdomain": "pwc", "wd": "wd3", "path": "Global_Experienced_Careers"},
    "deloitte": {"subdomain": "deloitteie", "wd": "wd3", "path": "experienced_professionals"},
    # Add new Workday companies here
}
```

## Scheduling with Cron

### Daily at 06:00

```bash
crontab -e
# Add:
0 6 * * * cd /path/to/daily-security-jobs && ./run.sh
```

### Using Hermes Agent cron

```bash
hermes cron create \
  --name "security-jobs-scraper" \
  --prompt "Run the scraper: bash ~/daily-security-jobs/run.sh. Include any MEDIA: line in your response." \
  --schedule "0 6 * * *" \
  --repeat forever
```

## Customizing Filters

### Adding cybersecurity keywords

Edit `CYBER_KEYWORDS` in `src/filters.py`:

```python
CYBER_KEYWORDS = [
    "security", "cyber", "soc", "pentest",
    # Add your keywords here
]
```

### Changing location rules

Edit the `is_location_match()` function in `src/filters.py`. The `UK_TERMS`, `NON_EU_TERMS`, and `EU_TERMS` lists can be extended as needed.

## Platform Details

### Accenture (Workday + Custom Frontend)

Accenture uses Workday (wd103) as their ATS but serves jobs through a custom AEM frontend. The scraper uses a **two-step approach**:

1.  **Workday CXS API** → job listings (title, ID, location) — filtered by "security" keyword
2.  **Accenture.com job details pages** → JSON-LD structured data (full description, qualifications, salary)

### Workday (PwC, Deloitte)

These use the standard Workday CXS API directly. Only basic listing data (title, location, department) is fetched — no full descriptions.

## Project Structure

```
daily-security-jobs/
├── README.md
├── requirements.txt
├── companies.json          # Company ATS tokens — add yours here
├── run.sh                  # Cron wrapper script
└── src/
    ├── __init__.py
    ├── main.py             # Entry point
    ├── filters.py          # Location & keyword filters
    ├── utils.py            # HTTP, timestamp, HTML helpers
    ├── docx_generator.py   # .docx report builder
    └── scrapers/
        ├── __init__.py
        ├── ashby.py
        ├── greenhouse.py
        ├── lever.py
        ├── personio.py
        ├── recruitee.py
        ├── amazon.py
        ├── workday.py
        └── accenture.py    # Two-step Workday + JSON-LD scraper
```

## License

MIT
