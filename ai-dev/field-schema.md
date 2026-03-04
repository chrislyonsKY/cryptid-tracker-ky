# Field Schema — Cryptid Tracker KY

## PostgreSQL + PostGIS

### Table: `cryptids`

The reference table of Kentucky's documented cryptids. Seeded once, rarely updated.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `SERIAL` | PK | Auto-increment ID |
| `slug` | `VARCHAR(50)` | UNIQUE, NOT NULL | URL-safe identifier (e.g., `bigfoot`, `pope-lick-monster`) |
| `name` | `VARCHAR(100)` | NOT NULL | Display name |
| `description` | `TEXT` | | Lore summary |
| `danger_rating` | `INTEGER` | CHECK 1-5 | 1=harmless curiosity, 5=existential threat |
| `habitat` | `VARCHAR(50)` | | Primary habitat type (forest, water, urban, cave, bridge) |
| `icon_url` | `VARCHAR(255)` | | Path to marker icon |
| `color` | `VARCHAR(7)` | | Hex color for map styling (e.g., `#8B4513`) |
| `first_sighted` | `INTEGER` | | Year of earliest known sighting |
| `notable_location` | `VARCHAR(200)` | | Most famous sighting location |
| `source_type` | `VARCHAR(20)` | | `folklore`, `bfro`, `nuforc`, or `synthetic` |

### Table: `sightings`

The main event table. Every validated sighting gets a row.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `UUID` | PK, DEFAULT gen_random_uuid() | Unique sighting identifier |
| `cryptid_id` | `INTEGER` | FK → cryptids(id), NOT NULL | What was sighted |
| `geom` | `geometry(Point, 4326)` | NOT NULL | Sighting location (WGS84) |
| `reporter_name` | `VARCHAR(100)` | NOT NULL | Who reported it |
| `description` | `TEXT` | | Witness account |
| `evidence_level` | `INTEGER` | CHECK 1-5, DEFAULT 1 | 1=rustling_bushes, 2=strange_sound, 3=blurry_photo, 4=clear_photo, 5=physical_evidence |
| `sighting_date` | `TIMESTAMPTZ` | DEFAULT NOW() | When the sighting occurred |
| `created_at` | `TIMESTAMPTZ` | DEFAULT NOW() | When the record was created |
| `season` | `VARCHAR(10)` | | spring, summer, fall, winter |
| `source` | `VARCHAR(20)` | DEFAULT 'user' | `user`, `bfro`, `nuforc`, `generator` |
| `source_id` | `VARCHAR(100)` | | Original ID from source dataset |
| `county_fips` | `VARCHAR(5)` | | KY county FIPS (computed via spatial join on insert) |
| `is_validated` | `BOOLEAN` | DEFAULT TRUE | Consumer validation status |
| `raw_kafka_key` | `VARCHAR(100)` | | Kafka message key for traceability |

**Indexes:**
- `idx_sightings_geom` — GiST index on `geom` (spatial queries)
- `idx_sightings_cryptid_date` — B-tree on `(cryptid_id, sighting_date DESC)` (filtered time queries)
- `idx_sightings_created` — B-tree on `created_at DESC` (recent sightings)
- `idx_sightings_county` — B-tree on `county_fips` (county aggregation)

### Table: `ky_counties`

Kentucky county boundaries for spatial joins and choropleth rendering.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `gid` | `SERIAL` | PK | Auto-increment ID |
| `fips` | `VARCHAR(5)` | UNIQUE, NOT NULL | County FIPS code |
| `name` | `VARCHAR(100)` | NOT NULL | County name |
| `geom` | `geometry(MultiPolygon, 4326)` | NOT NULL | County boundary |

**Indexes:**
- `idx_counties_geom` — GiST index on `geom`
- `idx_counties_fips` — B-tree on `fips`

---

## MySQL (Community Features)

### Table: `users`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `INT AUTO_INCREMENT` | PK | User ID |
| `username` | `VARCHAR(50)` | UNIQUE, NOT NULL | Login name |
| `display_name` | `VARCHAR(100)` | NOT NULL | Shown in UI |
| `email` | `VARCHAR(255)` | UNIQUE | Contact email |
| `created_at` | `DATETIME` | DEFAULT CURRENT_TIMESTAMP | Registration date |

### Table: `comments`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `INT AUTO_INCREMENT` | PK | Comment ID |
| `sighting_id` | `CHAR(36)` | NOT NULL, INDEX | UUID of the sighting (references PG) |
| `user_id` | `INT` | FK → users(id) | Author |
| `body` | `TEXT` | NOT NULL | Comment text |
| `created_at` | `DATETIME` | DEFAULT CURRENT_TIMESTAMP | Post date |

### Table: `votes`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `INT AUTO_INCREMENT` | PK | Vote ID |
| `sighting_id` | `CHAR(36)` | NOT NULL | UUID of the sighting (references PG) |
| `user_id` | `INT` | FK → users(id) | Voter |
| `value` | `TINYINT` | CHECK IN (-1, 1) | -1=doubt, +1=credible |
| `created_at` | `DATETIME` | DEFAULT CURRENT_TIMESTAMP | Vote date |

**Constraint:** UNIQUE(`sighting_id`, `user_id`) — one vote per user per sighting.

---

## Kafka Message Schemas

### Topic: `sighting-raw`

```json
{
  "sighting_id": "uuid-v4",
  "cryptid_slug": "bigfoot",
  "latitude": 37.7891,
  "longitude": -85.6012,
  "reporter_name": "Daniel Boone",
  "description": "Large bipedal figure observed near tree line at dusk",
  "evidence_level": 3,
  "sighting_date": "2026-03-15T20:30:00Z",
  "source": "user",
  "submitted_at": "2026-03-15T20:35:12Z"
}
```

**Key:** `sighting_id` (for dedup and log correlation)

### Topic: `sighting-validated`

Same schema as `sighting-raw` plus:
```json
{
  "...all sighting-raw fields...",
  "county_fips": "21017",
  "county_name": "Bourbon",
  "cryptid_id": 1,
  "validated_at": "2026-03-15T20:35:13Z"
}
```

### Topic: `sighting-rejected`

```json
{
  "sighting_id": "uuid-v4",
  "reason": "out_of_bounds",
  "detail": "Coordinates (41.23, -80.12) are outside Kentucky bounding box",
  "rejected_at": "2026-03-15T20:35:13Z",
  "original_message": { "...original sighting-raw payload..." }
}
```

### Topic: `threat-updates`

```json
{
  "fips": "21017",
  "county_name": "Bourbon",
  "threat_level": "moderate",
  "threat_score": 24.5,
  "sighting_count": 7,
  "top_cryptid": "bigfoot",
  "computed_at": "2026-03-15T20:40:00Z"
}
```

---

## API Response Schemas

### Sighting (GeoJSON Feature)

```json
{
  "type": "Feature",
  "geometry": {
    "type": "Point",
    "coordinates": [-85.6012, 37.7891]
  },
  "properties": {
    "id": "uuid-v4",
    "cryptid_slug": "bigfoot",
    "cryptid_name": "Bigfoot",
    "cryptid_color": "#8B4513",
    "reporter_name": "Daniel Boone",
    "description": "Large bipedal figure observed near tree line at dusk",
    "evidence_level": 3,
    "evidence_label": "blurry_photo",
    "sighting_date": "2026-03-15T20:30:00Z",
    "county_name": "Bourbon",
    "source": "user"
  }
}
```

### Stats Response

```json
{
  "total_sightings": 847,
  "sightings_30d": 142,
  "most_sighted": {
    "slug": "bigfoot",
    "name": "Bigfoot",
    "count": 312
  },
  "most_active_county": {
    "fips": "21013",
    "name": "Bell",
    "count": 45
  },
  "most_dangerous_county": {
    "fips": "21139",
    "name": "Livingston",
    "threat_level": "extreme",
    "threat_score": 87.3
  },
  "evidence_breakdown": {
    "rustling_bushes": 312,
    "strange_sound": 245,
    "blurry_photo": 178,
    "clear_photo": 89,
    "physical_evidence": 23
  }
}
```

### County Threat (GeoJSON Feature)

```json
{
  "type": "Feature",
  "geometry": { "type": "MultiPolygon", "coordinates": ["..."] },
  "properties": {
    "fips": "21139",
    "name": "Livingston",
    "threat_level": "extreme",
    "threat_score": 87.3,
    "sighting_count": 23,
    "top_cryptid": "beast-between-the-lakes",
    "color": "#7B0000"
  }
}
```

---

## Evidence Level Enum

| Value | Label | Description |
|---|---|---|
| 1 | `rustling_bushes` | Something moved. Probably. |
| 2 | `strange_sound` | Unidentifiable vocalization or noise |
| 3 | `blurry_photo` | Photographic evidence (inconclusive) |
| 4 | `clear_photo` | Photographic evidence (compelling) |
| 5 | `physical_evidence` | Footprint, hair sample, or direct physical encounter |

## Threat Level Enum

| Level | Color | Score Range | Description |
|---|---|---|---|
| `none` | `#2D5016` | 0 | No recent activity |
| `low` | `#7CB342` | 1-9 | Occasional reports, low evidence |
| `moderate` | `#FFB300` | 10-29 | Regular activity, credible reports |
| `high` | `#E65100` | 30-59 | Frequent sightings, high evidence |
| `extreme` | `#7B0000` | 60+ | Active hotspot — proceed with caution |

## Cryptid Seed Data

| Slug | Name | Danger | Habitat | First Sighted | Notable Location |
|---|---|---|---|---|---|
| `bigfoot` | Bigfoot | 3 | forest | 1782 | Green River area (Daniel Boone encounter) |
| `mothman` | Mothman | 4 | bridge, urban | 1868 | Mount Sterling |
| `pope-lick-monster` | Pope Lick Monster | 5 | bridge | 1940s | Pope Lick trestle, Louisville |
| `herrington-lake-monster` | Herrington Lake Monster | 3 | water | 1972 | Herrington Lake (Boyle/Garrard/Mercer) |
| `beast-between-the-lakes` | Beast Between the Lakes | 5 | forest | 1950s | Land Between the Lakes NRA |
| `bearilla` | Bearilla | 3 | forest | 1972 | Nicholas County |
| `spottsville-monster` | Spottsville Monster | 2 | forest | 1970s | Henderson County |
| `giraffe-possum` | Giraffe-Possum | 1 | rural | 1975 | Clark County |
| `hillbilly-beast` | Hillbilly Beast | 4 | forest | 1960s | Eastern Kentucky mountains |
| `boonesborough-octopus` | Boonesborough Octopus | 3 | water | 1944 | Kentucky River near Boonesborough |
| `sturgis-vampire` | Sturgis Vampire | 4 | urban | 1800s | Union County |
| `ufo` | UFO / UAP | 2 | sky | varies | Statewide |
