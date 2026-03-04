# Spec — Cryptid Tracker KY

## Project Summary

A real-time Kentucky cryptid sighting tracker built for the Aiven Free Tier Competition. Users submit sightings on a web map; sightings stream through Kafka, are validated and stored in PostGIS, cached in Valkey, and rendered on a MapLibre GL frontend showing sighting clusters and county-level "threat levels."

**Competition criteria:** 50% Build (quality, creativity, technical execution) · 50% Story (documentation, process, "why")

**Deadline:** March 31, 2026

---

## Functional Requirements

### FR-01: Sighting Submission
- User can click a location on the map to submit a sighting
- Required fields: location (lat/lon from map click), cryptid type (dropdown), reporter name
- Optional fields: description (text), evidence level (dropdown), date/time (defaults to now)
- Submission returns immediately with `202 Accepted` (async processing via Kafka)
- Invalid coordinates (outside Kentucky) rejected with `400` at API level

### FR-02: Sighting Map Display
- Map centered on Kentucky with county boundaries visible
- Individual sighting markers styled by cryptid type (custom icon per creature)
- Markers cluster at low zoom levels with count badges
- Clicking a marker shows sighting details (creature, date, description, evidence level)
- Map supports bbox-based spatial query (load sightings for visible extent)

### FR-03: County Threat Levels
- Each Kentucky county has a computed "threat level" based on recent sighting activity
- Threat levels: None, Low, Moderate, High, Extreme
- Counties rendered as a choropleth (color-coded polygons) on the map
- Threat level based on: sighting count (30 days) × average evidence level × max creature danger rating
- Recomputed every 5 minutes (or on-demand via script)

### FR-04: Live Feed & Stats
- Sidebar shows the 50 most recent sightings in reverse chronological order
- Global stats: total sightings, most-sighted creature, most active county, most dangerous county
- Reporter leaderboard (top 10 by sighting count)
- Stats update on page refresh or polling interval (30 seconds)

### FR-05: Cryptid Reference
- Reference table of ~12 Kentucky cryptids with: name, slug, description, danger rating, known habitat, icon
- Filterable on the map (show/hide by cryptid type)
- Each cryptid has a detail card accessible from the sidebar

### FR-06: Sighting Generator (Demo Tool)
- CLI tool that generates synthetic sightings and publishes to Kafka
- Supports batch mode (seed N sightings) and stream mode (continuous real-time)
- Location weighting by cryptid type (folklore-accurate hotspots)
- Configurable rate and cryptid filters

### FR-07: Community Features (MySQL)
- User registration (username, email, display name)
- Comments on individual sightings
- Upvote/downvote sighting credibility
- Provides the MySQL usage for competition requirements

---

## Non-Functional Requirements

### NFR-01: Aiven Free Tier Constraints
- PostgreSQL: Single node, shared resources — keep queries efficient, use spatial indexes
- Kafka: 5 topics max, 3-day retention — design topic schema carefully
- Valkey: Limited memory — use TTLs, don't cache unbounded data
- MySQL: Single node — simple CRUD, no complex joins needed

### NFR-02: Performance
- Map should load initial view (county choropleth + clustered markers) in < 3 seconds
- Sighting submission to map appearance: < 5 seconds (Kafka → consumer → cache → poll)
- API spatial queries should use PostGIS spatial indexes (GiST)

### NFR-03: Demo-ability
- The app must look good in a 60-second screen recording
- Generator streaming sightings in real-time while map updates is the money shot
- Threat levels changing as sightings accumulate tells the visual story

### NFR-04: Storytelling
- README and blog post document the full architecture and build process
- Each Aiven service's role is clearly justified (not shoehorned)
- Humor is a feature — the tone should be deadpan technical applied to absurd content

---

## Acceptance Criteria

| ID | Criteria | Verified By |
|---|---|---|
| AC-01 | Can submit a sighting via the map UI and see it appear within 10 seconds | Manual test |
| AC-02 | BFRO Bigfoot sightings for KY are loaded and visible on the map | Seed script + visual |
| AC-03 | NUFORC UFO sightings for KY are loaded and visible on the map | Seed script + visual |
| AC-04 | County threat choropleth renders with color-coded levels | Visual |
| AC-05 | Generator can stream sightings at configurable rate | CLI test |
| AC-06 | Live feed updates with new sightings | Manual test |
| AC-07 | Stats dashboard shows accurate counts | Compare to DB query |
| AC-08 | Map filters by cryptid type | Manual test |
| AC-09 | All 4 Aiven services are actively used and justified | Architecture review |
| AC-10 | Full README with architecture diagrams and build narrative | Document review |

---

## Data Sources

| Source | Format | Records (KY) | Fields Used | License |
|---|---|---|---|---|
| BFRO Sightings | CSV (data.world / GitHub) | ~100-200 | lat, lon, date, title, description, county, season | Public data (scraped) |
| NUFORC Sightings | CSV (GitHub / Kaggle) | ~500-1000 | lat, lon, datetime, shape, summary, full text | Public (copyright noted) |
| KY County Boundaries | GeoJSON / Shapefile | 120 counties | FIPS, name, geometry | Public domain (Census TIGER) |
| Cryptid Reference | Hand-curated | ~12 | name, description, danger, habitat, lore | Original content |
| Synthetic Sightings | Generated | unlimited | all sighting fields | Original |

---

## Milestones & Build Order

### Phase 1: Foundation (Day 1-2)
- [ ] Set up Aiven services (PG+PostGIS, Kafka, Valkey, MySQL)
- [ ] Create PostgreSQL schema (sightings, cryptids, counties)
- [ ] Load KY county boundaries into PostGIS
- [ ] Create cryptid reference table with ~12 Kentucky cryptids
- [ ] Create MySQL community schema (users, comments, votes)

### Phase 2: Data Pipeline (Day 3-4)
- [ ] Build Kafka producer (sighting submission)
- [ ] Build Kafka consumer (validation + DB write + Valkey update)
- [ ] Build BFRO seed ETL script (CSV → PostGIS)
- [ ] Build NUFORC seed ETL script (CSV → PostGIS)
- [ ] Build threat level computation script

### Phase 3: API (Day 5-6)
- [ ] FastAPI app skeleton with CORS and config
- [ ] GET /api/sightings (spatial query with bbox)
- [ ] POST /api/sightings (→ Kafka producer)
- [ ] GET /api/stats, /api/counties, /api/cryptids
- [ ] MySQL community endpoints (users, comments, votes)

### Phase 4: Frontend (Day 7-8)
- [ ] MapLibre GL map with KY county boundaries
- [ ] County threat choropleth layer
- [ ] Sighting markers with clustering
- [ ] Sidebar: live feed, stats, leaderboard
- [ ] Sighting submission form (map click → modal)
- [ ] Cryptid type filter controls

### Phase 5: Generator & Polish (Day 9-10)
- [ ] Sighting generator with folklore-weighted strategies
- [ ] Stream mode for live demo recording
- [ ] Visual polish, icons, responsive layout
- [ ] Demo video recording
- [ ] README / blog write-up with architecture diagrams

### Phase 6: Ship (Day 11)
- [ ] Deploy API (Railway/Render/Fly.io)
- [ ] Final testing with all services connected
- [ ] LinkedIn post with #AivenFreeTier
- [ ] Submit Google Form

---

## LinkedIn Story Arc (WIP Posts)

Plan 3-4 posts during the build for "bonus points":

1. **"Just set up 4 managed data services in under 5 minutes"** — Screenshot of Aiven console with all services running. Hook: the free tier is genuinely useful, not a trial trap.
2. **"Streaming Bigfoot sightings through Kafka"** — Screenshot of consumer logs processing BFRO data. Hook: real geocoded data from the BFRO flowing through a streaming pipeline.
3. **"Kentucky's cryptid threat map is live"** — Screenshot of the choropleth map. Hook: PostGIS spatial joins computing county-level threat assessments. Land Between the Lakes looking dangerous.
4. **"Submitted: Cryptid Tracker KY"** — Final screenshot with link. Hook: full architecture story, what each service does, why streaming matters even for "fun" projects.

All posts tagged **#AivenFreeTier**.
