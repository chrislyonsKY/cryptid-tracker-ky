"""
ETL: NUFORC (National UFO Reporting Center) Kentucky sightings → PostgreSQL.
Downloads NUFORC data and loads KY sightings into the sightings table.

Usage:
    python -m scripts.seed_nuforc
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

# NUFORC geocoded dataset (Tim Renner / data.world)
NUFORC_CSV_URL = "https://raw.githubusercontent.com/timothyrenner/nuforc_sightings_data/master/nuforc_reports.csv"
LOCAL_CSV = Path(__file__).resolve().parent.parent / "data" / "seed" / "nuforc_reports.csv"

# Kentucky bounding box
KY_LAT_MIN, KY_LAT_MAX = 36.49, 39.15
KY_LON_MIN, KY_LON_MAX = -89.57, -81.96

# Duration keywords to evidence level
DURATION_EVIDENCE_MAP = {
    "seconds": 1,
    "minute": 2,
    "minutes": 3,
    "hour": 4,
    "hours": 5,
}


def estimate_evidence(duration_str: str, shape: str) -> int:
    """Estimate evidence level from NUFORC duration and shape fields."""
    if not duration_str:
        return 2

    duration_lower = duration_str.lower()
    for keyword, level in DURATION_EVIDENCE_MAP.items():
        if keyword in duration_lower:
            return min(level, 5)

    return 2  # default


def get_season(month: int) -> str:
    """Get season from month number."""
    if month in (3, 4, 5):
        return "spring"
    elif month in (6, 7, 8):
        return "summer"
    elif month in (9, 10, 11):
        return "fall"
    return "winter"


def download_nuforc_data() -> list[dict]:
    """Download NUFORC CSV and filter to Kentucky sightings."""
    if LOCAL_CSV.exists():
        logger.info("Loading from local cache: %s", LOCAL_CSV)
        with open(LOCAL_CSV, "r", encoding="utf-8", errors="replace") as f:
            raw = f.read()
    else:
        logger.info("Downloading NUFORC sightings data (this may take a moment)...")
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        req = urllib.request.Request(NUFORC_CSV_URL, headers={"User-Agent": "CryptidTrackerKY/1.0"})
        with urllib.request.urlopen(req, context=ssl_context) as resp:
            raw = resp.read().decode("utf-8", errors="replace")

        LOCAL_CSV.parent.mkdir(parents=True, exist_ok=True)
        with open(LOCAL_CSV, "w", encoding="utf-8") as f:
            f.write(raw)
        logger.info("Saved to %s", LOCAL_CSV)

    reader = csv.DictReader(io.StringIO(raw))
    ky_sightings = []

    for row in reader:
        # Filter by state
        state = row.get("state", "").strip().upper()
        if state != "KY":
            continue

        try:
            lat = float(row.get("city_latitude", 0))
            lon = float(row.get("city_longitude", 0))
        except (ValueError, TypeError):
            continue

        # Validate bounds
        if not (KY_LAT_MIN <= lat <= KY_LAT_MAX and KY_LON_MIN <= lon <= KY_LON_MAX):
            continue

        # Skip zero coordinates
        if lat == 0 or lon == 0:
            continue

        # Parse date
        sighting_date = None
        date_str = row.get("date_time", "")
        for fmt in ("%m/%d/%Y %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                sighting_date = datetime.strptime(date_str.strip(), fmt)
                break
            except (ValueError, AttributeError):
                continue

        month = sighting_date.month if sighting_date else 7
        duration = row.get("duration", "")
        shape = row.get("shape", "")
        evidence = estimate_evidence(duration, shape)

        # Build description
        summary = row.get("summary", "") or row.get("text", "")
        description = summary[:2000] if summary else f"UFO sighting ({shape}) in {row.get('city', 'Kentucky')}"

        city = row.get("city", "Unknown")

        ky_sightings.append({
            "id": str(uuid4()),
            "latitude": lat,
            "longitude": lon,
            "reporter_name": f"NUFORC Reporter ({city})",
            "description": description,
            "evidence_level": evidence,
            "sighting_date": sighting_date or datetime(2000, 1, 1),
            "season": get_season(month),
            "source": "nuforc",
            "source_id": f"nuforc-{hash(date_str + str(lat) + str(lon)) & 0xFFFFFFFF:08x}",
        })

    logger.info("Found %d Kentucky NUFORC sightings", len(ky_sightings))
    return ky_sightings


def load_into_postgres(sightings: list[dict]) -> int:
    """Insert NUFORC sightings into PostgreSQL."""
    settings = Settings()
    db_uri = settings.pg_uri.replace("+asyncpg", "").replace("?ssl=require", "?sslmode=require")
    engine = create_engine(db_uri, echo=False)

    # Look up UfO cryptid_id
    with engine.connect() as conn:
        result = conn.execute(text("SELECT id FROM cryptids WHERE slug = 'ufo'"))
        row = result.fetchone()
        if not row:
            logger.error("Cryptid 'ufo' not found in database — run seed first!")
            return 0
        ufo_id = row[0]

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
                    "cryptid_id": ufo_id,
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
                logger.error("Failed to insert NUFORC sighting %s: %s", s["source_id"], e)

    logger.info("Loaded %d NUFORC sightings", loaded)
    return loaded


def main():
    """Download and seed NUFORC Kentucky UFO sightings."""
    logger.info("=== Seeding NUFORC Kentucky UFO Sightings ===")
    sightings = download_nuforc_data()
    if sightings:
        count = load_into_postgres(sightings)
        logger.info("Done. %d sightings seeded.", count)
    else:
        logger.warning("No Kentucky sightings found in NUFORC data.")


if __name__ == "__main__":
    main()
