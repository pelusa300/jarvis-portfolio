---
aliases: ["filter-and-description-design (2026-03-26)"]
---
# Filter Refinements: Negative Title Filter + HTML Description Cleanup — Design Spec

**Date:** 2026-03-26
**Project:** agente-job-hunter
**Status:** Approved

---

## Overview

Two surgical improvements to reduce false positives in job filtering and improve skills gap detection accuracy. Approach B: minimal scope, no new files, no new dependencies.

---

## Change 1 — Negative Title Filter (`filters/job_filter.py`)

### Problem
Jobs like "Poker Room Manager", "Brand Designer", "SaaS Platform Architect" pass the current filters because their *descriptions* contain crypto/AML keywords. The title is never checked independently.

### Solution
Add a constant list of excluded role keywords and check it against the job **title only** (not description). If the title matches any excluded keyword, the job is rejected immediately — before any positive keyword checks run.

### Constant

```python
TITLE_EXCLUDE_KEYWORDS = [
    "designer", "design", "creative",
    "software engineer", "backend engineer", "frontend engineer",
    "data engineer", "devops", "sre", "infrastructure",
    "software developer", "web developer", "mobile developer",
    "marketing", "sales", "growth",
    "data scientist", "machine learning", "ml engineer",
    "poker", "casino", "game developer", "game designer",
    "recruiter", "hr manager", "hr director", "hr business partner",
    "product manager", "scrum",
]
```

Placed at the top of `filters/job_filter.py` alongside the existing keyword lists.

**Note:** Bare `"engineer"` is intentionally excluded from this list. "Compliance Engineer", "AML Engineer", "KYC Engineer", and "RegTech Engineer" are legitimate target roles for Adrian. Only compound phrases like `"software engineer"`, `"backend engineer"` etc. are excluded.

### New function

```python
def _has_excluded_title(job: dict) -> bool:
    title = (job.get("title") or "").lower()
    return any(kw in title for kw in TITLE_EXCLUDE_KEYWORDS)
```

Checks only `job["title"]`, never description or location.

### Integration

```python
def _passes_strict(job: dict) -> bool:
    if _has_excluded_title(job):
        return False
    text = _text(job)
    return _is_remote(text) and _has_role(text) and _has_sector(text)

def _passes_broad(job: dict) -> bool:
    if _has_excluded_title(job):
        return False
    text = _text(job)
    criteria = [
        _is_remote(text) or _is_hybrid(text),
        _has_role(text),
        _has_sector(text),
        _is_known_company(job),
    ]
    return sum(criteria) >= 2
```

The exclusion check runs first in both functions. A job with title "Brand Designer" is rejected even if its description mentions "AML" or "blockchain".

### Design notes
- Substring match (same pattern as existing keyword checks): `kw in title`
- Case-insensitive: title is lowercased before comparison
- No regex, no word-boundary logic — intentionally simple
- `categorize_job()` is intentionally unaffected by this exclusion: it only receives jobs that have already passed `filter_jobs()`, so excluded jobs never reach categorization.
- "No new files" constraint applies to production code only; new test files are permitted.

---

## Change 2 — HTML Cleanup in Remote OK Scraper (`scrapers/remote_ok.py`)

### Problem
`item.get("description")` from the Remote OK API returns HTML (`<p>`, `<li>`, `<strong>`, etc.). The gap analyzer does substring matching on this raw HTML. Skills like "Chainalysis" would still match as plain text inside tags, but the overall text is noisy and harder to reason about. Cleaning it makes the description more reliable.

### Solution
Strip HTML tags using `BeautifulSoup` before storing the description. `BeautifulSoup` is already a project dependency (used by `crypto_jobs_list.py` and `web3_career.py`), so no new imports are required.

### Code change in `fetch_jobs()`

```python
# Before:
description = (item.get("description") or "") + " " + tags_text

# After:
raw_desc = item.get("description") or ""
clean_desc = BeautifulSoup(raw_desc, "html.parser").get_text(separator=" ", strip=True)
description = clean_desc + " " + tags_text
```

The `BeautifulSoup` import is added at the top of `remote_ok.py`:
```python
from bs4 import BeautifulSoup
```

### Effect
A Raw description like:
```html
<p>Experience with <strong>Chainalysis</strong> required. Must have <em>SQL</em> skills.</p>
```
Becomes:
```
Experience with Chainalysis required. Must have SQL skills.
```
Gap analyzer can now detect "Chainalysis" and "SQL" as gaps cleanly.

### Scope limitation
This only improves Remote OK jobs. Crypto Jobs List and Web3 Career scrapers already call `get_text()` on their HTML cards — their description is limited to what the listing card contains (no individual job page fetch). This is a known limitation, accepted per the chosen approach (B).

---

## Files Changed

| File | Change |
|------|--------|
| `filters/job_filter.py` | Add `TITLE_EXCLUDE_KEYWORDS` constant; add `_has_excluded_title()` function; integrate into `_passes_strict()` and `_passes_broad()` |
| `scrapers/remote_ok.py` | Add `from bs4 import BeautifulSoup`; strip HTML from description before storing |
| `tests/test_filter.py` | New tests for `_has_excluded_title()` and exclusion behavior in `filter_jobs()` |
| `tests/test_scraper_remote_ok.py` | New/updated test verifying description has no HTML tags |

## Files NOT Changed

| File | Reason |
|------|--------|
| `analysis/gap_analyzer.py` | Already reads `job.get("description")` correctly |
| `config.py` | No skills list changes |
| `notifier/telegram_bot.py` | No format changes |
| `main.py` | No pipeline changes |
| `scrapers/crypto_jobs_list.py` | Already uses `get_text()` |
| `scrapers/web3_career.py` | Already uses `get_text()` |

---

## Testing

### New tests — `tests/test_filter.py`

**`_has_excluded_title` unit tests:**
- Job with title "Brand Designer" → `_has_excluded_title()` returns `True`
- Job with title "Poker Room Manager" → `_has_excluded_title()` returns `True`
- Job with title "Senior DevOps Engineer" → `_has_excluded_title()` returns `True`
- Job with title "HR Manager" → `_has_excluded_title()` returns `True`
- Job with title "AML Analyst" → `_has_excluded_title()` returns `False`
- Job with title "Compliance Officer" → `_has_excluded_title()` returns `False`
- Job with title "AML Compliance Engineer" → `_has_excluded_title()` returns `False` (bare "engineer" is NOT in the list)
- Job with title "" (empty) → `_has_excluded_title()` returns `False`
- Job with title `None` → `_has_excluded_title()` returns `False`

**Integration tests via `filter_jobs()`:**
- Job with title "Brand Designer" and description containing all strict keywords → NOT in strict or broad
- Job with title "AML Compliance Engineer" and description with all strict keywords → passes both strict and broad

### New/updated tests — `tests/test_scraper_remote_ok.py`

- When API returns a job with HTML description `<p>Chainalysis required</p>`, the stored `description` field must not contain `<p>` or `</p>` tags
- The stored description must contain `"Chainalysis"` as plain text

### Existing tests
All existing tests in `tests/test_filter.py`, `tests/test_gap_analyzer.py`, and `tests/test_telegram_bot.py` must continue to pass without modification.

---

## Constraints

- Python 3.9 compatibility
- No new files created
- No new package dependencies (`beautifulsoup4` already in requirements)
- All existing tests must pass
