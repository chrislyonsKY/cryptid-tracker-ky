## Cryptid Tracker KY — Copilot Instructions

This is a Python/FastAPI project with a multi-service backend: PostgreSQL+PostGIS, Apache Kafka, Valkey, and MySQL on Aiven free tier.

### Key conventions:
- All config from environment variables via pydantic-settings (AIVEN_* prefix)
- Async database access with SQLAlchemy 2.0 + asyncpg
- PostGIS geometry columns use SRID 4326 (WGS84)
- GeoJSON coordinate order: [longitude, latitude]
- Kafka via confluent-kafka (not kafka-python)
- Valkey via redis-py (wire-compatible)
- All functions: type hints + docstrings
- All errors: try/except with logging (no bare print)
- Frontend: vanilla JS + MapLibre GL JS (no React, no build step)

### Read before coding:
- `CLAUDE.md` — project context and conventions
- `ai-dev/architecture.md` — system design
- `ai-dev/patterns.md` — code patterns to follow
- `ai-dev/field-schema.md` — database schemas and API contracts
