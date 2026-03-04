# Data Handling Guardrails — Cryptid Tracker KY

## Credentials

- NEVER hardcode passwords, API keys, or connection strings in source code
- All Aiven connection URIs stored in `.env` file (gitignored) with `AIVEN_` prefix
- Kafka SSL certificates stored in `certs/` directory (gitignored)
- `.env.example` contains placeholder values only — never real credentials

## Aiven Free Tier Limits

- **Kafka:** 5 topics max, 3-day retention — do not create topics programmatically without checking count
- **PostgreSQL:** Shared resources — always use spatial indexes, avoid full table scans
- **Valkey:** Limited memory — TTLs on all keys except essential counters, bounded lists (LTRIM)
- **MySQL:** Shared resources — simple CRUD only, no complex joins or heavy analytics

## Data Sources

- BFRO data is publicly scraped and redistributed — attribute in README
- NUFORC data has copyright notice — use for app functionality but do NOT reproduce full report text verbatim in the UI
- KY county boundaries from Census TIGER — public domain
- Synthetic sightings clearly marked with `source = 'generator'`

## User-Submitted Data

- Sighting descriptions pass through profanity filter before storage
- Reporter names are public — no expectation of anonymity in this demo
- No authentication required for sighting submission (competition demo, not production)
- Rate limiting on submit endpoint recommended but not critical for demo

## Output Files

- Seed data CSVs may be committed to the repo (public data)
- Never commit `.env`, `certs/`, or any file containing connection strings
- Log files should not contain full connection URIs — log host/port only if needed for debugging
