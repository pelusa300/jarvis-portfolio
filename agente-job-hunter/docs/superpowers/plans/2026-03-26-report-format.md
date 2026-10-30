---
aliases: ["report-format (2026-03-26)"]
---
# Telegram Report Format Improvements — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve the Telegram job report with salary display, category grouping in the BROAD section, a TOP 3 summary block, and expanded skill matching lists.

**Architecture:** Surgical edits to 5 existing files — no new files created. TDD throughout. Each task is independently committable.

**Tech Stack:** Python 3.9, pytest, existing codebase (`config.py`, `filters/job_filter.py`, `analysis/gap_analyzer.py`, `notifier/telegram_bot.py`, `main.py`)

**Spec:** `docs/superpowers/specs/2026-03-26-report-format-design.md`

---

## File Map

| File | Change |
|------|--------|
| `config.py` | Expand `SKILLS_HAVE` (16 items) and `SKILLS_LEARNING` (12 items) |
| `filters/job_filter.py` | Add `categorize_job(job: dict) -> str` function |
| `analysis/gap_analyzer.py` | Add `top3` key to `analyze_jobs()` return dict |
| `notifier/telegram_bot.py` | Salary line in `format_job_entry`; category grouping in BROAD; `top3` param in all 3 public functions; new summary block |
| `main.py` | Pass `analyzed["top3"]` to `send_report` |
| `tests/test_filter.py` | Add 6 `categorize_job` test cases |
| `tests/test_gap_analyzer.py` | Fix 1 existing fixture; add 4 `analyze_jobs` test cases |
| `tests/test_telegram_bot.py` | Fix 3 existing call sites; add 5 new test cases |

---

## Task 1: Skills Expansion (config.py + test fixture fix)

**Files:**
- Modify: `config.py`
- Modify: `tests/test_gap_analyzer.py` (fixture fix on line 31)

### Step 1: Fix the existing test fixture

In `tests/test_gap_analyzer.py` line 31, change "Python" to "Java" — otherwise adding "Python" to SKILLS_LEARNING will break this test's intent ("no skill match at all"):

- [ ] Edit `tests/test_gap_analyzer.py`:

```python
# line 31 — BEFORE:
    job = make_job("Generic software engineer role with Python")
# AFTER:
    job = make_job("Generic software engineer role with Java")
```

- [ ] Run to confirm it still passes:

```bash
python3 -m pytest tests/test_gap_analyzer.py::test_score_zero_for_no_skill_match -v
```
Expected: PASS

### Step 2: Expand the skills lists in config.py

- [ ] Replace `SKILLS_HAVE` and `SKILLS_LEARNING` in `config.py`:

```python
SKILLS_HAVE = [
    "CAMS", "KYC", "AML", "BSA", "FinCEN", "OFAC",
    "SAR", "CTR", "FATF", "Travel Rule",
    "CDD", "EDD", "sanctions screening", "risk assessment",
    "blockchain", "DeFi",
]

SKILLS_LEARNING = [
    "Chainalysis", "Elliptic", "TRM Labs", "blockchain analytics",
    "MLRO", "CFCS", "CKYC", "SQL", "Python",
    "crypto exchange experience", "ACAMS membership", "FinCEN SAR filing",
]

ALL_SKILLS = SKILLS_HAVE + SKILLS_LEARNING
```

### Step 3: Run all tests to confirm nothing is broken

- [ ] Run:

```bash
python3 -m pytest tests/ -v
```
Expected: All 33 tests pass (the fixture fix in Step 1 ensures `test_score_zero_for_no_skill_match` still passes).

### Step 4: Commit

- [ ] Commit:

```bash
git add config.py tests/test_gap_analyzer.py
git commit -m "feat: expand skills lists for accurate gap detection"
```

---

## Task 2: categorize_job Function (filters/job_filter.py + test_filter.py)

**Files:**
- Modify: `filters/job_filter.py`
- Modify: `tests/test_filter.py`

### Step 1: Write failing tests

- [ ] Update the existing import at the top of `tests/test_filter.py` (line 3):

```python
# BEFORE:
from filters.job_filter import filter_jobs
# AFTER:
from filters.job_filter import filter_jobs, categorize_job
```

- [ ] Add the following tests to the bottom of `tests/test_filter.py`:

```python

def make_cat_job(title, description=""):
    return {"title": title, "description": description}

def test_categorize_aml():
    assert categorize_job(make_cat_job("AML Analyst")) == "AML"

def test_categorize_kyc():
    assert categorize_job(make_cat_job("KYC Manager")) == "KYC"

def test_categorize_financial_crimes():
    assert categorize_job(make_cat_job("Financial Crimes Investigator")) == "Financial Crimes"

def test_categorize_compliance():
    assert categorize_job(make_cat_job("Compliance Officer")) == "Compliance"

def test_categorize_otras():
    assert categorize_job(make_cat_job("Software Engineer")) == "Otras"

def test_categorize_aml_wins_over_compliance():
    # AML has higher priority than Compliance
    job = make_cat_job("Compliance", description="anti-money laundering program")
    assert categorize_job(job) == "AML"
```

- [ ] Run to confirm they fail:

```bash
python3 -m pytest tests/test_filter.py -k "categorize" -v
```
Expected: ImportError or AttributeError — `categorize_job` doesn't exist yet.

### Step 2: Implement categorize_job in filters/job_filter.py

- [ ] Add the following at the bottom of `filters/job_filter.py` (after `filter_jobs`):

```python
# Category classification — ordered by priority (highest first)
_CATEGORY_RULES = [
    ("AML",             ["anti-money laundering", "aml", "money laundering"]),
    ("Financial Crimes", ["financial crimes", "financial crime", "financial intelligence"]),
    ("KYC",             ["kyc", "know your customer", "cdd", "customer due diligence"]),
    ("Compliance",      ["compliance"]),
]
CATEGORY_ORDER = ["AML", "Financial Crimes", "KYC", "Compliance", "Otras"]


def categorize_job(job: dict) -> str:
    """
    Classifica un job en una categoría basada en título + descripción.
    Prioridad: AML > Financial Crimes > KYC > Compliance > Otras
    """
    text = ((job.get("title") or "") + " " + (job.get("description") or "")).lower()
    for category, keywords in _CATEGORY_RULES:
        if any(kw in text for kw in keywords):
            return category
    return "Otras"
```

### Step 3: Run tests to confirm they pass

- [ ] Run:

```bash
python3 -m pytest tests/test_filter.py -v
```
Expected: All 16 tests pass (10 existing + 6 new).

### Step 4: Commit

- [ ] Commit:

```bash
git add filters/job_filter.py tests/test_filter.py
git commit -m "feat: add categorize_job to job filter"
```

---

## Task 3: Salary Display (telegram_bot.py + test_telegram_bot.py)

**Files:**
- Modify: `notifier/telegram_bot.py`
- Modify: `tests/test_telegram_bot.py`

### Step 1: Write failing salary tests

- [ ] Add to the bottom of `tests/test_telegram_bot.py`:

```python
def test_format_job_shows_salary_both():
    job = make_job()
    job["salary_min"] = 80000
    job["salary_max"] = 120000
    entry = format_job_entry(job, 1)
    assert "💰" in entry
    assert "$80,000" in entry
    assert "$120,000" in entry

def test_format_job_shows_salary_min_only():
    job = make_job()
    job["salary_min"] = 80000
    job["salary_max"] = None
    entry = format_job_entry(job, 1)
    assert "💰" in entry
    assert "desde $80,000" in entry

def test_format_job_shows_salary_max_only():
    job = make_job()
    job["salary_min"] = None
    job["salary_max"] = 120000
    entry = format_job_entry(job, 1)
    assert "💰" in entry
    assert "hasta $120,000" in entry

def test_format_job_no_salary_line_when_absent():
    job = make_job()
    job["salary_min"] = None
    job["salary_max"] = None
    entry = format_job_entry(job, 1)
    assert "💰" not in entry
```

- [ ] Run to confirm they fail:

```bash
python3 -m pytest tests/test_telegram_bot.py -k "salary" -v
```
Expected: FAIL — `format_job_entry` doesn't render salary yet.

### Step 2: Add salary line to format_job_entry in telegram_bot.py

- [ ] In `notifier/telegram_bot.py`, replace the `format_job_entry` function:

```python
def format_job_entry(job: dict, index: int) -> str:
    """Formatea una oferta como string para Telegram."""
    location = job.get("location", "")
    hybrid_warning = " ⚠️" if any(w in location.lower() for w in ["hybrid", "on-site", "onsite", "presencial"]) else ""

    skills_str = ", ".join(job.get("skills_matched") or []) or "—"
    gaps_str = ", ".join(job.get("gaps") or []) or "Ninguna detectada"

    lines = [
        f"{index}. {job.get('title', '?')} — {job.get('company', '?')}",
        f"   📍 {location}{hybrid_warning} | 🔗 {job.get('url', '')}",
    ]

    # Salary line — only if at least one value is present and non-zero
    sal_min = job.get("salary_min") or 0
    sal_max = job.get("salary_max") or 0
    if sal_min and sal_max:
        lines.append(f"   💰 ${sal_min:,} – ${sal_max:,} / año")
    elif sal_min:
        lines.append(f"   💰 desde ${sal_min:,} / año")
    elif sal_max:
        lines.append(f"   💰 hasta ${sal_max:,} / año")

    lines.append(f"   ✅ Cumples: {skills_str}")
    lines.append(f"   ❌ Te falta: {gaps_str}")

    if job.get("claude_analysis"):
        analysis = job["claude_analysis"]
        lines.append(f"   🤖 {analysis}")

    return "\n".join(lines)
```

### Step 3: Run salary tests to confirm they pass

- [ ] Run:

```bash
python3 -m pytest tests/test_telegram_bot.py -k "salary" -v
```
Expected: All 4 new salary tests pass.

### Step 4: Run full test suite to confirm nothing is broken

- [ ] Run:

```bash
python3 -m pytest tests/ -v
```
Expected: All tests pass.

### Step 5: Commit

- [ ] Commit:

```bash
git add notifier/telegram_bot.py tests/test_telegram_bot.py
git commit -m "feat: show salary in job report when available"
```

---

## Task 4: top3 in analyze_jobs (gap_analyzer.py + test_gap_analyzer.py)

**Files:**
- Modify: `analysis/gap_analyzer.py`
- Modify: `tests/test_gap_analyzer.py`

### Step 1: Write failing tests for top3

- [ ] Add the following imports and tests to `tests/test_gap_analyzer.py`:

```python
from analysis.gap_analyzer import analyze_jobs

def make_scored_job(score_description, url="https://example.com/1", is_strict=True):
    return {
        "title": "AML Analyst",
        "company": "TestCo",
        "location": "Remote",
        "url": url,
        "description": score_description,
        "source": "remote_ok",
        "date_posted": "2026-03-24",
        "salary_min": None,
        "salary_max": None,
        "_is_strict": is_strict,
    }

def test_analyze_jobs_returns_top3_key():
    strict = [make_scored_job("KYC AML BSA", url="https://example.com/1")]
    broad = [make_scored_job("Chainalysis TRM", url="https://example.com/2", is_strict=False)]
    result = analyze_jobs(strict, broad)
    assert "top3" in result

def test_analyze_jobs_top3_at_most_3():
    strict = [make_scored_job("KYC AML BSA FinCEN", url=f"https://example.com/{i}") for i in range(10)]
    result = analyze_jobs(strict, [])
    assert len(result["top3"]) <= 3

def test_analyze_jobs_top3_all_positive_score():
    strict = [make_scored_job("KYC AML", url=f"https://example.com/{i}") for i in range(5)]
    result = analyze_jobs(strict, [])
    for job in result["top3"]:
        assert job.get("score", 0) > 0

def test_analyze_jobs_top3_sorted_by_score_descending():
    jobs = [
        make_scored_job("KYC AML BSA FinCEN OFAC", url="https://example.com/1"),  # high score
        make_scored_job("KYC AML", url="https://example.com/2"),                   # medium score
        make_scored_job("KYC", url="https://example.com/3"),                       # lower score
    ]
    result = analyze_jobs(jobs, [])
    scores = [j["score"] for j in result["top3"]]
    assert scores == sorted(scores, reverse=True)
```

- [ ] Run to confirm they fail:

```bash
python3 -m pytest tests/test_gap_analyzer.py -k "top3" -v
```
Expected: FAIL — `analyze_jobs` doesn't return `top3` yet.

### Step 2: Update analyze_jobs to include top3

- [ ] In `analysis/gap_analyzer.py`, replace the `analyze_jobs` function:

```python
def analyze_jobs(strict: List[dict], broad: List[dict]) -> dict:
    """
    Punto de entrada principal. Scores todos los jobs y llama a Claude para el top 5.
    Devuelve {"strict": [...], "broad": [...], "top3": [...]}.
    top3: hasta 3 jobs con score > 0, Claude-enriched, ordenados por score desc.
    """
    # Marcar origen para tiebreaking
    strict_scored = [score_job({**j, "_is_strict": True}) for j in strict]
    broad_scored = [score_job({**j, "_is_strict": False}) for j in broad]

    # Deduplicar por URL (un job que aparece en ambas listas cuenta como strict)
    strict_urls = {j["url"] for j in strict_scored}
    all_jobs = strict_scored + [j for j in broad_scored if j["url"] not in strict_urls]
    top5 = select_top_jobs(all_jobs, n=5)

    # Nivel 2: Claude analysis para top 5
    for job in top5:
        job["claude_analysis"] = _get_claude_analysis(job)

    # Top 3 para resumen: solo jobs con score > 0, ya Claude-enriched
    top3 = [j for j in top5 if j.get("score", 0) > 0][:3]

    # Reconstruir listas con análisis añadido
    def enrich(job_list):
        enriched = []
        for j in job_list:
            match = next((t for t in top5 if t["url"] == j["url"]), None)
            enriched.append(match if match else j)
        return enriched

    return {"strict": enrich(strict_scored), "broad": enrich(broad_scored), "top3": top3}
```

### Step 3: Run tests to confirm they pass

- [ ] Run:

```bash
python3 -m pytest tests/test_gap_analyzer.py -v
```
Expected: All tests pass (8 existing + 4 new = 12 total).

### Step 4: Commit

- [ ] Commit:

```bash
git add analysis/gap_analyzer.py tests/test_gap_analyzer.py
git commit -m "feat: expose top3 in analyze_jobs return dict"
```

---

## Task 5: Report Structure — Categories + Summary Block (telegram_bot.py + main.py)

**Files:**
- Modify: `notifier/telegram_bot.py`
- Modify: `main.py`
- Modify: `tests/test_telegram_bot.py`

### Step 1: Update the 3 existing call sites in test_telegram_bot.py

These tests call `split_into_messages` and `format_report` without `top3`. Update them now so they pass after the signature change:

- [ ] In `tests/test_telegram_bot.py`, make these 3 edits:

```python
# test_split_messages_respects_limit — line 57:
# BEFORE: messages = split_into_messages(strict, broad, date_str="24 Mar 2026")
# AFTER:
    messages = split_into_messages(strict, broad, [], date_str="24 Mar 2026")

# test_split_never_cuts_mid_entry — line 65:
# BEFORE: messages = split_into_messages([job], [], date_str="24 Mar 2026")
# AFTER:
    messages = split_into_messages([job], [], [], date_str="24 Mar 2026")

# test_format_report_returns_list_of_strings — line 72:
# BEFORE: messages = format_report(strict, broad)
# AFTER:
    messages = format_report(strict, broad, [])
```

### Step 2: Add new tests for categories and summary block

- [ ] Add to the bottom of `tests/test_telegram_bot.py`:

```python
def test_broad_section_has_category_header():
    aml_job = make_job(title="AML Analyst", url="https://example.com/aml", is_strict=False)
    messages = split_into_messages([], [aml_job], [], date_str="26 Mar 2026")
    full = "\n".join(messages)
    assert "🔵 AML" in full  # verify the category header specifically, not just the job title

def test_empty_category_not_in_output():
    # Un job de KYC — no debería aparecer "Financial Crimes" en el mensaje
    kyc_job = make_job(title="KYC Manager", url="https://example.com/kyc", is_strict=False)
    messages = split_into_messages([], [kyc_job], [], date_str="26 Mar 2026")
    full = "\n".join(messages)
    assert "Financial Crimes" not in full

def test_summary_block_shows_top3():
    top3 = [
        {**make_job(title="Financial Crimes Analyst", url="https://example.com/1"), "score": 0.85},
        {**make_job(title="AML Investigator", url="https://example.com/2"), "score": 0.72},
    ]
    messages = split_into_messages([], [], top3, date_str="26 Mar 2026")
    full = "\n".join(messages)
    assert "TOP 3" in full
    assert "Financial Crimes Analyst" in full

def test_summary_block_absent_when_no_top3():
    messages = split_into_messages([], [], [], date_str="26 Mar 2026")
    full = "\n".join(messages)
    assert "TOP 3" not in full
```

- [ ] Run to confirm category/summary tests fail (split_into_messages still has old signature):

```bash
python3 -m pytest tests/test_telegram_bot.py -k "category or summary or empty_cat" -v
```
Expected: TypeError or AssertionError.

### Step 3: Rewrite split_into_messages and update format_report / send_report

- [ ] First, update the import block at the **top** of `notifier/telegram_bot.py`. After the existing `from typing import List` line, add:

```python
from filters.job_filter import categorize_job, CATEGORY_ORDER
```

- [ ] Then replace everything from `def split_into_messages` through the end of the file (lines 45–113) with the following block:

```python
# Category icons
_CATEGORY_ICONS = {
    "AML": "🔵",
    "Financial Crimes": "🟠",
    "KYC": "🟢",
    "Compliance": "🟡",
    "Otras": "⚪",
}


def split_into_messages(
    strict: List[dict],
    broad: List[dict],
    top3: List[dict],
    date_str: str,
) -> List[str]:
    """
    Construye mensajes de Telegram respetando el límite de 4096 chars.
    STRICT: todos juntos. BROAD: agrupados por categoría.
    """
    today = date_str
    next_monday = (date.today() + timedelta(days=(7 - date.today().weekday()) % 7 or 7)).strftime("%d %b %Y")

    header = f"🔍 Job Hunt Report — {today}\n\n"

    # Build summary block
    summary_lines = [f"\n{DIVIDER}", f"📊 Total nuevas: {len(strict) + len(broad)} | 🗓️ Próximo: {next_monday}"]
    if top3:
        summary_lines.append("\n🏆 TOP 3 PARA TU PERFIL")
        for i, job in enumerate(top3, 1):
            pct = int(job.get("score", 0) * 100)
            summary_lines.append(f"{i}. {job.get('title', '?')} — {job.get('company', '?')} ({pct}%)")
    footer = "\n".join(summary_lines)

    messages = []
    current = header

    def flush_section(title: str, jobs: List[dict]):
        nonlocal current
        section_header = f"{DIVIDER}\n{title} ({len(jobs)} ofertas)\n{DIVIDER}\n\n"

        if len(current) + len(section_header) > TELEGRAM_LIMIT:
            messages.append(current.rstrip())
            current = section_header
        else:
            current += section_header

        for i, job in enumerate(jobs, 1):
            entry = _truncate_entry_if_needed(format_job_entry(job, i))
            entry_block = entry + "\n\n"

            if len(current) + len(entry_block) > TELEGRAM_LIMIT:
                messages.append(current.rstrip())
                current = f"(cont.) {title}\n\n" + entry_block
            else:
                current += entry_block

    # STRICT section — unchanged structure
    flush_section("🎯 LISTA ESTRICTA", strict)

    # BROAD section — grouped by category
    if broad:
        broad_header = f"{DIVIDER}\n📋 LISTA AMPLIA ({len(broad)} ofertas)\n{DIVIDER}\n\n"
        if len(current) + len(broad_header) > TELEGRAM_LIMIT:
            messages.append(current.rstrip())
            current = broad_header
        else:
            current += broad_header

        # Group by category in display order
        categorized: dict = {cat: [] for cat in CATEGORY_ORDER}
        for job in broad:
            cat = categorize_job(job)
            categorized[cat].append(job)

        for cat in CATEGORY_ORDER:
            jobs_in_cat = categorized[cat]
            if not jobs_in_cat:
                continue
            icon = _CATEGORY_ICONS.get(cat, "⚪")
            cat_header = f"{icon} {cat} ({len(jobs_in_cat)} oferta{'s' if len(jobs_in_cat) != 1 else ''})\n"
            if len(current) + len(cat_header) > TELEGRAM_LIMIT:
                messages.append(current.rstrip())
                current = cat_header
            else:
                current += cat_header

            for i, job in enumerate(jobs_in_cat, 1):
                entry = _truncate_entry_if_needed(format_job_entry(job, i))
                entry_block = entry + "\n\n"
                if len(current) + len(entry_block) > TELEGRAM_LIMIT:
                    messages.append(current.rstrip())
                    current = f"(cont.) {cat}\n\n" + entry_block
                else:
                    current += entry_block

    # Append footer
    if len(current) + len(footer) > TELEGRAM_LIMIT:
        messages.append(current.rstrip())
        messages.append(footer.strip())
    else:
        current += footer
        messages.append(current.rstrip())

    return messages


def format_report(strict: List[dict], broad: List[dict], top3: List[dict]) -> List[str]:
    """Punto de entrada: genera lista de mensajes de Telegram."""
    date_str = date.today().strftime("%d %b %Y")
    return split_into_messages(strict, broad, top3, date_str)


async def send_report(strict: List[dict], broad: List[dict], top3: List[dict]) -> None:
    """Envía el reporte a Telegram."""
    import config
    from telegram import Bot

    bot = Bot(token=config.TELEGRAM_TOKEN)
    messages = format_report(strict, broad, top3)

    for msg in messages:
        await bot.send_message(
            chat_id=config.TELEGRAM_CHAT_ID,
            text=msg,
            disable_web_page_preview=True,
        )
    logger.info(f"Telegram: {len(messages)} mensaje(s) enviado(s)")
```

**Important:** Remove the old `split_into_messages`, `format_report`, and `send_report` functions entirely and replace with the code above. Also add the import of `categorize_job` and `CATEGORY_ORDER` at the top of the file.

The existing imports at the top of `telegram_bot.py`:
```python
import logging
from datetime import date, timedelta
from typing import List
```
Add after the existing imports:
```python
from filters.job_filter import categorize_job, CATEGORY_ORDER
```

### Step 4: Update main.py call site

- [ ] In `main.py`, replace the `send_report` call (line 100):

```python
# BEFORE:
        asyncio.run(send_report(analyzed["strict"], analyzed["broad"]))
# AFTER:
        asyncio.run(send_report(analyzed["strict"], analyzed["broad"], analyzed["top3"]))
```

### Step 5: Run full test suite

- [ ] Run:

```bash
python3 -m pytest tests/ -v
```
Expected: All tests pass. Count should be 33 (original) + 6 (categorize_job) + 4 (salary) + 4 (analyze_jobs top3) + 4 (split/format) = 51 tests.

### Step 6: Final commit

- [ ] Commit:

```bash
git add notifier/telegram_bot.py main.py tests/test_telegram_bot.py
git commit -m "feat: category grouping in broad section and TOP 3 summary block"
```

---

## Final Verification

- [ ] Run full test suite one last time:

```bash
python3 -m pytest tests/ -v
```
Expected: All tests pass.

- [ ] Run a live pipeline test (no Telegram credentials needed — will fail gracefully at the send step):

```bash
python3 -c "
from scrapers.remote_ok import fetch_jobs
from filters.job_filter import filter_jobs
from analysis.gap_analyzer import analyze_jobs

jobs = fetch_jobs()
filtered = filter_jobs(jobs)
analyzed = analyze_jobs(filtered['strict'][:3], filtered['broad'][:5])
print(f'top3: {len(analyzed[\"top3\"])} jobs')
for j in analyzed['top3']:
    print(f'  {j[\"title\"]} | score={j[\"score\"]:.2f}')
"
```
Expected: top3 printed with titles and scores.
