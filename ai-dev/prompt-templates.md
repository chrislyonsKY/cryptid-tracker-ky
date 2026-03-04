# Prompt Templates — Cryptid Tracker KY

Reusable prompts for Claude Code and other AI tools.

---

## Implementation Prompt

```
Read CLAUDE.md, ai-dev/architecture.md, ai-dev/patterns.md, ai-dev/guardrails/.

Implement [specific feature/module].

Before writing code:
1. Confirm you understand the module's responsibility
2. List the files you will create or modify
3. Check ai-dev/decisions/ for any prior decisions affecting this module
4. Show me the plan

Do not proceed until I type Engage.
```

## Code Review Prompt

```
Read CLAUDE.md, ai-dev/patterns.md, ai-dev/guardrails/.

Review [file or module] for:
- Adherence to project conventions in CLAUDE.md
- Compliance with ai-dev/guardrails/ constraints
- Error handling completeness
- Edge cases
- Anti-patterns listed in patterns.md

Produce a numbered list of findings with severity (Critical / Warning / Info).
```

## PostGIS Query Prompt

```
Read CLAUDE.md, ai-dev/field-schema.md, ai-dev/agents/data_expert.md.

Write a PostGIS query that [description].
- Use SRID 4326
- Use spatial indexes (GiST-friendly operators)
- Use parameterized binds
- Uppercase SQL keywords, lowercase identifiers
- Include EXPLAIN plan considerations
```

## Seed ETL Prompt

```
Read CLAUDE.md, ai-dev/agents/python_expert.md, ai-dev/field-schema.md.

Build an ETL script that:
1. Reads [BFRO/NUFORC] CSV from data/seed/
2. Filters to Kentucky records
3. Maps columns to the sightings table schema in ai-dev/field-schema.md
4. Handles missing/malformed coordinates gracefully
5. Inserts into PostgreSQL via SQLAlchemy
6. Logs progress and error counts

Follow all patterns in ai-dev/patterns.md.
```

## Kafka Consumer Prompt

```
Read CLAUDE.md, ai-dev/architecture.md, ai-dev/agents/python_expert.md, ai-dev/patterns.md.

Implement the Kafka consumer that:
1. Reads from sighting-raw topic
2. Runs validation pipeline (bounds, dedup, profanity, cryptid check)
3. On valid: INSERT to PostgreSQL, update Valkey caches, publish to sighting-validated
4. On invalid: log with reason, optionally publish to sighting-rejected
5. Uses confluent-kafka Consumer with proper error handling

Follow the consumer pattern in ai-dev/patterns.md exactly.
```

## Frontend Map Prompt

```
Read CLAUDE.md, ai-dev/agents/frontend_expert.md, ai-dev/field-schema.md.

Build the MapLibre GL frontend that:
1. Centers on Kentucky [-85.75, 37.85] at zoom 7
2. Loads county boundaries from /api/counties as choropleth (threat level colors)
3. Loads sightings from /api/sightings?bbox=... as clustered markers
4. Sidebar: recent sightings feed from /api/sightings/recent
5. Dark theme (Carto dark-matter basemap)
6. No frameworks — vanilla JS, single HTML file

Use [lon, lat] coordinate order everywhere.
```

## End-of-Session Commit Prompt

```
Read CLAUDE.md.

Summarize all changes made this session.
Group into logical git commits.
Use format: feat(module): description or fix(module): description

Show proposed commits. Do not run git until I type Engage.
```
