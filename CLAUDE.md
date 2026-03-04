# CLAUDE.md — Cryptid Tracker KY

> Real-time Kentucky cryptid sighting tracker built on Aiven's free tier services.
> Python (FastAPI) · PostgreSQL+PostGIS · Apache Kafka · Valkey · MySQL · MapLibre GL JS

Read this file completely before doing anything.
Then read `ai-dev/architecture.md` for full context.
Then read `ai-dev/guardrails/` for hard constraints.

---

## Context

This project is an entry for the [Aiven Free Tier Competition](https://aiven.io/blog/the-aiven-free-tier-competition) (deadline: March 31, 2026; $1,000 prize). The competition evaluates 50% on the build (quality, creativity, technical execution) and 50% on the story (documentation, process, "why"). The project must use at least one Aiven free tier service; using multiple services and showing how they work together is encouraged.

Our strategy: combine **real geocoded cryptid/UFO sighting data** (BFRO, NUFORC) with a **streaming architecture** that demonstrates how Kafka, PostgreSQL+PostGIS, Valkey, and MySQL work together — applied to the most important geospatial problem in Kentucky.

---

## Workflow Protocol

When starting a new task:
1. Read CLAUDE.md (this file)
2. Read ai-dev/architecture.md
3. Read ai-dev/guardrails/ for constraints that override all other guidance
4. Read the relevant ai-dev/agents/ file for your role
5. Check ai-dev/decisions/ for prior decisions that may affect your work
6. Check ai-dev/skills/ for domain patterns specific to this project

Before writing code:
1. Confirm you understand the module's responsibility
2. List the files you will create or modify
3. Show me the plan

Do not proceed until I type **Engage**.

---

## Compatibility Matrix

| Component | Version | Notes |
|---|---|---|
| Python | 3.11+ | FastAPI backend |
| FastAPI | 0.115+ | API framework |
| SQLAlchemy | 2.0+ | ORM with GeoAlchemy2 |
| GeoAlchemy2 | 0.15+ | PostGIS integration |
| confluent-kafka | latest | Kafka producer/consumer |
| redis (valkey) | latest | Valkey client (redis-py compatible) |
| Node.js | 20+ LTS | Frontend build tooling (if needed) |
| MapLibre GL JS | 4.x | Map rendering |

### Aiven Free Tier Services

| Service | Connection | Purpose |
|---|---|---|
| PostgreSQL (+PostGIS) | `AIVEN_PG_URI` env var | Spatial data store: sightings, cryptids, KY counties |
| Apache Kafka | `AIVEN_KAFKA_*` env vars | Event streaming: sighting ingest and validation pipeline |
| Valkey | `AIVEN_VALKEY_URI` env var | Cache layer: threat levels, live stats, leaderboard |
| MySQL | `AIVEN_MYSQL_URI` env var | Community layer: user accounts, comments, upvotes |

---

## Project Structure

```
cryptid-tracker-ky/
├── CLAUDE.md                          # This file — AI reads first
├── README.md                          # Human-facing project overview
├── ai-dev/                            # AI development infrastructure
│   ├── architecture.md                # System design, data flow, module interfaces
│   ├── spec.md                        # Requirements, acceptance criteria
│   ├── patterns.md                    # Code patterns and anti-patterns
│   ├── field-schema.md                # Database schemas, API contracts
│   ├── prompt-templates.md            # Reusable AI prompts for development
│   ├── agents/                        # Specialized agent configurations
│   ├── decisions/                     # Architectural decision records
│   ├── skills/                        # Project-specific domain skills
│   └── guardrails/                    # Hard constraints (override everything)
├── src/
│   ├── api/                           # FastAPI application
│   │   ├── main.py                    # App entry point, CORS, lifespan
│   │   ├── routes/                    # API route handlers
│   │   │   ├── sightings.py           # Submit/query sightings
│   │   │   ├── cryptids.py            # Cryptid reference data
│   │   │   ├── stats.py               # Live stats and threat levels
│   │   │   └── counties.py            # County boundaries + threat map
│   │   ├── models/                    # SQLAlchemy + Pydantic models
│   │   ├── services/                  # Business logic layer
│   │   └── config.py                  # Environment-based configuration
│   ├── consumer/                      # Kafka consumer service
│   │   ├── main.py                    # Consumer entry point
│   │   ├── validators.py              # Sighting validation logic
│   │   └── handlers.py                # DB write + Valkey cache updates
│   ├── generator/                     # Synthetic sighting generator
│   │   ├── main.py                    # CLI entry point
│   │   ├── strategies.py              # Location weighting, creature selection
│   │   └── producer.py                # Kafka producer wrapper
│   └── frontend/                      # Static web frontend
│       ├── index.html                 # Single-page app shell
│       ├── js/
│       │   ├── app.js                 # Main application logic
│       │   ├── map.js                 # MapLibre GL map initialization
│       │   ├── sidebar.js             # Live feed, stats, controls
│       │   └── api.js                 # API client
│       └── css/
│           └── style.css              # Application styles
├── data/
│   ├── seed/                          # Seed data files (BFRO, NUFORC extracts)
│   ├── schemas/                       # SQL migration scripts
│   │   ├── 001_postgis_init.sql       # Enable PostGIS, create spatial tables
│   │   ├── 002_cryptids_seed.sql      # Cryptid reference data
│   │   ├── 003_ky_counties.sql        # County boundaries (simplified)
│   │   └── 004_mysql_community.sql    # MySQL community tables
│   └── ky_counties.geojson            # Kentucky county boundaries
├── scripts/
│   ├── seed_bfro.py                   # ETL: BFRO CSV → PostgreSQL
│   ├── seed_nuforc.py                 # ETL: NUFORC CSV → PostgreSQL
│   └── compute_threat_levels.py       # Scheduled threat level computation
├── docker-compose.yml                 # Local development (optional)
├── requirements.txt                   # Python dependencies
├── .env.example                       # Environment variable template
└── .gitignore
```

---

## Critical Conventions

### Environment & Credentials
- ALL connection strings come from environment variables, never hardcoded
- Use `.env` file locally (gitignored); `AIVEN_*` prefix for all Aiven service URIs
- Kafka SSL certificates stored in `certs/` directory (gitignored)

### Python
- All modules use `logging` (no bare `print()`)
- All database access through SQLAlchemy sessions with context managers
- All Kafka operations wrapped in try/except with dead-letter logging
- Type hints on all function signatures
- Docstrings on all public functions

### SQL
- Uppercase keywords, lowercase identifiers
- All spatial queries use SRID 4326 (WGS84)
- Parameterized queries only — never interpolate user input

### API
- All endpoints return JSON
- Spatial data returned as GeoJSON Feature/FeatureCollection
- Error responses follow `{"detail": "message"}` pattern (FastAPI default)

### Frontend
- Vanilla JS — no framework. This is a demo, not a SPA.
- MapLibre GL JS loaded from CDN
- API base URL configurable via `window.CONFIG.API_URL`

---

## Architecture Summary

See `ai-dev/architecture.md` for full detail.

**Data Flow:**
1. Sighting submitted via API → published to Kafka `sighting-raw` topic
2. Consumer reads `sighting-raw` → validates → writes to PostgreSQL (PostGIS) + updates Valkey caches → publishes to `sighting-validated` topic
3. API reads from PostgreSQL for historical queries, Valkey for live stats
4. Frontend renders MapLibre GL map with sighting markers + county threat choropleth
5. Generator script produces synthetic sightings → publishes to Kafka for live demo

**Key Design Decisions:**
- PostGIS for spatial storage and analysis (clustering, county joins, bounding box queries)
- Kafka decouples ingest from processing — demonstrates real streaming architecture
- Valkey caches computed values (threat levels, stats) to avoid repeated spatial queries
- MySQL for community features (accounts, comments) — separates transactional from analytical
- Static frontend — avoids build complexity, keeps focus on backend architecture

---

## What NOT To Do

- Do NOT use ORM for spatial queries — use raw SQL with GeoAlchemy2 functions or `text()` for complex PostGIS operations
- Do NOT store GeoJSON blobs in PostgreSQL — use proper `geometry(Point, 4326)` columns
- Do NOT call PostGIS on every API request — that's what Valkey is for
- Do NOT build a React app — static HTML + vanilla JS + MapLibre GL is the right call here
- Do NOT over-engineer auth — this is a competition demo, not a production system
- Do NOT use Kafka for request-reply patterns — it's fire-and-forget ingest only
- Do NOT commit `.env`, `certs/`, or any Aiven connection credentials
