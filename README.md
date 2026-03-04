# Cryptid Tracker KY

![Aiven Free Tier](https://img.shields.io/badge/Aiven-Free_Tier-FF5733?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48Y2lyY2xlIGN4PSIxMiIgY3k9IjEyIiByPSIxMCIgZmlsbD0id2hpdGUiLz48L3N2Zz4=)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-PostGIS-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![Apache Kafka](https://img.shields.io/badge/Apache_Kafka-Streaming-231F20?style=for-the-badge&logo=apachekafka&logoColor=white)
![Valkey](https://img.shields.io/badge/Valkey-Cache-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-Community-4479A1?style=for-the-badge&logo=mysql&logoColor=white)
![Python](https://img.shields.io/badge/Python-FastAPI-3776AB?style=for-the-badge&logo=python&logoColor=white)
![MapLibre](https://img.shields.io/badge/MapLibre_GL-JS-396CB2?style=for-the-badge&logo=maplibre&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)
![WCAG](https://img.shields.io/badge/WCAG-2.1%20AA-green)

![Threat Level](https://img.shields.io/badge/KY_Threat_Level-EXTREME-7B0000?style=for-the-badge)
![Cryptids Tracked](https://img.shields.io/badge/Cryptids_Tracked-12-orange?style=for-the-badge)
![Bigfoot Danger](https://img.shields.io/badge/Bigfoot_Danger-★★★☆☆-8B4513?style=for-the-badge)

**Real-time Kentucky cryptid sighting tracker** — built for the [Aiven Free Tier Competition](https://aiven.io/blog/the-aiven-free-tier-competition).

> *Applying enterprise streaming architecture to Kentucky's most pressing geospatial problem.*

## What Is This?

A web application that tracks cryptid sightings across Kentucky. Users submit sightings on an interactive map; sightings stream through Apache Kafka, are validated and stored in PostGIS, cached in Valkey, and rendered on a MapLibre GL frontend showing sighting clusters and county-level "threat levels."

Real historical data from the [BFRO](https://www.bfro.net/) (Bigfoot sightings) and [NUFORC](https://nuforc.org/) (UFO reports) seed the map alongside synthetic sightings for Kentucky's documented cryptid menagerie: the Pope Lick Monster, Beast Between the Lakes, Herrington Lake Monster, Bearilla, and more.

## Architecture

```
User → FastAPI → Kafka (sighting-raw) → Consumer → PostgreSQL+PostGIS + Valkey
                                                  → Kafka (sighting-validated)

Frontend (MapLibre GL) ← FastAPI ← PostgreSQL (spatial) + Valkey (cache)

Community features (comments, votes) → MySQL
```

**Four Aiven free tier services, each with a genuine role:**

- **PostgreSQL + PostGIS** — Spatial data store. Sighting geometry, county boundaries, cryptid references. Spatial indexes, ST_Contains for county joins, ST_ClusterDBSCAN for hotspot detection.
- **Apache Kafka** — Event streaming. Decouples sighting submission from processing. Enables the validation consumer pipeline and real-time generator demo.
- **Valkey** — Computed cache layer. County threat levels, live stats, recent sightings feed, reporter leaderboard. Eliminates repeated expensive spatial queries.
- **MySQL** — Community features. User accounts, comments on sightings, credibility votes.

## Kentucky Cryptids

| Creature | Danger Rating | Known Habitat |
|---|---|---|
| Bigfoot | ★★★☆☆ | Forests statewide |
| Pope Lick Monster | ★★★★★ | Pope Lick trestle, Louisville |
| Beast Between the Lakes | ★★★★★ | Land Between the Lakes NRA |
| Mothman | ★★★★☆ | Bridges, urban areas |
| Herrington Lake Monster | ★★★☆☆ | Herrington Lake |
| Bearilla | ★★★☆☆ | Nicholas County forests |
| Hillbilly Beast | ★★★★☆ | Eastern Kentucky mountains |
| Sturgis Vampire | ★★★★☆ | Union County |
| Spottsville Monster | ★★☆☆☆ | Henderson County |
| Giraffe-Possum | ★☆☆☆☆ | Clark County (rural) |
| Boonesborough Octopus | ★★★☆☆ | Kentucky River |
| UFO / UAP | ★★☆☆☆ | Statewide |

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/chrislyonsKY/cryptid-tracker-ky.git
cd cryptid-tracker-ky
pip install -r requirements.txt

# 2. Configure Aiven connections
cp .env.example .env
# Edit .env with your Aiven service URIs

# 3. Set up databases
python -m scripts.setup_db

# 4. Seed data
python -m scripts.seed_bfro
python -m scripts.seed_nuforc

# 5. Start the consumer
python -m src.consumer.main &

# 6. Start the API
uvicorn src.api.main:app --reload

# 7. Open the map
# http://localhost:8000

# 8. (Optional) Stream synthetic sightings
python -m src.generator.main --mode stream
```

## Data Sources

- **BFRO Bigfoot Sightings** — [data.world](https://data.world/timothyrenner/bfro-sightings-data) / [GitHub](https://github.com/timothyrenner/bfro_sightings_data)
- **NUFORC UFO Reports** — [GitHub](https://github.com/timothyrenner/nuforc_sightings_data) / [Kaggle](https://www.kaggle.com/datasets/NUFORC/ufo-sightings)
- **KY County Boundaries** — [US Census TIGER/Line](https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html)
- **Kentucky Cryptid Folklore** — Various published sources; see `ai-dev/decisions/DL-002-real-data-plus-synthetic.md`

## Built With

Python (FastAPI) · PostgreSQL + PostGIS · Apache Kafka · Valkey · MySQL · MapLibre GL JS

All managed services on [Aiven Free Tier](https://console.aiven.io/signup).

---

**#AivenFreeTier**
