---
aliases: ["job-hunter-design (2026-03-24)"]
---
# Job Hunter Automatizado — Spec de Diseño

**Fecha:** 2026-03-24
**Proyecto:** agente-job-hunter
**Usuario:** [candidate]

---

## Objetivo

Sistema automatizado que busca ofertas de trabajo remoto en Compliance/AML crypto cada semana, las filtra por requisitos, analiza las brechas de habilidades del usuario, y envía un reporte por Telegram.

---

## Requisitos

- Ejecutar automáticamente cada lunes a las 8:00 AM (macOS launchd)
- Buscar en: Crypto Jobs List, Web3 Career, Remote OK, LinkedIn
- Filtrar ofertas en dos listas: estricta y amplia
- Analizar brechas de habilidades en dos niveles: keywords + Claude
- Enviar reporte semanal por Telegram
- No reenviar ofertas ya vistas (deduplicación persistente con TTL)
- Fácil de migrar a cloud en el futuro

---

## Arquitectura

### Estructura de archivos

```
agente-job-hunter/
├── main.py                  # Orquestador principal
├── config.py                # Perfil, keywords, tokens desde .env
├── prompts.py               # Prompts de Claude (separados para fácil iteración)
├── .env                     # Credenciales (no commitear — .gitignore enforced)
├── .gitignore               # Incluye .env, logs/, seen_jobs.json
├── setup.sh                 # Instala launchd, verifica deps, enforce .gitignore
├── scrapers/
│   ├── crypto_jobs_list.py  # Scraper cryptojobslist.com
│   ├── web3_career.py       # Scraper web3.career
│   ├── remote_ok.py         # API pública JSON de remoteok.com
│   └── linkedin.py          # Playwright headless con credenciales .env
├── filters/
│   └── job_filter.py        # Produce lista estricta y lista amplia
├── analysis/
│   └── gap_analyzer.py      # Keywords rápidas + análisis Claude (top 5)
├── notifier/
│   └── telegram_bot.py      # Formatea y envía mensajes a Telegram
├── storage/
│   └── seen_jobs.json       # Historial de URLs vistas con fecha (TTL 90 días)
├── logs/
│   └── job_hunter.log       # Logs de ejecución
└── com.your_usernamejobhunter.plist # Configuración launchd
```

### Flujo de datos

```
main.py
  → scrapers/* (ThreadPoolExecutor, LinkedIn en hilo separado)
  → deduplicación contra seen_jobs.json
  → job_filter.py (lista estricta + lista amplia)
  → gap_analyzer.py (keywords rápidas para todas, Claude para top 5)
  → telegram_bot.py (envía reporte)
  → actualizar seen_jobs.json (escritura atómica)
```

---

## Modelo de datos

### Job

Cada oferta es un diccionario estandarizado devuelto por todos los scrapers:

```python
{
  "title": str,           # Título del puesto
  "company": str,         # Nombre de la empresa
  "location": str,        # "Remote", "Hybrid", "On-site", etc.
  "url": str,             # URL única (clave de deduplicación)
  "description": str,     # Texto completo de la oferta
  "source": str,          # "crypto_jobs_list" | "web3_career" | "remote_ok" | "linkedin"
  "date_posted": str,     # ISO 8601: "2026-03-24" (vacío si no disponible)
  "salary_min": int|None, # Opcional — solo Remote OK lo provee en v1
  "salary_max": int|None, # Opcional — solo Remote OK lo provee en v1
}
```

### seen_jobs.json

Schema con TTL — no lista plana:

```json
[
  {"url": "https://...", "date_seen": "2026-03-24"},
  {"url": "https://...", "date_seen": "2026-03-17"}
]
```

URLs con `date_seen` de más de 90 días se eliminan al inicio de cada ejecución (pruning automático). Escritura **atómica**: escribir a `seen_jobs.tmp` y luego renombrar a `seen_jobs.json` para evitar corrupción si el proceso se interrumpe.

---

## Módulos

### scrapers/

Cada scraper es independiente y falla de forma aislada (`try/except`). Si uno falla, los demás continúan. Todos devuelven `list[dict]` con el modelo Job estándar.

Los scrapers corren en paralelo usando `concurrent.futures.ThreadPoolExecutor`. LinkedIn corre en su propio hilo (Playwright no es compatible con `asyncio`).

- **crypto_jobs_list.py:** `requests` + `BeautifulSoup`. Sin autenticación.
- **web3_career.py:** `requests` + `BeautifulSoup`. Sin autenticación.
- **remote_ok.py:** API pública JSON (`https://remoteok.com/api`). Sin autenticación. Mapea campos `tags`, `salary_min`, `salary_max`. Los campos `salary_min`/`salary_max` se incluyen en el modelo Job; los `tags` se usan como texto adicional en `description` para el filtrado de keywords.
- **linkedin.py:** `playwright` headless. Requiere `LINKEDIN_EMAIL` y `LINKEDIN_PASSWORD` en `.env`. Queries: `"AML Compliance Crypto Remote"`, `"KYC Analyst Blockchain Remote"`. Extrae 25 resultados por query.

  **Riesgos de LinkedIn:**
  - El scraping de LinkedIn viola sus Términos de Servicio. Usar con conciencia de este riesgo.
  - LinkedIn puede bloquear la cuenta o presentar CAPTCHA. El scraper detecta redirección a login o CAPTCHA como fallo, lo loguea, y continúa sin LinkedIn.
  - Las credenciales (`LINKEDIN_EMAIL`, `LINKEDIN_PASSWORD`) nunca deben commitearse. `setup.sh` verifica `.gitignore` antes de continuar.
  - Recomendado: usar una cuenta secundaria, no la cuenta principal de LinkedIn.

### filters/job_filter.py

Recibe `list[Job]`, devuelve `{"strict": list[Job], "broad": list[Job]}`.

**Lista Estricta** — cumple TODOS:
1. Mención de "remote" o "100% remote" en `location` o `description` (case-insensitive)
2. Al menos una keyword de rol: `AML`, `Anti-Money Laundering`, `Compliance`, `KYC`, `MLRO`
3. Al menos una keyword de sector: `crypto`, `blockchain`, `Web3`, `DeFi`, `exchange`

**Lista Amplia** — cumple AL MENOS DOS de:
1. Menciona "remote" o "hybrid"
2. Keyword de rol presente
3. Keyword de sector presente
4. Empresa conocida del ecosistema (Coinbase, Kraken, Binance, Circle, Gemini, Chainalysis, etc.)

Todas las keywords son case-insensitive. Ofertas que no pasan ni el filtro amplio se descartan.

### analysis/gap_analyzer.py

**Nivel 1 — Keywords rápidas** (todas las ofertas filtradas):
- Compara keywords detectadas en la oferta contra `config.SKILLS_HAVE` y `config.SKILLS_LEARNING`
- `SKILLS_HAVE`: CAMS, KYC, AML, BSA, FinCEN, OFAC, SAR, CTR, FATF, Travel Rule
- `SKILLS_LEARNING`: Chainalysis, Elliptic, TRM Labs, Blockchain analytics, MLRO
- Produce `score` (keywords del perfil que matchean / total keywords del dominio en la oferta) y lista de brechas

**Nivel 2 — Análisis Claude** (top 5 por score):
- Prompt definido en `prompts.py` (no hardcodeado en gap_analyzer)
- Usa `claude-sonnet-4-6` via Anthropic API
- Resultado incluido en el mensaje Telegram de cada oferta top

**Criterio de selección top 5 con tiebreaker:**
1. Score más alto
2. En empate: preferencia por lista estricta sobre lista amplia
3. En empate: `date_posted` más reciente
4. En empate: orden de fuente: `remote_ok` > `crypto_jobs_list` > `web3_career` > `linkedin`

### prompts.py

Contiene el prompt de Claude como constante editable:

```python
GAP_ANALYSIS_PROMPT = """
Dado el perfil the user (estudiando CAMS, conocimientos en KYC/AML/BSA/FinCEN/OFAC,
buscando rol remoto en crypto compliance), analiza esta oferta e indica:
1) qué requisitos ya cumple
2) qué le falta específicamente
3) una recomendación concreta de cómo cerrar esa brecha

Oferta:
{job_description}
"""
```

### notifier/telegram_bot.py

Formato del reporte:

```
🔍 Job Hunt Report — DD MMM YYYY

━━━━━━━━━━━━━━━━━━━━━━
🎯 LISTA ESTRICTA (N ofertas)
━━━━━━━━━━━━━━━━━━━━━━

1. [Título] — [Empresa]
   📍 [Location] | 🔗 [URL]
   ✅ Cumples: [skills]
   ❌ Te falta: [gaps]
   🤖 [Análisis Claude si aplica]

━━━━━━━━━━━━━━━━━━━━━━
📋 LISTA AMPLIA (N ofertas)
━━━━━━━━━━━━━━━━━━━━━━

...

━━━━━━━━━━━━━━━━━━━━━━
📊 Total nuevas esta semana: N
🗓️ Próximo reporte: DD MMM YYYY
```

**División de mensajes:** El límite de Telegram es 4096 caracteres por mensaje. La división se hace **solo en límites de oferta completa** — nunca en mitad de una entrada. Cada entrada de oferta se trata como unidad indivisible. Si una entrada individual supera 4096 caracteres (raro pero posible con análisis Claude largo), se trunca el campo `🤖 Análisis Claude` al final.

Las ofertas híbridas o presenciales se marcan con ⚠️.

### config.py

Carga variables de `.env` con `python-dotenv`. Expone:
- `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`
- `LINKEDIN_EMAIL`, `LINKEDIN_PASSWORD`
- `ANTHROPIC_API_KEY`
- `SKILLS_HAVE: list[str]` — hardcodeado en `config.py`, no en `.env`
- `SKILLS_LEARNING: list[str]` — hardcodeado en `config.py`, no en `.env`
- `KNOWN_CRYPTO_COMPANIES: list[str]` — hardcodeado en `config.py`, no en `.env`

Las listas de skills y empresas son listas de strings Python definidas directamente en `config.py` (no en `.env`), para facilitar edición sin reconfigurar variables de entorno.

### setup.sh

Acciones en orden:
1. Verificar que `.gitignore` contenga `.env`; si no, agregarlo automáticamente
2. Verificar Python 3.9+ disponible
3. Instalar dependencias con `pip install -r requirements.txt`
4. Instalar browsers de Playwright: `playwright install chromium`
5. Crear `storage/seen_jobs.json` vacío si no existe: `[]`
6. Copiar `com.your_usernamejobhunter.plist` a `~/Library/LaunchAgents/`
7. Registrar con launchd: `launchctl load ~/Library/LaunchAgents/com.your_usernamejobhunter.plist`
8. Imprimir instrucción: `"Job Hunter instalado. Próxima ejecución: lunes 8:00 AM"`

Incluye flag `--skip-linkedin` documentado en el README para desarrollo sin credenciales LinkedIn.

### com.your_usernamejobhunter.plist

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
    <string>/path/to/venv/bin/python</string>
    <string>/path/to/agente-job-hunter/main.py</string>
  </array>
  <key>WorkingDirectory</key>
  <string>/path/to/agente-job-hunter</string>
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
  <string>/path/to/agente-job-hunter/logs/job_hunter.log</string>
  <key>StandardErrorPath</key>
  <string>/path/to/agente-job-hunter/logs/job_hunter.log</string>
  <key>RunAtLoad</key>
  <false/>
</dict>
</plist>
```

Notas:
- `Weekday = 2` = lunes en launchd (domingo = 1)
- `setup.sh` reemplaza los `/path/to/` con rutas absolutas reales usando `$(pwd)` y `$(which python)` del virtualenv
- `RunAtLoad = false` — no ejecutar al cargar, solo según calendario

---

## Manejo de errores

- Cada scraper falla de forma aislada con `try/except` y log del error; el pipeline continúa
- LinkedIn: si detecta CAPTCHA o redirección a login, loguea el fallo y omite la fuente
- Si Claude API falla, el análisis se omite y la oferta se envía sin campo `🤖`
- Si Telegram falla, se loguea el error y `seen_jobs.json` **no se actualiza** (para reintentar la próxima ejecución)
- `seen_jobs.json`: escritura atómica vía archivo temporal; si el proceso se interrumpe, el archivo original permanece intacto

---

## Dependencias Python

```
requests
beautifulsoup4
playwright
anthropic
python-dotenv
python-telegram-bot
```

---

## Variables de entorno requeridas (.env)

```
TELEGRAM_TOKEN=
TELEGRAM_CHAT_ID=
LINKEDIN_EMAIL=
LINKEDIN_PASSWORD=
ANTHROPIC_API_KEY=
```

---

## Migración a cloud

El diseño es cloud-ready: reemplazar `launchd` por el cron de Railway/Render es el único cambio necesario. Las credenciales se mueven de `.env` a las variables de entorno del servicio.

---

## Fuera de alcance (v1)

- Interfaz web o dashboard
- Auto-aplicación a ofertas
- Generación automática de cover letters
- Tracking de aplicaciones enviadas
- Ejecución con `--skip-linkedin` flag (documentado pero no implementado en el CLI en v1; se puede pasar manualmente)
