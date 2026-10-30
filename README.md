# Jarvis — Personal AI Chief of Staff

A modular, agent-based personal assistant system built with Python and the Anthropic Claude API. Jarvis runs autonomously on a local Mac via macOS LaunchAgents, with agents that specialize in distinct domains and communicate through shared file reports.

> This repository contains a curated subset of the full system. Additional private agents handle personal finance, DeFi portfolio management, and voice interaction.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         macOS (LaunchAgents)                    │
│                                                                 │
│  07:10am  ┌─────────┐   ┌───────────┐   ┌──────────────────┐  │
│  daily    │  Scout  │   │Job-Hunter │   │    agente-CFO    │  │
│           │  (CIO)  │   │  (Talent) │   │ (Finance report) │  │
│           └────┬────┘   └─────┬─────┘   └────────┬─────────┘  │
│                │              │                   │             │
│                └──────────────┼───────────────────┘             │
│                               │                                 │
│                        shared_reports/                          │
│                  (Markdown/JSON inter-agent bus)                │
│                               │                                 │
│  08:30am  ┌───────────────────▼──────────────────────────────┐  │
│  daily    │              Health-Check                         │  │
│           │  Reads logs + shared_reports, sends ONE Telegram  │  │
│           │  alert if anything failed. No API calls.          │  │
│           └───────────────────┬──────────────────────────────┘  │
│                               │                                 │
│                        Telegram Supergroup                      │
│                    (topic-based notifications)                  │
│                                                                 │
│  on-demand ┌────────────────────────────────────────────────┐   │
│            │  CAMS Agent  │  (AML exam study & tracking)    │   │
│            └────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Agents

| Agent | Type | What it does |
|---|---|---|
| **agente-scout** | Autonomous (daily) | Monitors AI ecosystem, Claude Code updates, crypto regulation, and AML/compliance news; filters by relevance to Jarvis and career goals |
| **agente-job-hunter** | Autonomous (daily) | Scrapes remote Compliance/AML/crypto job boards (RemoteOK, Web3Career, LinkedIn, Indeed, Greenhouse); filters by fit; sends curated results to Telegram |
| **agente-CFO** | Autonomous (daily) | Reads financial snapshot + DeFi positions; generates consolidated report and sends actionable alerts to Telegram |
| **agente-CAMS** | On-demand | CAMS certification study assistant — tracks sessions, generates quizzes, maintains study logs toward exam readiness |
| **agente-health-check** | Autonomous (8:30am) | Verifies all other agents ran successfully; sends a single Telegram alert per day if anything failed |

---

## How agents communicate

Agents do not call each other directly. They write structured reports to `shared_reports/` and read each other's outputs from there. `shared_reports/_index.md` acts as the system map — every agent reads it first to know what files exist, who owns them, and how fresh they are.

---

## Installation

### Prerequisites

- macOS (LaunchAgents required)
- Python 3.11+
- `pip install python-dotenv requests anthropic`

### Setup

1. Clone this repo
2. Create the central credentials file:
   ```bash
   mkdir -p ~/.config/jarvis
   cp .env.example ~/.config/jarvis/.env
   # Fill in your values
   chmod 600 ~/.config/jarvis/.env
   ```
3. Install a LaunchAgent (example — health-check):
   ```bash
   # Edit the plist to replace your_username with your macOS username
   cp agente-health-check/com.jarvis.healthcheck.plist \
      ~/Library/LaunchAgents/com.jarvis.healthcheck.plist
   launchctl load ~/Library/LaunchAgents/com.jarvis.healthcheck.plist
   ```
4. Verify API key is loading correctly (no key is printed):
   ```bash
   python3 verify_api_key.py
   ```

---

## Design Decisions

### Single credentials file with chmod 600

All agents read `ANTHROPIC_API_KEY` from `~/.config/jarvis/.env` (not from per-agent `.env` files). This means rotating the key requires editing one file, not hunting across five directories. The file lives outside the repo and is never committed.

```python
load_dotenv(Path.home() / ".config/jarvis/.env")  # central key
load_dotenv()                                       # agent-specific vars
```

`chmod 600` ensures only the owner can read it — standard practice for credential files.

### Health-check makes no API calls

The health-check script is intentionally zero-cost: no Anthropic API calls, no third-party dependencies beyond `requests`. It reads log files and checks file modification times. This means it runs even when the API key is out of credits — which is exactly when you need monitoring most.

### Dead man's switch on Sundays

The health-check writes a sentinel file (`sentinel/.last_run`) with the current timestamp after every successful run. On startup, it checks whether the sentinel is older than 24 hours — if so, it alerts that it missed a run. On Sundays, instead of silence, it sends "All systems OK this week" to confirm it's alive. Between Monday and Saturday, silence means everything is fine.

### shared_reports as inter-agent bus

Agents are decoupled Python scripts. They communicate by writing structured Markdown/JSON to `shared_reports/` and reading each other's outputs. This avoids tight coupling, makes each agent independently testable, and means any agent can be replaced or upgraded without touching the others.

---

## Compliance Angle

Building this system pushed me to apply habits I associate with good compliance work:

**Continuous monitoring with a single actionable alert** — the health-check runs daily, checks whether every agent produced output on schedule, and sends one Telegram message only when something needs attention. Designing it this way meant thinking about signal-to-noise: too many alerts trains people to ignore them.

**Data traceability** — every agent writes timestamped output to `shared_reports/` with a documented owner, update frequency, and staleness threshold. I wanted to be able to answer "when was this last updated and by whom?" without digging through logs.

**Secure credential handling** — API keys live in a single file outside the repository (`~/.config/jarvis/.env`, chmod 600), never in per-agent configs or committed to git. Rotating a key means editing one file.

**Studying toward CAMS** — `agente-CAMS` tracks my study sessions and gaps as I work toward the Certified Anti-Money Laundering Specialist exam. The domain knowledge I'm building informs how I think about the monitoring and escalation patterns in the rest of the system.

---

## Sample Output

Health-check Telegram alert when an agent fails (invented data):

```
🔴 Jarvis Health Check — 2026-10-30 08:30

❌ scout     — last run: 26h ago | error: Your credit balance is too low to
               access the Anthropic API. Please go to Plans & Billing to…
✅ cfo       — last run: 3h ago
✅ job-hunter — last run: 4h ago
✅ flare     — last run: 2h ago
```

On days when everything ran cleanly, no message is sent. On Sundays, a single
"All systems OK this week" confirms the monitor itself is alive.

---

## Tech Stack

- **Language:** Python 3.11
- **AI:** Anthropic Claude (claude-sonnet-4-6)
- **Scheduling:** macOS LaunchAgents
- **Notifications:** Telegram Bot API (topic-based supergroup)
- **Search:** Brave Search API (Scout agent)
- **Inter-agent communication:** File system (`shared_reports/`)

---

## About the author

I'm transitioning into compliance and AML in the crypto space. I'm currently studying for the CAMS certification and built Jarvis to automate the parts of my day that benefit from structure — monitoring, research, job search — so I can focus on the work that requires judgment. This repo is a slice of that system.
