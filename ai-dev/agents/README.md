# ai-dev/agents/ — Agent Inventory

## Available Agents

| Agent | File | Primary Use |
|---|---|---|
| Solutions Architect | `architect.md` | System design, service integration, Kafka/Valkey key design review |
| Python Expert | `python_expert.md` | FastAPI, Kafka producer/consumer, Valkey cache, ETL scripts |
| Data & Database Expert | `data_expert.md` | PostGIS schemas, spatial queries, SQL migrations, threat computation |
| Frontend & Map Expert | `frontend_expert.md` | MapLibre GL map, vanilla JS UI, choropleth, markers |

## Phase → Agent Mapping

| Phase | Primary | Supporting |
|---|---|---|
| Schema design & migrations | Data Expert | Architect |
| Kafka + consumer pipeline | Python Expert | Architect |
| API endpoints | Python Expert | Data Expert |
| Seed data ETL | Python Expert | Data Expert |
| Sighting generator | Python Expert | — |
| Frontend map & UI | Frontend Expert | — |
| Threat level computation | Data Expert | Python Expert |
| Architecture review | Architect | All |

## Usage

Reference in Claude Code prompts:

```
Read ai-dev/agents/python_expert.md.
Implement the Kafka consumer validation pipeline per ai-dev/architecture.md.
```

Or combine for cross-cutting tasks:

```
Read ai-dev/agents/data_expert.md and ai-dev/agents/python_expert.md.
Build the BFRO seed ETL script that reads CSV and inserts into PostGIS.
```
