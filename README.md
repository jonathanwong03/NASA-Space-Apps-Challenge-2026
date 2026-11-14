# FireSafe-SI: Microgravity Combustion Intelligence for Crew Fire Safety

**NASA Space Apps Challenge 2026.** An SI-powered dashboard that **summarizes, ranks and interprets** NASA's
microgravity combustion investigations to give fire-safety insight for spacecraft, space stations, Moon bases,
pressurized rovers and Mars habitats.

> Flames in microgravity behave differently from flames on Earth. Moon habitats are expected to run at **≥ 30% O2 and ≤ 10.2 psi**,
> where materials are much more flammable. FireSafe-SI shows researchers and engineers which NASA data applies to
> those environments, and where no data exists yet.

---

## Quick start

Requirements: Docker Desktop (Compose v2).

```bash
cp .env.example .env          # optional; add ANTHROPIC_API_KEY to enable Claude-generated answers
docker compose up -d --build
```

Open **http://localhost:8080**.

On first start the ingestion service loads a bundled snapshot of the NASA PSI data, so the dashboard works within
seconds even offline. It then pulls fresh data from the **live NASA PSI API** in the background (about 1 minute).
Data persists in the `pgdata` volume. `docker compose down -v` resets it.

| URL | What |
|---|---|
| http://localhost:8080 | Dashboard (React + Vite) |
| http://localhost:8080/api/catalog/docs | Catalog service OpenAPI |
| http://localhost:8080/api/insights/docs | Insights (SI) service OpenAPI |
| http://localhost:8080/api/ingest/docs | Ingestion service OpenAPI |
| `localhost:5433` | Postgres (user/pass/db `firesafe`) |

---

## Architecture

```
                         ┌──────────────────────────────────────────────┐
  Browser ──► :8080 ──►  │ frontend (nginx)                             │
                         │  • serves the React/Vite SPA                 │
                         │  • API gateway: /api/<service>/ → service    │
                         └──────┬──────────────┬──────────────┬─────────┘
                                │              │              │
                 /api/ingest    │  /api/catalog│  /api/insights (SSE)
                                ▼              ▼              ▼
                     ┌──────────────┐ ┌──────────────┐ ┌───────────────────┐
  NASA PSI API ◄──── │  ingestion   │ │   catalog    │ │     insights      │ ───► Claude API
  (live JSON + S3    │  FastAPI ETL │ │ FastAPI read │ │ FastAPI SI layer  │     (optional)
   test-table CSVs)  │  owns schema │ │ API, compare │ │ rank · gaps ·     │
                     │  profiling   │ │ tables, CSV  │ │ search · Q&A ·    │
                     └──────┬───────┘ └──────┬───────┘ │ briefs            │
                            │                │         └─────────┬─────────┘
                            └────────────────┴───────────────────┘
                                             ▼
                                   ┌───────────────────┐
                                   │ Postgres 16 (db)  │
                                   └───────────────────┘
```

| Service | Stack | Responsibility |
|---|---|---|
| `db` | postgres:16-alpine | Investigations, parsed test tables, habitats, incidents, spinoffs, sync runs, cached SI briefs |
| `ingestion` | Python 3.12, FastAPI, httpx, SQLAlchemy | Pulls PSI search → detail → presigned-S3 test-table CSVs. Parses and profiles them, upserts into Postgres. Falls back to a bundled snapshot when the API is unreachable. `POST /sync` triggers a live re-sync |
| `catalog` | FastAPI | Browse/filter investigations, detail, test tables (parsed numbers + CSV export), comparison with automatic similarity/difference detection, O2/pressure conditions, stats |
| `insights` | FastAPI, `anthropic` SDK | **SI layer**: explainable scenario ranking, coverage-gap analysis, BM25 search, streaming Q&A (SSE) and investigation briefs |
| `frontend` | React 19, Vite 8, Recharts, nginx | Dashboard UI and API gateway |

Shared code (`backend/common`) holds config, the SQLAlchemy models and CSV/number parsing.

---

## NASA datasets used (required for Global Awards)

| Dataset | Link | How it supports the solution |
|---|---|---|
| **NASA Physical Sciences Informatics (PSI): Combustion Science investigations** (24 investigations: BASS, BASS-II, Saffire-I/II/III, SAME, SAME-R, DAFT, FLEX, FLEX-2, CFI, ACME BRE / CLD / E-FIELD / s-Flame / Flame Design / CFI-G, SPICE, SLICE and ground analyses) | https://psi.nasa.gov/physci/repo/search?q=combustion&data_source=psi&data_type=investigation | The core dataset. Objectives, hypotheses, approaches, hardware, publications (352) and the **experimental test-matrix CSVs** (22 tables, ~2,000 test records). These are parsed into O2, pressure, flow, fuels, sample geometry, varied vs. constant parameters and sensors |
| **PSI JSON web service** (live connection) | `https://psi.nasa.gov/geode-py/ws/repo/search`, `/repo/investigations/{id}`, `/studies/{id}/download` | Live sync. No key required |
| NASA Glenn Combustion Science | https://www.nasa.gov/glenn/glenn-expertise-space-exploration/physical-sciences-program/combustion-science/ | Program context |
| A Researcher's Guide to Combustion Science | https://www.nasa.gov/missions/station/a-researchers-guide-to-combustion-science/ | Background for interpretation |
| Apollo 1 / Apollo 13 lessons learned (NASA OSMA) | https://sma.nasa.gov/sma-disciplines/accllp/apollo-1#history · https://sma.nasa.gov/sma-disciplines/accllp/apollo-13 | Incident timeline that motivates prevention, detection and suppression |
| Fire aboard Mir (NASA History) | https://www.nasa.gov/history/25-years-ago-fire-aboard-space-station-mir/ | Incident timeline |
| NASA Spinoffs | https://spinoff.nasa.gov/node/9407 · https://spinoff.nasa.gov/node/9582 · https://spinoff.nasa.gov/node/9918 · https://spinoff.nasa.gov/node/11065 | Earth-benefit applications (detectors, air tanks, fire attire, water-mist extinguisher valve) |

PSI asks users to cite datasets by DOI. Every investigation page in the dashboard shows its DOI and links its PSI landing page.

**Live connection:** we found PSI's public JSON API by inspecting its Angular front end. The ingestion
service uses it directly and downloads each experimental table through the presigned-S3 download endpoint. NASA NTRS
was also evaluated but blocks automated clients (HTTP 403), so publication lists come from PSI's own records.

---

## What the SI does

1. **Summarize.** Every investigation gets an SI brief (what it studied, test matrix, fire-safety findings, Moon/Mars
   relevance, modeling data, Earth applications). It is written by Claude when an API key is set, and by a rule-based template otherwise.
2. **Extract.** A profiler reads each heterogeneous test table (`"0.17; 0.21;0.25; 0.3"`, `"757.7 mmHg"`, `"~ 21.5"`,
   `"LOW O2"`…) and normalizes O2 (%), pressure (atm/psi), flow (cm/s), fuels, and which parameters **varied vs. stayed constant**.
3. **Rank.** An explainable score for every investigation against a habitat scenario (ISS, Orion, Moon Base, rover,
   Mars, spacesuit, Earth) and a pillar focus. Weighted components: pillar fit, fire-safety directness, O2 match,
   pressure match, flow match, fuel relevance, gravity relevance and data richness. Each result lists the reasons for its score.
4. **Interpret.** Gap analysis checks tested conditions against habitat atmospheres. Key finding: **no solid-material
   flammability test in PSI exceeds ~22% O2**, and no tested condition falls inside the Moon Base O2 × pressure envelope.
   Only six gas/droplet investigations reach ≥ 30% O2.
5. **Ask.** Streaming Q&A grounded in all PSI records, with `[PSI-xx]` citations linked to investigation pages.
   With `ANTHROPIC_API_KEY` set it uses **Claude (`claude-opus-5-5`)**. The full corpus sits in a prompt-cached system
   prompt and server-side refusal fallbacks are enabled. Without a key, a BM25 + rules engine answers offline.

### Dashboard pages
- **Overview:** KPIs, data-gap findings, per-pillar "where to look first", investigation timeline, incident history
- **Scenario Ranking:** ranked list with expandable score breakdown and reasons
- **Atmosphere Coverage:** O2 vs. pressure map of every tested condition, with habitat boxes and per-habitat coverage
- **Ask the SI:** chat with citations, scenario-aware
- **Investigations / detail:** filters, text search, SI brief, conditions vs. Moon Base band, varied/constant parameters, test-matrix preview, publications
- **Compare:** 2–4 investigations side by side, with automatic similarities and differences plus envelope bars
- **Data Lab:** plot any numeric columns of any test table and export CSV for model calibration
- **Earth Benefits:** NASA Spinoffs plus each investigation's stated Earth benefits
- **Data Sources & Sync:** provenance, live-sync button, sync history

---

## Configuration (`.env`)

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | *(empty)* | Enables Claude Q&A and briefs |
| `CLAUDE_MODEL` | `claude-opus-5-5` | Claude model ID |
| `WEB_PORT` / `DB_PORT` | `8080` / `5433` | Host ports |
| `SYNC_ON_STARTUP` | `true` | Pull from the live PSI API whenever the stack starts |
| `POSTGRES_USER/PASSWORD/DB` | `firesafe` | Database credentials |

## Local frontend development

```bash
docker compose up -d          # backend + gateway on :8080
cd frontend && npm install && npm run dev   # http://localhost:5173, proxies /api → :8080
```

## Project structure

```
compose.yaml
backend/
  common/              shared config, SQLAlchemy models, CSV/number parsing
  ingestion_service/   PSI client, ETL pipeline, profiler, curated domain knowledge, PSI snapshot
  catalog_service/     read/compare/table API
  insights_service/    ranking, gap analysis, BM25 search, Claude integration, offline engine
frontend/              React + Vite SPA, nginx gateway config
```

## Assumptions and limits
- Habitat atmospheres follow the challenge brief (Moon Base/rover ≥ 30% O2, ≤ 10.2 psi; suit 100% O2 at 4.3 psi).
  The 8.2 psi lower bound and the Mars atmosphere are **planning assumptions** and are labelled as such in the UI.
- Where a test table doesn't report O2 or pressure, ISS cabin conditions (~21%, ~1 atm) are assumed and flagged.
- Pillar weights and hardware families per investigation are curated from the challenge brief and PSI metadata
  (`backend/ingestion_service/curated.py`). Newly published PSI investigations fall back to keyword-derived weights.
- PSI holds no partial-gravity data yet (LUCI and FM2 are expected later). The ACME E-FIELD experiment is used as the
  only proxy for partial gravity.
