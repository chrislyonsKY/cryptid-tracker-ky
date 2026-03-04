# Architecture — Cryptid Tracker KY

## System Overview

Cryptid Tracker KY is a real-time spatial sighting tracker for Kentucky cryptids, built on Aiven's free tier managed services. The system demonstrates a streaming data architecture applied to geocoded crowdsourced data, combining real historical sighting records (BFRO Bigfoot, NUFORC UFO) with synthetic sightings for lesser-known Kentucky cryptids.

```
┌─────────────────────────────────────────────────────────────────────┐
│                          FRONTEND                                   │
│  MapLibre GL JS — sighting markers, county threat choropleth,       │
│  live feed sidebar, global stats dashboard                          │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ REST API (JSON / GeoJSON)
┌───────────────────────────▼─────────────────────────────────────────┐
│                        FASTAPI SERVER                                │
│  Routes: /sightings, /cryptids, /stats, /counties, /submit          │
│  Reads from: PostgreSQL (historical) + Valkey (live cache)          │
│  Writes to: Kafka (sighting-raw topic)                              │
└────┬──────────────────┬──────────────────────┬──────────────────────┘
     │                  │                      │
     ▼                  ▼                      ▼
┌─────────┐    ┌──────────────┐       ┌──────────────┐
│  KAFKA  │    │  POSTGRESQL  │       │    VALKEY     │
│ (Aiven) │    │   + PostGIS  │       │   (Aiven)    │
│         │    │   (Aiven)    │       │              │
│ Topics: │    │              │       │ Keys:        │
│ - raw   │    │ Tables:      │       │ - threat:*   │
│ - valid │    │ - sightings  │       │ - stats      │
│         │    │ - cryptids   │       │ - recent     │
│ 5 topic │    │ - counties   │       │ - leaders    │
│ limit   │    │              │       │              │
└────┬────┘    └──────────────┘       └──────────────┘
     │
     ▼
┌──────────────────────────────────────────────────┐
│                KAFKA CONSUMER                      │
│  Reads: sighting-raw                               │
│  Validates: bounds check, dedup, profanity         │
│  Writes: PostgreSQL (INSERT) + Valkey (cache update)│
│  Publishes: sighting-validated                      │
└──────────────────────────────────────────────────┘

┌──────────────────────────┐    ┌──────────────────┐
│     SIGHTING GENERATOR   │    │      MYSQL       │
│  Synthetic sighting      │    │     (Aiven)      │
│  producer for live demo  │    │                  │
│  Publishes → Kafka raw   │    │  Tables:         │
│                          │    │  - users         │
│  Strategies:             │    │  - comments      │
│  - Folklore-weighted     │    │  - votes         │
│  - Seasonal patterns     │    │                  │
│  - Evidence variation    │    │                  │
└──────────────────────────┘    └──────────────────┘
```

## Module Interfaces

### 1. FastAPI Server (`src/api/`)

The API server is the central hub. It handles HTTP requests from the frontend and coordinates between all four data stores.

**Endpoints:**

| Method | Path | Source | Returns |
|---|---|---|---|
| `POST` | `/api/sightings` | → Kafka `sighting-raw` | `202 Accepted` + sighting ID |
| `GET` | `/api/sightings` | PostgreSQL (spatial query) | GeoJSON FeatureCollection |
| `GET` | `/api/sightings/{id}` | PostgreSQL | GeoJSON Feature |
| `GET` | `/api/sightings/recent` | Valkey `recent:sightings` | JSON array |
| `GET` | `/api/cryptids` | PostgreSQL | JSON array of cryptid types |
| `GET` | `/api/cryptids/{slug}` | PostgreSQL | JSON cryptid detail |
| `GET` | `/api/stats` | Valkey `stats:global` | JSON stats object |
| `GET` | `/api/stats/leaderboard` | Valkey `leaderboard:reporters` | JSON sorted array |
| `GET` | `/api/counties` | PostgreSQL + Valkey | GeoJSON with threat_level property |
| `GET` | `/api/counties/{fips}/threat` | Valkey `threat:{fips}` | JSON threat detail |

**Query Parameters for `GET /api/sightings`:**
- `bbox` — Bounding box filter: `minLon,minLat,maxLon,maxLat`
- `cryptid` — Filter by cryptid slug (e.g., `bigfoot`, `mothman`)
- `evidence_min` — Minimum evidence level (1-5)
- `after` / `before` — Date range filter (ISO 8601)
- `limit` / `offset` — Pagination (default 100, max 500)

### 2. Kafka Consumer (`src/consumer/`)

A standalone Python process that reads from `sighting-raw`, validates, persists, and republishes.

**Validation Pipeline:**
1. **Schema validation** — Required fields present, types correct
2. **Bounds check** — Coordinates fall within Kentucky bounding box (lat: 36.49-39.15, lon: -89.57 to -81.96)
3. **Duplicate detection** — Same reporter + same location within 1km + same cryptid within 1 hour → reject
4. **Profanity filter** — Description field checked against word list
5. **Cryptid validation** — `cryptid_slug` matches a known cryptid in the reference table

**On valid sighting:**
1. INSERT into PostgreSQL `sightings` table with PostGIS geometry
2. UPDATE Valkey `recent:sightings` list (LPUSH + LTRIM to 50)
3. UPDATE Valkey `stats:global` hash (HINCRBY total, per-cryptid counts)
4. UPDATE Valkey `leaderboard:reporters` sorted set (ZINCRBY)
5. PUBLISH to `sighting-validated` topic

**On invalid sighting:**
1. Log rejection reason
2. Optionally publish to `sighting-rejected` topic (if within 5-topic limit)

### 3. Sighting Generator (`src/generator/`)

A CLI tool that produces realistic synthetic sightings for demo purposes. Used during video walkthroughs and live presentations.

**Generation Strategies:**
- **Folklore-weighted locations** — Each cryptid type has weighted zones (e.g., Pope Lick Monster clusters near Louisville, Herrington Lake Monster near Danville/Harrodsburg)
- **Land cover bias** — Forest and rural areas weighted higher for terrestrial cryptids, water bodies for aquatic
- **Seasonal patterns** — More sightings in summer/fall, fewer in winter
- **Evidence distribution** — Weighted toward lower evidence levels (most sightings are "rustling bushes" or "blurry photo")
- **Time-of-day patterns** — Most sightings between dusk and midnight

**CLI Interface:**
```bash
# Generate 100 sightings over the last year (batch seed)
python -m src.generator.main --mode batch --count 100 --days-back 365

# Stream sightings in real-time (1 every 5-30 seconds)
python -m src.generator.main --mode stream --interval-min 5 --interval-max 30

# Generate only bigfoot sightings
python -m src.generator.main --mode stream --cryptid bigfoot
```

### 4. Frontend (`src/frontend/`)

A static single-page application using MapLibre GL JS. No build step — just HTML, CSS, and vanilla JavaScript served from the FastAPI static files mount.

**Map Layers:**
1. **County choropleth** — Kentucky counties colored by threat level (green → yellow → orange → red → purple)
2. **Sighting markers** — Individual sightings styled by cryptid type (custom icons per creature)
3. **Cluster layer** — At low zoom levels, sightings cluster with count badges
4. **Heatmap layer** — Toggle for sighting density visualization

**Sidebar Components:**
1. **Live Feed** — Scrolling list of recent sightings (polled from `/api/sightings/recent`)
2. **Global Stats** — Total sightings, most-sighted creature, most active county
3. **Leaderboard** — Top sighting reporters
4. **Filters** — Cryptid type, evidence level, date range
5. **Submit Form** — Report a new sighting (POST to `/api/sightings`)

## Data Flow Detail

### Sighting Submission Flow

```
User clicks map → fills form → POST /api/sightings
    │
    ▼
FastAPI validates request body (Pydantic)
    │
    ▼
Assign UUID sighting_id + timestamp
    │
    ▼
Serialize to JSON → produce to Kafka "sighting-raw"
    │
    ▼
Return 202 Accepted { "sighting_id": "...", "status": "pending" }
    │
    ▼ (async, milliseconds later)
    │
Consumer reads from "sighting-raw"
    │
    ▼
Validation pipeline (bounds, dedup, profanity, cryptid check)
    │
    ├── VALID ──────────────────────────────────────────┐
    │                                                    │
    │   INSERT INTO sightings (geom, cryptid_id, ...)   │
    │   LPUSH recent:sightings → LTRIM 50               │
    │   HINCRBY stats:global total_sightings 1           │
    │   ZINCRBY leaderboard:reporters {name} 1           │
    │   PRODUCE → "sighting-validated"                    │
    │                                                    │
    └── INVALID ────────────────────────────────────────┐
        │                                                │
        │   LOG warning with rejection reason            │
        └────────────────────────────────────────────────┘
```

### Threat Level Computation

Threat levels are computed periodically (every 5 minutes via scheduled task or on-demand) rather than on every sighting, to avoid expensive spatial joins on each insert.

```sql
-- County threat level query
WITH recent_sightings AS (
    SELECT s.geom, s.evidence_level, s.cryptid_id, c.danger_rating
    FROM sightings s
    JOIN cryptids c ON s.cryptid_id = c.id
    WHERE s.created_at > NOW() - INTERVAL '30 days'
),
county_scores AS (
    SELECT
        k.fips,
        k.name,
        COUNT(rs.*) AS sighting_count,
        AVG(rs.evidence_level) AS avg_evidence,
        MAX(rs.danger_rating) AS max_danger,
        -- Weighted score: count * avg_evidence * max_danger
        COUNT(rs.*) * COALESCE(AVG(rs.evidence_level), 0) * COALESCE(MAX(rs.danger_rating), 1) AS threat_score
    FROM ky_counties k
    LEFT JOIN recent_sightings rs ON ST_Contains(k.geom, rs.geom)
    GROUP BY k.fips, k.name
)
SELECT fips, name, sighting_count, threat_score,
    CASE
        WHEN threat_score = 0 THEN 'none'
        WHEN threat_score < 10 THEN 'low'
        WHEN threat_score < 30 THEN 'moderate'
        WHEN threat_score < 60 THEN 'high'
        ELSE 'extreme'
    END AS threat_level
FROM county_scores;
```

Results are written to Valkey as `threat:{fips}` keys with a 5-minute TTL.

## Kafka Topic Design

Limited to 5 topics on the free tier. Allocate carefully:

| Topic | Partitions | Retention | Purpose |
|---|---|---|---|
| `sighting-raw` | 1 | 3 days | Unvalidated sighting submissions |
| `sighting-validated` | 1 | 3 days | Validated sightings (post-consumer) |
| `sighting-rejected` | 1 | 3 days | Rejected sightings with reason codes |
| `threat-updates` | 1 | 3 days | County threat level change events |
| *(reserved)* | — | — | Future use (notifications, etc.) |

## Valkey Key Design

| Key Pattern | Type | TTL | Content |
|---|---|---|---|
| `stats:global` | Hash | none | `{total, bigfoot_count, mothman_count, ...}` |
| `threat:{fips}` | Hash | 300s | `{level, score, sighting_count, top_cryptid}` |
| `recent:sightings` | List | none | Last 50 sighting JSON objects (LPUSH + LTRIM) |
| `leaderboard:reporters` | Sorted Set | none | Reporter names scored by sighting count |
| `sighting:pending:{id}` | String | 60s | Dedup guard during consumer processing |

## Technology Rationale

| Choice | Why | Alternative Considered |
|---|---|---|
| FastAPI | Async-native, auto OpenAPI docs, Pydantic validation, fast | Flask (sync, no auto-docs) |
| PostGIS | Spatial indexing, ST_Contains for county joins, ST_ClusterDBSCAN | Storing lat/lon as floats (no spatial ops) |
| MapLibre GL JS | Free, vector tiles, performant clustering, open source | Leaflet (raster-only, slower for many markers) |
| Vanilla JS | No build step, competition simplicity, focus on backend | React (overkill for a demo frontend) |
| confluent-kafka | Production-grade Python Kafka client, Aiven-compatible | kafka-python (less maintained) |
| SQLAlchemy 2.0 | Modern async, GeoAlchemy2 integration, good ORM | psycopg2 raw (verbose, no model layer) |
