---
aliases: ["report-format-design (2026-03-26)"]
---
# Telegram Report Format Improvements — Design Spec

**Date:** 2026-03-26
**Project:** agente-job-hunter
**Status:** Approved

---

## Overview

Four targeted improvements to the Telegram report format sent by the job hunter automation system. All changes follow Approach 3: surgical edits to existing files only, no new modules.

---

## Change 1 — Skills Match (config.py)

Expand the skills lists to better reflect Adrian's real profile and surface genuine gaps.

### SKILLS_HAVE (Adrian already knows — shown as "Cumples")
```python
SKILLS_HAVE = [
    "CAMS", "KYC", "AML", "BSA", "FinCEN", "OFAC",
    "SAR", "CTR", "FATF", "Travel Rule",
    "CDD", "EDD", "sanctions screening", "risk assessment",
    "blockchain", "DeFi",
]
```

### SKILLS_LEARNING (Adrian doesn't have yet — shown as "Te falta")
```python
SKILLS_LEARNING = [
    "Chainalysis", "Elliptic", "TRM Labs", "blockchain analytics",
    "MLRO", "CFCS", "CKYC", "SQL", "Python",
    "crypto exchange experience", "ACAMS membership", "FinCEN SAR filing",
]
```

**Notes:**
- No literal string appears in both lists.
- `"FinCEN"` (SKILLS_HAVE) and `"FinCEN SAR filing"` (SKILLS_LEARNING) will both match a job description that contains the phrase "FinCEN SAR filing" because `_find_skills_in_text` uses substring containment (`s.lower() in text_lower`). This means such a job would show "FinCEN" in "Cumples" and "FinCEN SAR filing" in "Te falta" simultaneously. This is an acceptable cosmetic limitation — the user sees both, which is informative (they know FinCEN generally but lack SAR filing experience specifically). No code change to `_find_skills_in_text` is required.
- Adding `"Python"` to SKILLS_LEARNING requires updating the existing test fixture `test_score_zero_for_no_skill_match` in `test_gap_analyzer.py`. Change its job description from `"Generic software engineer role with Python"` to `"Generic software engineer role with Java"` to preserve the intent of "no skill match at all".

**No logic changes** in `gap_analyzer.py` — only the list contents change.

---

## Change 2 — Salary Display (telegram_bot.py)

Add an optional salary line to `format_job_entry()`. Only rendered when at least one of `salary_min` / `salary_max` is present.

### Format rules
- Both values: `💰 $80,000 – $120,000 / año`
- Only min: `💰 desde $80,000 / año`
- Only max: `💰 hasta $120,000 / año`
- Neither (`None` / `0`): line omitted entirely (no "N/A", no placeholder)
- Numbers formatted with thousands separator (`,`)

### Job entry example (with salary)
```
1. Financial Crimes Analyst — Coinbase
   📍 Remote | 🔗 https://remoteok.com/...
   💰 $80,000 – $120,000 / año
   ✅ Cumples: KYC, AML, BSA
   ❌ Te falta: Chainalysis, SQL
```

### Job entry example (no salary)
```
2. AML Investigator — Kraken
   📍 Remote | 🔗 https://remoteok.com/...
   ✅ Cumples: KYC, AML, OFAC
   ❌ Te falta: Chainalysis, MLRO
```

**Note:** Only Remote OK currently provides salary data. Other scrapers return `None` for both fields and will simply not show the line.

---

## Change 3 — Report Structure (telegram_bot.py + gap_analyzer.py + main.py)

### 3a. STRICT section — unchanged structure
All strict jobs shown together under the existing header:
```
━━━━━━━━━━━━━━━━━━━━━━
🎯 LISTA ESTRICTA (N ofertas)
━━━━━━━━━━━━━━━━━━━━━━

1. Job Title — Company
   ...
```

### 3b. BROAD section — grouped by category

A new `categorize_job(job: dict) -> str` function added to `filters/job_filter.py`.

**Category keywords** (checked against title + description, case-insensitive):

| Category | Keywords |
|----------|----------|
| AML | anti-money laundering, AML, money laundering |
| Financial Crimes | financial crimes, financial crime, financial intelligence |
| KYC | KYC, know your customer, CDD, customer due diligence |
| Compliance | compliance |
| Otras | (catch-all) |

**Classification priority** (when a job matches multiple categories):
AML > Financial Crimes > KYC > Compliance > Otras

**Section display order** (order categories appear in the message):
AML → Financial Crimes → KYC → Compliance → Otras

Empty categories are omitted.

**Rendered output:**
```
━━━━━━━━━━━━━━━━━━━━━━
📋 LISTA AMPLIA (23 ofertas)
━━━━━━━━━━━━━━━━━━━━━━

🔵 AML (8 ofertas)
1. AML Analyst — Binance
   ...

🟠 Financial Crimes (3 ofertas)
1. Financial Crimes Investigator — Chainalysis
   ...

🟢 KYC (5 ofertas)
1. KYC Manager — Circle
   ...

🟡 Compliance (6 ofertas)
1. Compliance Officer — Circle
   ...

⚪ Otras (1 oferta)
...
```

### 3c. Updated function signatures and code changes

**`gap_analyzer.py` — `analyze_jobs()` updated return:**

The docstring must be updated to reflect `top3`. `top3` is `top5[:3]` — jobs with `score > 0` only (zero-score jobs are excluded before slicing). If fewer than 3 jobs score > 0, the list contains however many are available.

```python
def analyze_jobs(strict: List[dict], broad: List[dict]) -> dict:
    """
    Returns {"strict": [...], "broad": [...], "top3": [...]}.
    top3: top 3 scoring jobs (score > 0) across both lists, Claude-enriched.
    """
    ...
    top5 = select_top_jobs(all_jobs, n=5)
    # Claude enrichment runs on top5 as before
    for job in top5:
        job["claude_analysis"] = _get_claude_analysis(job)
    top3 = [j for j in top5 if j.get("score", 0) > 0][:3]  # exclude zero-score
    ...
    return {"strict": enrich(strict_scored), "broad": enrich(broad_scored), "top3": top3}
```

**`telegram_bot.py` — updated signatures and internal call chain:**

```python
def split_into_messages(strict: List[dict], broad: List[dict], top3: List[dict], date_str: str) -> List[str]:
    # builds messages; top3 used in summary block
    ...

def format_report(strict: List[dict], broad: List[dict], top3: List[dict]) -> List[str]:
    date_str = date.today().strftime("%d %b %Y")
    return split_into_messages(strict, broad, top3, date_str)

async def send_report(strict: List[dict], broad: List[dict], top3: List[dict]) -> None:
    ...
    messages = format_report(strict, broad, top3)
    ...
```

**`main.py` — updated call site:**
```python
analyzed = analyze_jobs(strict, broad)
asyncio.run(send_report(analyzed["strict"], analyzed["broad"], analyzed["top3"]))
```

### 3d. Summary block (replaces current footer)

```
━━━━━━━━━━━━━━━━━━━━━━
📊 Total nuevas: 28 | 🗓️ Próximo: 02 Apr 2026

🏆 TOP 3 PARA TU PERFIL
1. Financial Crimes Analyst — Coinbase (85%)
2. AML Investigator — Kraken (72%)
3. KYC Manager — Circle (68%)
```

Score displayed as integer percentage (`score * 100`). If fewer than 3 jobs scored > 0, show however many are available.

---

## Files Changed

| File | Change |
|------|--------|
| `config.py` | Expand `SKILLS_HAVE` and `SKILLS_LEARNING` lists |
| `filters/job_filter.py` | Add `categorize_job(job: dict) -> str` function |
| `analysis/gap_analyzer.py` | Add `top3` key to return dict; compute as `top5` filtered to `score > 0`, then `[:3]` |
| `notifier/telegram_bot.py` | Salary in `format_job_entry`; category grouping in BROAD section; `top3` param in `format_report`, `split_into_messages`, `send_report`; new summary block |
| `main.py` | Pass `analyzed["top3"]` to `send_report` |

## Files NOT changed

| File | Reason |
|------|--------|
| `scrapers/*.py` | No scraper changes needed |
| `storage/store.py` | Storage unchanged |

---

## Testing

### Existing test to fix (must be applied before merging)

**`tests/test_gap_analyzer.py`** — `test_score_zero_for_no_skill_match` (line 31):
- Change: `make_job("Generic software engineer role with Python")`
- To: `make_job("Generic software engineer role with Java")`
- Reason: "Python" is now in SKILLS_LEARNING; the fixture must contain no listed skill to test the zero-score branch correctly.

### New test cases required

**`tests/test_filter.py`** — `categorize_job`:
- Title "AML Analyst" → `"AML"`
- Title "KYC Manager" → `"KYC"`
- Title "Financial Crimes Investigator" → `"Financial Crimes"`
- Title "Compliance Officer" → `"Compliance"`
- Title "Software Engineer" → `"Otras"`
- Job with both AML and Compliance keywords → `"AML"` (priority wins)

**`tests/test_telegram_bot.py`** — salary in `format_job_entry`:
- Job with `salary_min=80000, salary_max=120000` → shows `💰 $80,000 – $120,000 / año`
- Job with `salary_min=80000, salary_max=None` → shows `💰 desde $80,000 / año`
- Job with `salary_min=None, salary_max=120000` → shows `💰 hasta $120,000 / año`
- Job with `salary_min=None, salary_max=None` → no salary line in output

**`tests/test_gap_analyzer.py`** — `analyze_jobs` return dict:
- Return dict contains `top3` key
- `top3` has at most 3 entries
- All entries in `top3` have `score > 0`
- `top3` entries are ordered by score descending

**`tests/test_telegram_bot.py`** — empty category omission:
- A broad list with no Financial Crimes jobs must not emit a "Financial Crimes" header in the output

### Existing telegram_bot tests to update (must be applied before merging)

The three existing tests in `tests/test_telegram_bot.py` that call `split_into_messages` or `format_report` must be updated to pass `top3=[]` as a third argument — otherwise they will raise `TypeError` after the signature changes:

- `test_split_messages_respects_limit` — update call: `split_into_messages(strict, broad, [], date_str="24 Mar 2026")`
- `test_split_never_cuts_mid_entry` — update call: `split_into_messages(strict, broad, [], date_str="24 Mar 2026")`
- `test_format_report_returns_list_of_strings` — update call: `format_report(strict, broad, [])`

---

## Constraints

- Python 3.9 compatibility (no `X | Y` union types, use `Optional[X]`)
- No new files created
- All existing tests must continue to pass (with the one fixture fix noted above)
- Message splitting logic (`split_into_messages`) must still respect the 4096-char Telegram limit
