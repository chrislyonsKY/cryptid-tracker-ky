"""
ETL: BFRO (Bigfoot Field Researchers Organization) Kentucky sightings → PostgreSQL.
Downloads BFRO data and loads KY sightings into the sightings table.

Data source: BFRO public sighting database (pre-scraped CSV at data.world).

Usage:
    python -m scripts.seed_bfro
"""

import csv
import io
import json
import logging
import ssl
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import certifi
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.api.config import Settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# BFRO geocoded sighting database (Tim Renner / data.world)
BFRO_CSV_URL = "https://raw.githubusercontent.com/timothyrenner/bfro_sightings_data/master/bfro_reports_geocoded.csv"
LOCAL_CSV = Path(__file__).resolve().parent.parent / "data" / "seed" / "bfro_geocoded.csv"

# Kentucky bounding box
KY_LAT_MIN, KY_LAT_MAX = 36.49, 39.15
KY_LON_MIN, KY_LON_MAX = -89.57, -81.96

# Map BFRO classification to evidence level
# Class A = clear observation → 4
# Class B = sounds/smells/indirect → 2
# Class C = secondhand report → 1
BFRO_CLASS_TO_EVIDENCE = {
    "Class A": 4,
    "Class B": 2,
    "Class C": 1,
}


def get_season(month: int) -> str:
    """Get season from month number."""
    if month in (3, 4, 5):
        return "spring"
    elif month in (6, 7, 8):
        return "summer"
    elif month in (9, 10, 11):
        return "fall"
    return "winter"


def download_bfro_data() -> list[dict]:
    """Download BFRO CSV and filter to Kentucky sightings."""
    if LOCAL_CSV.exists():
        logger.info("Loading from local cache: %s", LOCAL_CSV)
        with open(LOCAL_CSV, "r", encoding="utf-8", errors="replace") as f:
            raw = f.read()
    else:
        logger.info("Downloading BFRO geocoded data...")
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        req = urllib.request.Request(BFRO_CSV_URL, headers={"User-Agent": "CryptidTrackerKY/1.0"})
        with urllib.request.urlopen(req, context=ssl_context) as resp:
            raw = resp.read().decode("utf-8", errors="replace")

        # Save locally
        LOCAL_CSV.parent.mkdir(parents=True, exist_ok=True)
        with open(LOCAL_CSV, "w", encoding="utf-8") as f:
            f.write(raw)
        logger.info("Saved to %s", LOCAL_CSV)

    reader = csv.DictReader(io.StringIO(raw))
    ky_sightings = []

    for row in reader:
        try:
            lat = float(row.get("latitude", 0))
            lon = float(row.get("longitude", 0))
        except (ValueError, TypeError):
            continue

        # Filter to Kentucky bounds
        if not (KY_LAT_MIN <= lat <= KY_LAT_MAX and KY_LON_MIN <= lon <= KY_LON_MAX):
            continue

        # Parse date
        sighting_date = None
        date_str = row.get("date", "")
        try:
            if date_str:
                sighting_date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            pass

        month = sighting_date.month if sighting_date else 7  # default summer

        classification = row.get("classification", "Class B")
        evidence_level = BFRO_CLASS_TO_EVIDENCE.get(classification, 2)

        # Build title from observed field
        observed = row.get("observed", "")
        description = observed[:2000] if observed else f"BFRO Report #{row.get('number', 'unknown')}"

        ky_sightings.append({
            "id": str(uuid4()),
            "latitude": lat,
            "longitude": lon,
            "reporter_name": "BFRO Investigator",
            "description": description,
            "evidence_level": evidence_level,
            "sighting_date": sighting_date or datetime(2000, 1, 1),
            "season": get_season(month),
            "source": "bfro",
            "source_id": f"bfro-{row.get('number', 'unknown')}",
        })

    logger.info("Found %d Kentucky BFRO sightings", len(ky_sightings))
    return ky_sightings


def load_into_postgres(sightings: list[dict]) -> int:
    """Insert BFRO sightings into PostgreSQL."""
    settings = Settings()
    db_uri = settings.pg_uri.replace("+asyncpg", "").replace("?ssl=require", "?sslmode=require")
    engine = create_engine(db_uri, echo=False)

    # Look up the bigfoot cryptid_id
    with engine.connect() as conn:
        result = conn.execute(text("SELECT id FROM cryptids WHERE slug = 'bigfoot'"))
        row = result.fetchone()
        if not row:
            logger.error("Cryptid 'bigfoot' not found in database — run seed first!")
            return 0
        bigfoot_id = row[0]

    loaded = 0
    with engine.begin() as conn:
        for s in sightings:
            try:
                conn.execute(text("""
                    INSERT INTO sightings (
                        id, cryptid_id, geom, reporter_name, description,
                        evidence_level, sighting_date, season, source, source_id,
                        is_validated, created_at
                    ) VALUES (
                        :id::uuid, :cryptid_id,
                        ST_SetSRID(ST_MakePoint(:lon, :lat), 4326),
                        :reporter, :description,
                        :evidence, :sighting_date, :season, :source, :source_id,
                        TRUE, :sighting_date
                    )
                    ON CONFLICT DO NOTHING
                """), {
                    "id": s["id"],
                    "cryptid_id": bigfoot_id,
                    "lon": s["longitude"],
                    "lat": s["latitude"],
                    "reporter": s["reporter_name"],
                    "description": s["description"],
                    "evidence": s["evidence_level"],
                    "sighting_date": s["sighting_date"],
                    "season": s["season"],
                    "source": s["source"],
                    "source_id": s["source_id"],
                })
                loaded += 1
            except Exception as e:
                logger.error("Failed to insert BFRO sighting %s: %s", s["source_id"], e)

    logger.info("Loaded %d BFRO sightings", loaded)
    return loaded


def main():
    """Download and seed BFRO Kentucky sightings."""
    logger.info("=== Seeding BFRO Kentucky Bigfoot Sightings ===")
    sightings = download_bfro_data()
    if sightings:
        count = load_into_postgres(sightings)
        logger.info("Done. %d sightings seeded.", count)
    else:
        logger.warning("No Kentucky sightings found in BFRO data.")


if __name__ == "__main__":
    main()
