---
aliases: ["job-hunter (2026-03-24)"]
---
# Job Hunter Automatizado — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a weekly automated system that scrapes Compliance/AML crypto job listings from 4 sources, filters them into strict/broad lists, analyzes skill gaps with keywords + Claude, and sends a Telegram report every Monday at 8 AM.

**Architecture:** Modular pipeline — independent scrapers (ThreadPoolExecutor) → deduplication → filter → gap analysis → Telegram notifier. Each module is independently testable. `main.py` orchestrates in sequence.

**Tech Stack:** Python 3.9+, requests, BeautifulSoup4, playwright (Chromium), anthropic SDK, python-telegram-bot, python-dotenv, pytest, macOS launchd

**Spec:** `docs/superpowers/specs/2026-03-24-job-hunter-design.md`

---

## File Map

| File | Responsibility |
|------|---------------|
| `config.py` | Load env vars + define skills/companies lists |
| `prompts.py` | Claude prompt constants |
| `storage/store.py` | Read/write/prune `seen_jobs.json` with TTL |
| `scrapers/remote_ok.py` | Fetch jobs from Remote OK public JSON API |
| `scrapers/crypto_jobs_list.py` | Scrape cryptojobslist.com with requests+BS4 |
| `scrapers/web3_career.py` | Scrape web3.career with requests+BS4 |
| `scrapers/linkedin.py` | Scrape LinkedIn with Playwright headless |
| `filters/job_filter.py` | Filter jobs into strict and broad lists |
| `analysis/gap_analyzer.py` | Keyword scoring + Claude gap analysis |
| `notifier/telegram_bot.py` | Format and send Telegram messages |
| `main.py` | Orchestrator — runs full pipeline |
| `com.your_usernamejobhunter.plist` | launchd schedule (Monday 8AM) |
| `setup.sh` | Install script: deps + launchd registration |
| `requirements.txt` | Python dependencies |
| `.gitignore` | Exclude .env, logs/, storage/seen_jobs.* |
| `tests/test_store.py` | Tests for storage layer |
| `tests/test_filter.py` | Tests for job_filter |
| `tests/test_gap_analyzer.py` | Tests for gap_analyzer (level 1 only) |
| `tests/test_telegram_bot.py` | Tests for message formatting |

---

## Task 1: Project Scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `scrapers/__init__.py`
- Create: `filters/__init__.py`
- Create: `analysis/__init__.py`
- Create: `notifier/__init__.py`
- Create: `storage/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p scrapers filters analysis notifier storage tests logs
touch scrapers/__init__.py filters/__init__.py analysis/__init__.py
touch notifier/__init__.py storage/__init__.py tests/__init__.py
touch logs/.gitkeep  # git no trackea directorios vacíos
```

- [ ] **Step 2: Create `requirements.txt`**

```
requests==2.31.0
beautifulsoup4==4.12.3
playwright==1.44.0
anthropic==0.28.0
python-dotenv==1.0.1
python-telegram-bot==21.3
pytest==8.2.0
pytest-mock==3.14.0
```

- [ ] **Step 3: Create `.gitignore`**

```
.env
logs/
storage/seen_jobs.json
storage/seen_jobs.tmp
__pycache__/
*.pyc
.pytest_cache/
```

- [ ] **Step 4: Create `.env.example`**

```
TELEGRAM_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
LINKEDIN_EMAIL=your_linkedin_email
LINKEDIN_PASSWORD=your_linkedin_password
ANTHROPIC_API_KEY=your_anthropic_key
```

- [ ] **Step 5: Create empty `storage/seen_jobs.json`**

```bash
echo '[]' > storage/seen_jobs.json
```

- [ ] **Step 6: Commit**

```bash
git add requirements.txt .gitignore .env.example scrapers/ filters/ analysis/ notifier/ storage/__init__.py tests/ logs/.gitkeep
git commit -m "chore: project scaffolding and directory structure"
```

---

## Task 2: config.py y prompts.py

**Files:**
- Create: `config.py`
- Create: `prompts.py`

- [ ] **Step 1: Create `config.py`**

```python
import os
from dotenv import load_dotenv

load_dotenv()

# Credenciales desde .env
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL", "")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Skills hardcodeadas (editar aquí, no en .env)
SKILLS_HAVE = [
    "CAMS", "KYC", "AML", "BSA", "FinCEN", "OFAC",
    "SAR", "CTR", "FATF", "Travel Rule",
]

SKILLS_LEARNING = [
    "Chainalysis", "Elliptic", "TRM Labs",
    "blockchain analytics", "MLRO",
]

ALL_SKILLS = SKILLS_HAVE + SKILLS_LEARNING

# Empresas conocidas del ecosistema crypto
KNOWN_CRYPTO_COMPANIES = [
    "Coinbase", "Kraken", "Binance", "Circle", "Gemini",
    "Chainalysis", "Elliptic", "TRM Labs", "Fireblocks",
    "Anchorage", "BitGo", "Paxos", "Ripple", "Consensys",
    "OpenSea", "Uniswap", "Aave", "Compound", "Celsius",
]

# Prioridad de fuentes para tiebreaking (menor índice = mayor prioridad)
SOURCE_PRIORITY = ["remote_ok", "crypto_jobs_list", "web3_career", "linkedin"]
```

- [ ] **Step 2: Create `prompts.py`**

```python
GAP_ANALYSIS_PROMPT = """\
Dado el perfil the user (estudiando CAMS, conocimientos en KYC/AML/BSA/FinCEN/OFAC,
buscando rol remoto en crypto compliance), analiza esta oferta e indica:
1) qué requisitos ya cumple
2) qué le falta específicamente
3) una recomendación concreta de cómo cerrar esa brecha

Sé conciso. Máximo 200 palabras en total.

Oferta:
{job_description}
"""
```

- [ ] **Step 3: Commit**

```bash
git add config.py prompts.py
git commit -m "feat: add config and prompts modules"
```

---

## Task 3: Storage Layer (seen_jobs.json)

**Files:**
- Create: `storage/store.py`
- Create: `tests/test_store.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_store.py
import json
import os
import pytest
from datetime import date, timedelta
from unittest.mock import patch
from storage.store import load_seen_urls, save_seen_urls, is_new_job, mark_as_seen, prune_old_entries

FAKE_PATH = "tests/fixtures/seen_jobs_test.json"

@pytest.fixture(autouse=True)
def cleanup():
    yield
    for f in [FAKE_PATH, FAKE_PATH.replace(".json", ".tmp")]:
        if os.path.exists(f):
            os.remove(f)

def test_load_empty_file(tmp_path):
    p = tmp_path / "seen.json"
    p.write_text("[]")
    assert load_seen_urls(str(p)) == []

def test_load_nonexistent_file(tmp_path):
    p = tmp_path / "notexist.json"
    assert load_seen_urls(str(p)) == []

def test_is_new_job_true():
    seen = [{"url": "https://a.com", "date_seen": "2026-03-01"}]
    assert is_new_job("https://b.com", seen) is True

def test_is_new_job_false():
    seen = [{"url": "https://a.com", "date_seen": "2026-03-01"}]
    assert is_new_job("https://a.com", seen) is False

def test_mark_as_seen_adds_entry():
    seen = []
    today = date.today().isoformat()
    result = mark_as_seen("https://new.com", seen)
    assert len(result) == 1
    assert result[0]["url"] == "https://new.com"
    assert result[0]["date_seen"] == today

def test_prune_removes_old_entries():
    old_date = (date.today() - timedelta(days=91)).isoformat()
    recent_date = date.today().isoformat()
    seen = [
        {"url": "https://old.com", "date_seen": old_date},
        {"url": "https://new.com", "date_seen": recent_date},
    ]
    result = prune_old_entries(seen, ttl_days=90)
    assert len(result) == 1
    assert result[0]["url"] == "https://new.com"

def test_save_is_atomic(tmp_path):
    p = tmp_path / "seen.json"
    seen = [{"url": "https://a.com", "date_seen": "2026-03-24"}]
    save_seen_urls(seen, str(p))
    assert p.exists()
    assert not (tmp_path / "seen.tmp").exists()
    data = json.loads(p.read_text())
    assert data == seen
```

- [ ] **Step 2: Run tests — deben fallar**

```bash
pytest tests/test_store.py -v
```
Expected: `ModuleNotFoundError` o `ImportError`

- [ ] **Step 3: Implement `storage/store.py`**

```python
import json
import os
from datetime import date, timedelta
from typing import List

SEEN_JOBS_PATH = "storage/seen_jobs.json"


def load_seen_urls(path: str = SEEN_JOBS_PATH) -> List[dict]:
    """Carga el historial de URLs vistas. Devuelve [] si no existe o está corrupto."""
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def save_seen_urls(seen: List[dict], path: str = SEEN_JOBS_PATH) -> None:
    """Escritura atómica: escribe a .tmp y renombra."""
    tmp_path = path.replace(".json", ".tmp")
    with open(tmp_path, "w") as f:
        json.dump(seen, f, indent=2)
    os.replace(tmp_path, path)


def is_new_job(url: str, seen: List[dict]) -> bool:
    """Devuelve True si la URL no fue vista antes."""
    seen_urls = {entry["url"] for entry in seen}
    return url not in seen_urls


def mark_as_seen(url: str, seen: List[dict]) -> List[dict]:
    """Agrega una URL al historial con la fecha de hoy."""
    return seen + [{"url": url, "date_seen": date.today().isoformat()}]


def prune_old_entries(seen: List[dict], ttl_days: int = 90) -> List[dict]:
    """Elimina entradas con date_seen de más de ttl_days días."""
    cutoff = date.today() - timedelta(days=ttl_days)
    result = []
    for entry in seen:
        try:
            entry_date = date.fromisoformat(entry["date_seen"])
            if entry_date >= cutoff:
                result.append(entry)
        except (ValueError, KeyError):
            pass
    return result
```

- [ ] **Step 4: Run tests — deben pasar**

```bash
pytest tests/test_store.py -v
```
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add storage/store.py tests/test_store.py
git commit -m "feat: storage layer with TTL and atomic write"
```

---

## Task 4: Job Filter

**Files:**
- Create: `filters/job_filter.py`
- Create: `tests/test_filter.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_filter.py
import pytest
from filters.job_filter import filter_jobs

def make_job(**kwargs):
    defaults = {
        "title": "Test Job",
        "company": "TestCo",
        "location": "Remote",
        "url": "https://example.com/job/1",
        "description": "AML compliance role in crypto blockchain",
        "source": "remote_ok",
        "date_posted": "2026-03-24",
        "salary_min": None,
        "salary_max": None,
    }
    defaults.update(kwargs)
    return defaults

def test_strict_list_requires_remote_role_and_sector():
    job = make_job(location="Remote", description="AML Compliance crypto blockchain")
    result = filter_jobs([job])
    assert job in result["strict"]

def test_strict_rejects_non_remote():
    job = make_job(location="New York", description="AML Compliance crypto blockchain")
    result = filter_jobs([job])
    assert job not in result["strict"]

def test_strict_rejects_missing_role_keyword():
    job = make_job(location="Remote", description="blockchain crypto developer")
    result = filter_jobs([job])
    assert job not in result["strict"]

def test_strict_rejects_missing_sector_keyword():
    job = make_job(location="Remote", description="AML Compliance banking")
    result = filter_jobs([job])
    assert job not in result["strict"]

def test_broad_requires_two_criteria():
    # Solo tiene 'remote' — no pasa
    job = make_job(location="Remote", description="Software engineer Java")
    result = filter_jobs([job])
    assert job not in result["broad"]

def test_broad_passes_with_remote_and_role():
    job = make_job(location="Remote", description="KYC analyst banking")
    result = filter_jobs([job])
    assert job in result["broad"]

def test_broad_passes_with_known_company():
    job = make_job(location="On-site", company="Coinbase", description="AML analyst")
    result = filter_jobs([job])
    assert job in result["broad"]

def test_hybrid_appears_in_broad_not_strict():
    job = make_job(location="Hybrid", description="AML crypto compliance")
    result = filter_jobs([job])
    assert job not in result["strict"]
    assert job in result["broad"]

def test_no_duplicates_between_lists():
    job = make_job(location="Remote", description="AML crypto blockchain compliance")
    result = filter_jobs([job])
    # Un job puede estar en ambas listas (strict es subconjunto de broad)
    # pero no debe aparecer duplicado dentro de cada lista
    assert result["strict"].count(job) <= 1
    assert result["broad"].count(job) <= 1

def test_discards_irrelevant_jobs():
    job = make_job(location="On-site", description="Software engineer Python Django")
    result = filter_jobs([job])
    assert job not in result["strict"]
    assert job not in result["broad"]
```

- [ ] **Step 2: Run tests — deben fallar**

```bash
pytest tests/test_filter.py -v
```
Expected: `ImportError`

- [ ] **Step 3: Implement `filters/job_filter.py`**

```python
from typing import List, Dict
import config

ROLE_KEYWORDS = ["aml", "anti-money laundering", "compliance", "kyc", "mlro"]
SECTOR_KEYWORDS = ["crypto", "blockchain", "web3", "defi", "exchange"]
REMOTE_KEYWORDS = ["remote", "100% remote"]
HYBRID_KEYWORDS = ["hybrid"]


def _text(job: dict) -> str:
    """Texto combinado para búsqueda de keywords."""
    return (
        (job.get("location") or "") + " " +
        (job.get("description") or "") + " " +
        (job.get("title") or "")
    ).lower()


def _has_keyword(text: str, keywords: list) -> bool:
    return any(kw.lower() in text for kw in keywords)


def _is_remote(text: str) -> bool:
    return _has_keyword(text, REMOTE_KEYWORDS)


def _is_hybrid(text: str) -> bool:
    return _has_keyword(text, HYBRID_KEYWORDS)


def _has_role(text: str) -> bool:
    return _has_keyword(text, ROLE_KEYWORDS)


def _has_sector(text: str) -> bool:
    return _has_keyword(text, SECTOR_KEYWORDS)


def _is_known_company(job: dict) -> bool:
    company = (job.get("company") or "").lower()
    return any(c.lower() in company for c in config.KNOWN_CRYPTO_COMPANIES)


def _passes_strict(job: dict) -> bool:
    text = _text(job)
    return _is_remote(text) and _has_role(text) and _has_sector(text)


def _passes_broad(job: dict) -> bool:
    text = _text(job)
    criteria = [
        _is_remote(text) or _is_hybrid(text),
        _has_role(text),
        _has_sector(text),
        _is_known_company(job),
    ]
    return sum(criteria) >= 2


def filter_jobs(jobs: List[dict]) -> Dict[str, List[dict]]:
    """
    Recibe lista de jobs, devuelve {"strict": [...], "broad": [...]}.
    strict: cumple TODOS (remote + rol + sector)
    broad: cumple AL MENOS 2 de 4 criterios
    """
    strict = [j for j in jobs if _passes_strict(j)]
    broad = [j for j in jobs if _passes_broad(j)]
    return {"strict": strict, "broad": broad}
```

- [ ] **Step 4: Run tests — deben pasar**

```bash
pytest tests/test_filter.py -v
```
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add filters/job_filter.py tests/test_filter.py
git commit -m "feat: job filter with strict and broad lists"
```

---

## Task 5: Gap Analyzer (Nivel 1 — Keywords)

**Files:**
- Create: `analysis/gap_analyzer.py`
- Create: `tests/test_gap_analyzer.py`

- [ ] **Step 1: Write failing tests (solo nivel 1)**

```python
# tests/test_gap_analyzer.py
import pytest
from analysis.gap_analyzer import score_job, select_top_jobs

def make_job(description, source="remote_ok", date_posted="2026-03-24", is_strict=True):
    return {
        "title": "AML Analyst",
        "company": "TestCo",
        "location": "Remote",
        "url": "https://example.com/job/1",
        "description": description,
        "source": source,
        "date_posted": date_posted,
        "salary_min": None,
        "salary_max": None,
        "_is_strict": is_strict,
    }

def test_score_matches_known_skills():
    job = make_job("This role requires KYC, AML, and BSA knowledge")
    result = score_job(job)
    assert result["score"] > 0
    assert "KYC" in result["skills_matched"] or "kyc" in [s.lower() for s in result["skills_matched"]]

def test_score_identifies_gaps():
    job = make_job("Requires Chainalysis and TRM Labs experience")
    result = score_job(job)
    assert len(result["gaps"]) > 0

def test_score_zero_for_no_skill_match():
    job = make_job("Generic software engineer role with Python")
    result = score_job(job)
    assert result["score"] == 0

def test_select_top_5_returns_at_most_5():
    jobs = [make_job(f"KYC AML BSA FinCEN OFAC job {i}") for i in range(10)]
    top = select_top_jobs(jobs, n=5)
    assert len(top) <= 5

def test_select_top_prefers_higher_score():
    low = make_job("generic compliance job", source="linkedin")
    high = make_job("KYC AML BSA FinCEN OFAC Chainalysis TRM", source="remote_ok")
    top = select_top_jobs([low, high], n=1)
    assert top[0]["url"] == high["url"]

def test_select_top_tiebreak_strict_over_broad():
    strict_job = make_job("KYC AML", source="remote_ok", is_strict=True)
    broad_job = make_job("KYC AML", source="remote_ok", is_strict=False)
    # Mismo score, strict debe ganar
    top = select_top_jobs([broad_job, strict_job], n=1)
    assert top[0]["_is_strict"] is True

def test_select_top_tiebreak_source_priority():
    job_linkedin = make_job("KYC AML", source="linkedin", is_strict=True)
    job_remote_ok = make_job("KYC AML", source="remote_ok", is_strict=True)
    top = select_top_jobs([job_linkedin, job_remote_ok], n=1)
    assert top[0]["source"] == "remote_ok"

def test_select_top_tiebreak_date_recency():
    older = make_job("KYC AML", source="remote_ok", date_posted="2026-01-01", is_strict=True)
    newer = make_job("KYC AML", source="remote_ok", date_posted="2026-03-24", is_strict=True)
    # Mismo score, mismo strict, misma fuente — la más reciente debe ganar
    top = select_top_jobs([older, newer], n=1)
    assert top[0]["date_posted"] == "2026-03-24"
```

- [ ] **Step 2: Run tests — deben fallar**

```bash
pytest tests/test_gap_analyzer.py -v
```
Expected: `ImportError`

- [ ] **Step 3: Implement `analysis/gap_analyzer.py` (nivel 1 solamente)**

```python
import logging
from typing import List, Optional
import config
import prompts

logger = logging.getLogger(__name__)

SOURCE_PRIORITY = {src: i for i, src in enumerate(config.SOURCE_PRIORITY)}


def _find_skills_in_text(text: str, skills: list) -> list:
    """Devuelve las skills que aparecen en el texto (case-insensitive)."""
    text_lower = text.lower()
    return [s for s in skills if s.lower() in text_lower]


def score_job(job: dict) -> dict:
    """
    Nivel 1: analiza keywords del job contra el perfil the user.
    - skills_matched: skills que the user YA TIENE o está aprendiendo, mencionadas en la oferta
    - gaps: skills de SKILLS_LEARNING mencionadas en la oferta (conoce el concepto, le falta práctica)
            más cualquier skill de dominio conocida no en el perfil the user
    - score: skills_matched / total_skills_in_job
    """
    text = (job.get("description") or "") + " " + (job.get("title") or "")

    # Skills que the user tiene
    skills_matched = _find_skills_in_text(text, config.SKILLS_HAVE)
    # Skills que the user está aprendiendo (aparecen en la oferta — gap real de experiencia práctica)
    skills_learning_in_job = _find_skills_in_text(text, config.SKILLS_LEARNING)
    # Total de skills relevantes detectadas en la oferta
    all_detected = skills_matched + skills_learning_in_job

    # Brechas: skills en el job que the user NO tiene (solo está aprendiendo o no conoce)
    gaps = skills_learning_in_job

    total = len(all_detected) if all_detected else 1  # evitar división por cero
    score = len(skills_matched) / total

    return {
        **job,
        "score": score,
        "skills_matched": skills_matched,
        "gaps": gaps,
        "claude_analysis": None,
    }


def select_top_jobs(jobs: List[dict], n: int = 5) -> List[dict]:
    """
    Selecciona los top N jobs por score.
    Tiebreaker: score DESC → strict > broad → date_posted DESC → source priority ASC.
    """
    def sort_key(j):
        is_strict = 1 if j.get("_is_strict") else 0
        # Negar la fecha (string ISO 8601) para ordenar descendente
        # "2026-03-24" → prefijo negativo via tupla negada char a char es innecesario;
        # usamos un truco simple: prefixar con '-' no funciona en strings, así que
        # comparamos como string directamente (ISO 8601 ordena bien lexicográficamente)
        # y pasamos reverse=True solo para el campo date via negación del score de fecha.
        # Solución limpia: convertir a int YYYYMMDD y negar.
        date_str = (j.get("date_posted") or "0000-00-00").replace("-", "")
        date_int = int(date_str) if date_str.isdigit() else 0
        source_rank = SOURCE_PRIORITY.get(j.get("source", ""), 99)
        return (-j.get("score", 0), -is_strict, -date_int, source_rank)

    return sorted(jobs, key=sort_key)[:n]


def analyze_jobs(strict: List[dict], broad: List[dict]) -> dict:
    """
    Punto de entrada principal. Scores todos los jobs y llama a Claude para el top 5.
    Devuelve {"strict": [...], "broad": [...]} con campos score/gaps/claude_analysis añadidos.
    """
    # Marcar origen para tiebreaking
    strict_scored = [score_job({**j, "_is_strict": True}) for j in strict]
    broad_scored = [score_job({**j, "_is_strict": False}) for j in broad]

    strict_urls = {j["url"] for j in strict_scored}
    all_jobs = strict_scored + [j for j in broad_scored if j["url"] not in strict_urls]
    top5 = select_top_jobs(all_jobs, n=5)

    # Nivel 2: Claude analysis para top 5
    for job in top5:
        job["claude_analysis"] = _get_claude_analysis(job)

    # Reconstruir listas con análisis añadido
    top5_urls = {j["url"] for j in top5}

    def enrich(job_list):
        enriched = []
        for j in job_list:
            match = next((t for t in top5 if t["url"] == j["url"]), None)
            enriched.append(match if match else j)
        return enriched

    return {"strict": enrich(strict_scored), "broad": enrich(broad_scored)}


def _get_claude_analysis(job: dict) -> Optional[str]:
    """Nivel 2: llama a Claude para análisis de brechas. Devuelve None si falla."""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        prompt = prompts.GAP_ANALYSIS_PROMPT.format(
            job_description=f"{job.get('title', '')} at {job.get('company', '')}\n\n{job.get('description', '')}"
        )
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text
    except Exception as e:
        logger.warning(f"Claude analysis failed for {job.get('url')}: {e}")
        return None
```

- [ ] **Step 4: Run tests — deben pasar**

```bash
pytest tests/test_gap_analyzer.py -v
```
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add analysis/gap_analyzer.py tests/test_gap_analyzer.py
git commit -m "feat: gap analyzer with keyword scoring and Claude analysis"
```

---

## Task 6: Telegram Notifier

**Files:**
- Create: `notifier/telegram_bot.py`
- Create: `tests/test_telegram_bot.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_telegram_bot.py
import pytest
from notifier.telegram_bot import format_job_entry, split_into_messages, format_report

TELEGRAM_LIMIT = 4096

def make_job(title="AML Analyst", company="Kraken", location="Remote",
             url="https://example.com/1", skills_matched=None, gaps=None,
             claude_analysis=None, is_strict=True):
    return {
        "title": title,
        "company": company,
        "location": location,
        "url": url,
        "description": "AML compliance crypto",
        "source": "remote_ok",
        "date_posted": "2026-03-24",
        "salary_min": None,
        "salary_max": None,
        "_is_strict": is_strict,
        "score": 0.8,
        "skills_matched": skills_matched or ["KYC", "AML"],
        "gaps": gaps or ["Chainalysis"],
        "claude_analysis": claude_analysis,
    }

def test_format_job_contains_title_and_company():
    job = make_job()
    entry = format_job_entry(job, 1)
    assert "AML Analyst" in entry
    assert "Kraken" in entry

def test_format_job_contains_url():
    job = make_job()
    entry = format_job_entry(job, 1)
    assert "https://example.com/1" in entry

def test_format_job_shows_gaps():
    job = make_job(gaps=["Chainalysis", "TRM Labs"])
    entry = format_job_entry(job, 1)
    assert "Chainalysis" in entry

def test_format_job_includes_claude_analysis_when_present():
    job = make_job(claude_analysis="Te falta experiencia práctica con Chainalysis.")
    entry = format_job_entry(job, 1)
    assert "Te falta experiencia" in entry

def test_format_job_hybrid_has_warning():
    job = make_job(location="Hybrid")
    entry = format_job_entry(job, 1)
    assert "⚠️" in entry

def test_split_messages_respects_limit():
    jobs = [make_job(title=f"Job {i}", url=f"https://example.com/{i}") for i in range(20)]
    strict = jobs[:10]
    broad = jobs[10:]
    messages = split_into_messages(strict, broad, date_str="24 Mar 2026")
    for msg in messages:
        assert len(msg) <= TELEGRAM_LIMIT

def test_split_never_cuts_mid_entry():
    # Job con descripción larga
    long_analysis = "X" * 3000
    job = make_job(claude_analysis=long_analysis)
    messages = split_into_messages([job], [], date_str="24 Mar 2026")
    # Si la entrada excede el límite, debe estar truncada, no cortada
    for msg in messages:
        assert len(msg) <= TELEGRAM_LIMIT

def test_format_report_returns_list_of_strings():
    strict = [make_job()]
    broad = [make_job(title="Compliance Officer", url="https://example.com/2", is_strict=False)]
    messages = format_report(strict, broad)
    assert isinstance(messages, list)
    assert all(isinstance(m, str) for m in messages)
```

- [ ] **Step 2: Run tests — deben fallar**

```bash
pytest tests/test_telegram_bot.py -v
```
Expected: `ImportError`

- [ ] **Step 3: Implement `notifier/telegram_bot.py`**

```python
import logging
from datetime import date, timedelta
from typing import List

logger = logging.getLogger(__name__)

TELEGRAM_LIMIT = 4096
DIVIDER = "━" * 22


def format_job_entry(job: dict, index: int) -> str:
    """Formatea una oferta como string para Telegram."""
    location = job.get("location", "")
    hybrid_warning = " ⚠️" if any(w in location.lower() for w in ["hybrid", "on-site", "presencial"]) else ""

    skills_str = ", ".join(job.get("skills_matched") or []) or "—"
    gaps_str = ", ".join(job.get("gaps") or []) or "Ninguna detectada"

    lines = [
        f"{index}. {job.get('title', '?')} — {job.get('company', '?')}",
        f"   📍 {location}{hybrid_warning} | 🔗 {job.get('url', '')}",
        f"   ✅ Cumples: {skills_str}",
        f"   ❌ Te falta: {gaps_str}",
    ]

    if job.get("claude_analysis"):
        analysis = job["claude_analysis"]
        lines.append(f"   🤖 {analysis}")

    return "\n".join(lines)


def _truncate_entry_if_needed(entry: str, max_len: int = TELEGRAM_LIMIT) -> str:
    """Si una entrada individual excede el límite, trunca el análisis Claude."""
    if len(entry) <= max_len:
        return entry
    # Truncar en el marcador de Claude
    cut_marker = "   🤖 "
    idx = entry.find(cut_marker)
    if idx != -1:
        truncated = entry[:idx] + cut_marker + "[Análisis omitido por longitud]"
        return truncated[:max_len]
    return entry[:max_len]


def split_into_messages(strict: List[dict], broad: List[dict], date_str: str) -> List[str]:
    """
    Construye mensajes de Telegram respetando el límite de 4096 chars.
    La división ocurre solo en límites de oferta completa.
    """
    today = date_str
    next_monday = (date.today() + timedelta(days=(7 - date.today().weekday()) % 7 or 7)).strftime("%d %b %Y")

    header = f"🔍 Job Hunt Report — {today}\n\n"
    footer = f"\n{DIVIDER}\n📊 Total nuevas esta semana: {len(strict) + len(broad)}\n🗓️ Próximo reporte: {next_monday}"

    messages = []
    current = header

    def flush_section(title: str, jobs: List[dict]):
        nonlocal current
        section_header = f"{DIVIDER}\n{title} ({len(jobs)} ofertas)\n{DIVIDER}\n\n"

        # ¿cabe el header de sección en el mensaje actual?
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
                current = entry_block
            else:
                current += entry_block

    flush_section("🎯 LISTA ESTRICTA", strict)
    flush_section("📋 LISTA AMPLIA", broad)

    # Footer
    if len(current) + len(footer) > TELEGRAM_LIMIT:
        messages.append(current.rstrip())
        messages.append(footer.strip())
    else:
        current += footer
        messages.append(current.rstrip())

    return messages


def format_report(strict: List[dict], broad: List[dict]) -> List[str]:
    """Punto de entrada: genera lista de mensajes de Telegram."""
    date_str = date.today().strftime("%d %b %Y")
    return split_into_messages(strict, broad, date_str)


async def send_report(strict: List[dict], broad: List[dict]) -> None:
    """Envía el reporte a Telegram."""
    import config
    from telegram import Bot

    bot = Bot(token=config.TELEGRAM_TOKEN)
    messages = format_report(strict, broad)

    for msg in messages:
        await bot.send_message(
            chat_id=config.TELEGRAM_CHAT_ID,
            text=msg,
            disable_web_page_preview=True,
        )
    logger.info(f"Telegram: {len(messages)} mensaje(s) enviado(s)")
```

- [ ] **Step 4: Run tests — deben pasar**

```bash
pytest tests/test_telegram_bot.py -v
```
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add notifier/telegram_bot.py tests/test_telegram_bot.py
git commit -m "feat: telegram notifier with message splitting"
```

---

## Task 7: Scraper — Remote OK

**Files:**
- Create: `scrapers/remote_ok.py`

> Remote OK tiene una API pública JSON. Es el scraper más confiable y el mejor punto de partida. No requiere tests unitarios porque depende de red externa — se valida con un smoke test manual.

- [ ] **Step 1: Implement `scrapers/remote_ok.py`**

```python
import logging
import requests
from typing import List

logger = logging.getLogger(__name__)

REMOTE_OK_URL = "https://remoteok.com/api"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; JobHunterBot/1.0)"}


def fetch_jobs() -> List[dict]:
    """Fetches jobs from Remote OK public API. Returns [] on any failure."""
    try:
        response = requests.get(REMOTE_OK_URL, headers=HEADERS, timeout=15)
        response.raise_for_status()
        data = response.json()

        # El primer elemento es metadata legal, los demás son jobs
        jobs_raw = [item for item in data if isinstance(item, dict) and item.get("id")]

        jobs = []
        for item in jobs_raw:
            tags = item.get("tags") or []
            tags_text = " ".join(tags)
            description = (item.get("description") or "") + " " + tags_text

            jobs.append({
                "title": item.get("position", ""),
                "company": item.get("company", ""),
                "location": "Remote",  # Remote OK solo lista trabajos remotos
                "url": item.get("url", ""),
                "description": description.strip(),
                "source": "remote_ok",
                "date_posted": _parse_date(item.get("date", "")),
                "salary_min": _parse_salary(item.get("salary_min")),
                "salary_max": _parse_salary(item.get("salary_max")),
            })

        logger.info(f"remote_ok: {len(jobs)} jobs fetched")
        return jobs

    except Exception as e:
        logger.error(f"remote_ok scraper failed: {e}")
        return []


def _parse_date(raw: str) -> str:
    """Extrae YYYY-MM-DD de la fecha de Remote OK (ISO 8601)."""
    if not raw:
        return ""
    return raw[:10]  # "2026-03-24T00:00:00.000Z" → "2026-03-24"


def _parse_salary(raw) -> int | None:
    try:
        return int(raw) if raw else None
    except (ValueError, TypeError):
        return None
```

- [ ] **Step 2: Smoke test manual**

```bash
python -c "from scrapers.remote_ok import fetch_jobs; jobs = fetch_jobs(); print(f'Fetched {len(jobs)} jobs'); print(jobs[0] if jobs else 'No jobs')"
```
Expected: imprime un número > 0 y el primer job

- [ ] **Step 3: Commit**

```bash
git add scrapers/remote_ok.py
git commit -m "feat: remote_ok scraper using public JSON API"
```

---

## Task 8: Scrapers — Crypto Jobs List y Web3 Career

**Files:**
- Create: `scrapers/crypto_jobs_list.py`
- Create: `scrapers/web3_career.py`

> Ambos usan requests + BeautifulSoup. Los selectores HTML pueden cambiar — el scraper debe fallar gracefully. No hay tests unitarios automáticos (dependen de red); se validan con smoke tests.

- [ ] **Step 1: Implement `scrapers/crypto_jobs_list.py`**

```python
import logging
import requests
from bs4 import BeautifulSoup
from typing import List

logger = logging.getLogger(__name__)

BASE_URL = "https://cryptojobslist.com"
SEARCH_URLS = [
    f"{BASE_URL}/compliance",
    f"{BASE_URL}/aml",
]
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; JobHunterBot/1.0)"}


def fetch_jobs() -> List[dict]:
    """Scrapes Crypto Jobs List. Returns [] on any failure."""
    jobs = []
    seen_urls = set()

    for url in SEARCH_URLS:
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # Selector principal — puede cambiar si actualizan el sitio
            job_cards = soup.select("article.job-card, div[data-job-id], li.job")
            if not job_cards:
                # Fallback: busca cualquier enlace que apunte a /jobs/
                job_cards = soup.select("a[href*='/jobs/']")

            for card in job_cards:
                try:
                    job = _parse_card(card)
                    if job and job["url"] not in seen_urls:
                        seen_urls.add(job["url"])
                        jobs.append(job)
                except Exception as e:
                    logger.debug(f"Error parsing card: {e}")

        except Exception as e:
            logger.error(f"crypto_jobs_list failed for {url}: {e}")

    logger.info(f"crypto_jobs_list: {len(jobs)} jobs fetched")
    return jobs


def _parse_card(card) -> dict | None:
    """Extrae datos de una card de oferta."""
    link = card.find("a") if card.name != "a" else card
    if not link or not link.get("href"):
        return None

    href = link["href"]
    if not href.startswith("http"):
        href = BASE_URL + href

    title_el = card.find(["h2", "h3", "span"], class_=lambda c: c and "title" in c.lower()) if hasattr(card, 'find') else None
    company_el = card.find(["span", "div"], class_=lambda c: c and "company" in c.lower()) if hasattr(card, 'find') else None
    location_el = card.find(["span", "div"], class_=lambda c: c and "location" in c.lower()) if hasattr(card, 'find') else None

    return {
        "title": title_el.get_text(strip=True) if title_el else card.get_text(strip=True)[:80],
        "company": company_el.get_text(strip=True) if company_el else "",
        "location": location_el.get_text(strip=True) if location_el else "Remote",
        "url": href,
        "description": card.get_text(separator=" ", strip=True)[:1000] if hasattr(card, 'get_text') else "",
        "source": "crypto_jobs_list",
        "date_posted": "",
        "salary_min": None,
        "salary_max": None,
    }
```

- [ ] **Step 2: Implement `scrapers/web3_career.py`**

```python
import logging
import requests
from bs4 import BeautifulSoup
from typing import List

logger = logging.getLogger(__name__)

BASE_URL = "https://web3.career"
SEARCH_URLS = [
    f"{BASE_URL}/compliance-jobs",
    f"{BASE_URL}/aml-jobs",
    f"{BASE_URL}/remote+compliance-jobs",
]
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; JobHunterBot/1.0)"}


def fetch_jobs() -> List[dict]:
    """Scrapes Web3 Career. Returns [] on any failure."""
    jobs = []
    seen_urls = set()

    for url in SEARCH_URLS:
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            job_cards = soup.select("tr.job_row, div.job-card, article")
            if not job_cards:
                job_cards = soup.select("a[href*='/job/'], a[href*='/jobs/']")

            for card in job_cards:
                try:
                    job = _parse_card(card)
                    if job and job["url"] not in seen_urls:
                        seen_urls.add(job["url"])
                        jobs.append(job)
                except Exception as e:
                    logger.debug(f"Error parsing card: {e}")

        except Exception as e:
            logger.error(f"web3_career failed for {url}: {e}")

    logger.info(f"web3_career: {len(jobs)} jobs fetched")
    return jobs


def _parse_card(card) -> dict | None:
    link = card.find("a") if card.name != "a" else card
    if not link or not link.get("href"):
        return None

    href = link["href"]
    if not href.startswith("http"):
        href = BASE_URL + href

    title_el = card.find(["h2", "h3", "td"], class_=lambda c: c and ("title" in c.lower() or "position" in c.lower())) if hasattr(card, 'find') else None
    company_el = card.find(["span", "td", "div"], class_=lambda c: c and "company" in c.lower()) if hasattr(card, 'find') else None

    return {
        "title": title_el.get_text(strip=True) if title_el else card.get_text(strip=True)[:80],
        "company": company_el.get_text(strip=True) if company_el else "",
        "location": "Remote",
        "url": href,
        "description": card.get_text(separator=" ", strip=True)[:1000] if hasattr(card, 'get_text') else "",
        "source": "web3_career",
        "date_posted": "",
        "salary_min": None,
        "salary_max": None,
    }
```

- [ ] **Step 3: Smoke tests**

```bash
python -c "from scrapers.crypto_jobs_list import fetch_jobs; jobs = fetch_jobs(); print(f'Crypto Jobs List: {len(jobs)} jobs')"
python -c "from scrapers.web3_career import fetch_jobs; jobs = fetch_jobs(); print(f'Web3 Career: {len(jobs)} jobs')"
```
Expected: números >= 0 (pueden ser 0 si el HTML cambió, pero no deben lanzar excepción)

- [ ] **Step 4: Commit**

```bash
git add scrapers/crypto_jobs_list.py scrapers/web3_career.py
git commit -m "feat: scrapers for Crypto Jobs List and Web3 Career"
```

---

## Task 9: Scraper — LinkedIn

**Files:**
- Create: `scrapers/linkedin.py`

> Requiere credenciales reales para funcionar. Playwright debe estar instalado (`playwright install chromium`). Falla gracefully si no hay credenciales.

- [ ] **Step 1: Implement `scrapers/linkedin.py`**

```python
import logging
from typing import List
import config

logger = logging.getLogger(__name__)

SEARCH_QUERIES = [
    "AML Compliance Crypto Remote",
    "KYC Analyst Blockchain Remote",
]

def fetch_jobs() -> List[dict]:
    """
    Scrapes LinkedIn via Playwright headless.
    ADVERTENCIA: Viola los ToS de LinkedIn. Usar con cuenta secundaria.
    Returns [] si no hay credenciales o si LinkedIn bloquea el acceso.
    """
    if not config.LINKEDIN_EMAIL or not config.LINKEDIN_PASSWORD:
        logger.warning("LinkedIn: credenciales no configuradas — fuente omitida")
        return []

    try:
        from playwright.sync_api import sync_playwright
        return _scrape_with_playwright()
    except ImportError:
        logger.error("LinkedIn: playwright no instalado — ejecuta 'playwright install chromium'")
        return []
    except Exception as e:
        logger.error(f"LinkedIn scraper failed: {e}")
        return []


def _scrape_with_playwright() -> List[dict]:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

    jobs = []
    seen_urls = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = context.new_page()

        # Login
        try:
            page.goto("https://www.linkedin.com/login", timeout=15000)
            page.fill("#username", config.LINKEDIN_EMAIL)
            page.fill("#password", config.LINKEDIN_PASSWORD)
            page.click("button[type=submit]")
            page.wait_for_url("**/feed/**", timeout=15000)
        except PlaywrightTimeout:
            logger.warning("LinkedIn: login timeout o CAPTCHA detectado — fuente omitida")
            browser.close()
            return []

        # Verificar si llegamos al feed (no a CAPTCHA ni challenge)
        if "checkpoint" in page.url or "challenge" in page.url:
            logger.warning("LinkedIn: desafío de seguridad detectado — fuente omitida")
            browser.close()
            return []

        # Búsquedas
        for query in SEARCH_QUERIES:
            try:
                search_url = f"https://www.linkedin.com/jobs/search/?keywords={query.replace(' ', '%20')}&f_WT=2"
                page.goto(search_url, timeout=15000)
                page.wait_for_selector(".jobs-search__results-list, .scaffold-layout__list", timeout=10000)

                cards = page.query_selector_all(".job-card-container, .base-card")
                for card in cards[:25]:
                    try:
                        job = _parse_linkedin_card(card, page)
                        if job and job["url"] not in seen_urls:
                            seen_urls.add(job["url"])
                            jobs.append(job)
                    except Exception as e:
                        logger.debug(f"LinkedIn card parse error: {e}")

            except PlaywrightTimeout:
                logger.warning(f"LinkedIn: timeout en query '{query}'")
            except Exception as e:
                logger.error(f"LinkedIn search failed for '{query}': {e}")

        browser.close()

    logger.info(f"linkedin: {len(jobs)} jobs fetched")
    return jobs


def _parse_linkedin_card(card, page) -> dict | None:
    title_el = card.query_selector(".job-card-list__title, .base-search-card__title")
    company_el = card.query_selector(".job-card-container__company-name, .base-search-card__subtitle")
    location_el = card.query_selector(".job-card-container__metadata-item, .job-search-card__location")
    link_el = card.query_selector("a[href*='/jobs/view/']")

    if not link_el:
        return None

    url = link_el.get_attribute("href") or ""
    if "?" in url:
        url = url.split("?")[0]

    return {
        "title": title_el.inner_text().strip() if title_el else "",
        "company": company_el.inner_text().strip() if company_el else "",
        "location": location_el.inner_text().strip() if location_el else "",
        "url": url,
        "description": card.inner_text().strip()[:500],
        "source": "linkedin",
        "date_posted": "",
        "salary_min": None,
        "salary_max": None,
    }
```

- [ ] **Step 2: Smoke test (solo si tienes credenciales configuradas)**

```bash
python -c "from scrapers.linkedin import fetch_jobs; jobs = fetch_jobs(); print(f'LinkedIn: {len(jobs)} jobs')"
```
Expected: número >= 0 sin excepción no manejada

- [ ] **Step 3: Commit**

```bash
git add scrapers/linkedin.py
git commit -m "feat: LinkedIn scraper with Playwright (graceful failure)"
```

---

## Task 10: Orquestador main.py

**Files:**
- Create: `main.py`

- [ ] **Step 1: Implement `main.py`**

```python
#!/usr/bin/env python3
"""
Job Hunter — Orquestador principal.
Ejecuta el pipeline completo: scraping → dedup → filter → analysis → Telegram.
"""
import asyncio
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

from storage.store import load_seen_urls, save_seen_urls, is_new_job, mark_as_seen, prune_old_entries
from filters.job_filter import filter_jobs
from analysis.gap_analyzer import analyze_jobs
from notifier.telegram_bot import send_report

# Garantizar que logs/ existe antes de inicializar el FileHandler
os.makedirs("logs", exist_ok=True)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("logs/job_hunter.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


def run_scrapers() -> list:
    """Ejecuta todos los scrapers en paralelo. LinkedIn en su propio hilo."""
    from scrapers import remote_ok, crypto_jobs_list, web3_career, linkedin

    scraper_fns = [
        remote_ok.fetch_jobs,
        crypto_jobs_list.fetch_jobs,
        web3_career.fetch_jobs,
        linkedin.fetch_jobs,
    ]

    all_jobs = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(fn): fn.__module__ for fn in scraper_fns}
        for future in as_completed(futures):
            module = futures[future]
            try:
                jobs = future.result()
                logger.info(f"{module}: {len(jobs)} jobs returned")
                all_jobs.extend(jobs)
            except Exception as e:
                logger.error(f"{module} raised exception: {e}")

    return all_jobs


def deduplicate(jobs: list, seen: list) -> list:
    """Filtra jobs ya vistos."""
    new_jobs = [j for j in jobs if j.get("url") and is_new_job(j["url"], seen)]
    logger.info(f"Dedup: {len(jobs)} total → {len(new_jobs)} new")
    return new_jobs


def main():
    logger.info("=== Job Hunter starting ===")
    logger.info(f"Date: {date.today().isoformat()}")

    # 1. Cargar y prunear historial
    seen = load_seen_urls()
    seen = prune_old_entries(seen, ttl_days=90)
    logger.info(f"Seen jobs loaded: {len(seen)} entries after pruning")

    # 2. Scraping
    all_jobs = run_scrapers()
    logger.info(f"Total scraped: {len(all_jobs)} jobs")

    # 3. Deduplicación
    new_jobs = deduplicate(all_jobs, seen)
    if not new_jobs:
        logger.info("No new jobs this week. Skipping Telegram.")
        return

    # 4. Filtrado
    filtered = filter_jobs(new_jobs)
    strict = filtered["strict"]
    broad = filtered["broad"]
    logger.info(f"Filtered: {len(strict)} strict, {len(broad)} broad")

    if not strict and not broad:
        logger.info("No jobs passed filters. Skipping Telegram.")
        return

    # 5. Gap analysis
    analyzed = analyze_jobs(strict, broad)

    # 6. Telegram
    try:
        asyncio.run(send_report(analyzed["strict"], analyzed["broad"]))
        # Marcar como vistos TODOS los jobs nuevos scrapeados (no solo los filtrados),
        # para evitar reprocesar jobs descartados la próxima semana.
        all_new_urls = [j["url"] for j in new_jobs if j.get("url")]
        for url in all_new_urls:
            seen = mark_as_seen(url, seen)
        save_seen_urls(seen)
        logger.info(f"seen_jobs.json updated with {len(all_new_urls)} new entries")
    except Exception as e:
        logger.error(f"Telegram send failed — seen_jobs.json NOT updated: {e}")
        sys.exit(1)

    logger.info("=== Job Hunter completed successfully ===")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Dry run (sin credenciales reales)**

```bash
python main.py
```
Expected: logs visibles en terminal, termina con error de Telegram si no hay token (es esperado en esta fase)

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: main orchestrator with full pipeline"
```

---

## Task 11: launchd plist y setup.sh

**Files:**
- Create: `com.your_usernamejobhunter.plist`
- Create: `setup.sh`

- [ ] **Step 1: Create `com.your_usernamejobhunter.plist`**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.your_usernamejobhunter</string>
  <key>ProgramArguments</key>
  <array>
    <string>PYTHON_PATH_PLACEHOLDER</string>
    <string>WORKING_DIR_PLACEHOLDER/main.py</string>
  </array>
  <key>WorkingDirectory</key>
  <string>WORKING_DIR_PLACEHOLDER</string>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Weekday</key>
    <integer>2</integer>
    <key>Hour</key>
    <integer>8</integer>
    <key>Minute</key>
    <integer>0</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>WORKING_DIR_PLACEHOLDER/logs/job_hunter.log</string>
  <key>StandardErrorPath</key>
  <string>WORKING_DIR_PLACEHOLDER/logs/job_hunter.log</string>
  <key>RunAtLoad</key>
  <false/>
</dict>
</plist>
```

- [ ] **Step 2: Create `setup.sh`**

```bash
#!/bin/bash
set -e

echo "=== Job Hunter Setup ==="

# 1. Enforce .gitignore
if ! grep -q "^\.env$" .gitignore 2>/dev/null; then
    echo ".env" >> .gitignore
    echo "✅ Added .env to .gitignore"
fi

# 2. Verificar Python 3.9+
python3 --version | grep -E "3\.(9|1[0-9])" > /dev/null || {
    echo "❌ Python 3.9+ requerido"
    exit 1
}
echo "✅ Python OK"

# 3. Instalar dependencias
pip install -r requirements.txt
echo "✅ Dependencies installed"

# 4. Instalar Playwright browsers
python3 -m playwright install chromium
echo "✅ Playwright Chromium installed"

# 5. Crear seen_jobs.json si no existe
mkdir -p storage logs
if [ ! -f storage/seen_jobs.json ]; then
    echo '[]' > storage/seen_jobs.json
    echo "✅ storage/seen_jobs.json created"
fi

# 6. Generar plist con rutas absolutas
WORKING_DIR="$(pwd)"
PYTHON_PATH="$(python3 -c 'import sys; print(sys.executable)')"
PLIST_DEST="$HOME/Library/LaunchAgents/com.your_usernamejobhunter.plist"

sed "s|WORKING_DIR_PLACEHOLDER|$WORKING_DIR|g; s|PYTHON_PATH_PLACEHOLDER|$PYTHON_PATH|g" \
    com.your_usernamejobhunter.plist > "$PLIST_DEST"
echo "✅ plist installed to $PLIST_DEST"

# 7. Cargar en launchd
launchctl unload "$PLIST_DEST" 2>/dev/null || true
launchctl load "$PLIST_DEST"
echo "✅ launchd job registered"

echo ""
echo "🚀 Job Hunter instalado."
echo "   Próxima ejecución automática: lunes a las 8:00 AM"
echo "   Para ejecutar ahora: python3 main.py"
echo "   Logs: logs/job_hunter.log"
```

- [ ] **Step 3: Hacer ejecutable setup.sh**

```bash
chmod +x setup.sh
```

- [ ] **Step 4: Commit**

```bash
git add com.your_usernamejobhunter.plist setup.sh
git commit -m "feat: launchd plist and setup.sh installer"
```

---

## Task 12: Run All Tests + Integración Final

- [ ] **Step 1: Ejecutar suite completa de tests**

```bash
pytest tests/ -v
```
Expected: todos los tests en `test_store.py`, `test_filter.py`, `test_gap_analyzer.py`, `test_telegram_bot.py` pasan

- [ ] **Step 2: Verificar que .env no está en git**

```bash
git status
git ls-files .env
```
Expected: `git ls-files .env` no devuelve nada

- [ ] **Step 3: Pipeline dry run con datos reales (Remote OK solamente)**

```python
# Ejecutar en python3 REPL o como script temporal
from scrapers.remote_ok import fetch_jobs
from filters.job_filter import filter_jobs
from analysis.gap_analyzer import analyze_jobs

jobs = fetch_jobs()
print(f"Scraped: {len(jobs)}")
filtered = filter_jobs(jobs)
print(f"Strict: {len(filtered['strict'])}, Broad: {len(filtered['broad'])}")
analyzed = analyze_jobs(filtered['strict'][:2], filtered['broad'][:2])
for j in analyzed['strict']:
    print(f"  {j['title']} | score={j['score']:.2f} | gaps={j['gaps']}")
```

Expected: datos reales procesados sin errores

- [ ] **Step 4: Commit final**

```bash
git add .
git commit -m "chore: final integration test and cleanup"
```

---

## Configuración Requerida Antes de setup.sh

1. Crear `.env` con tus valores reales (ver `.env.example`)
2. Crear un bot de Telegram: hablar con `@BotFather` en Telegram → `/newbot`
3. Obtener tu `TELEGRAM_CHAT_ID`: hablar con `@userinfobot`
4. Tener tu `ANTHROPIC_API_KEY` de console.anthropic.com
5. (Opcional) Preparar cuenta secundaria de LinkedIn

---

## Post-Instalación

```bash
# Verificar que launchd registró el job
launchctl list | grep your_usernamejobhunter

# Ejecutar manualmente para probar
python3 main.py

# Ver logs
tail -f logs/job_hunter.log
```
