# Coding Standards Guardrails — Cryptid Tracker KY

These rules apply to ALL code generated for this project, regardless of which agent is active. Violations are treated as Critical findings.

## Python

- All scripts must use `logging` (no bare `print()` statements)
- All database queries must use parameterized binds or SQLAlchemy ORM (no string concatenation)
- All async database access through `async with` session context managers
- All Kafka operations wrapped in try/except with structured logging
- Type hints on all function signatures
- Docstrings on all public functions (purpose, params, returns, raises)
- Imports grouped: stdlib → third-party → local (with blank lines between)
- Target: Python 3.11+

## SQL

- Uppercase keywords (`SELECT`, `INSERT`, `WHERE`, `ST_Contains`)
- Lowercase identifiers (table names, column names)
- All queries use bind parameters (`:param` for raw SQL, ORM binds for SQLAlchemy)
- All geometry columns specify SRID 4326
- All spatial tables have GiST indexes on geometry columns

## JavaScript

- Vanilla JS only — no frameworks, no TypeScript, no build step
- `const` by default, `let` only when reassignment is needed, never `var`
- All API calls wrapped in try/catch with user-facing error display
- `[longitude, latitude]` coordinate order everywhere (GeoJSON standard)
- No inline styles — all styling in CSS file

## General

- No hardcoded credentials, connection strings, or API keys in source code
- All configuration from environment variables via `.env` (gitignored)
- Meaningful variable names — no single-letter variables except loop counters
- No commented-out code in committed files
- UTF-8 encoding for all source files
