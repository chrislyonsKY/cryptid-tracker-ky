"""
Load Kentucky county boundaries into PostGIS from US Census TIGER/Line GeoJSON.
Downloads the data, simplifies geometry, and inserts into ky_counties table.

Usage:
    python -m scripts.load_counties
"""

import json
import logging
import os
import ssl
import sys
import urllib.request
from pathlib import Path

import certifi
from sqlalchemy import create_engine, text

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.api.config import Settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# US Census TIGER/Line GeoJSON for Kentucky counties (FIPS state code 21)
CENSUS_URL = "https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json"
# Alternative: direct Census cartographic boundary (simplified, smaller)
CARTOGRAPHIC_URL = "https://raw.githubusercontent.com/deldersveld/topojson/master/countries/us-states/KY-21-kentucky-counties.json"

# If we have a local file already
LOCAL_GEOJSON = Path(__file__).resolve().parent.parent / "data" / "ky_counties.geojson"


def download_ky_counties() -> dict:
    """Download Kentucky county boundaries from Census cartographic boundaries."""
    # First check if we have a local file
    if LOCAL_GEOJSON.exists():
        logger.info("Loading counties from local file: %s", LOCAL_GEOJSON)
        with open(LOCAL_GEOJSON, "r", encoding="utf-8") as f:
            return json.load(f)

    # Download the full US counties GeoJSON and filter to KY (FIPS starts with '21')
    logger.info("Downloading US county boundaries from plotly/datasets...")
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    req = urllib.request.Request(CENSUS_URL, headers={"User-Agent": "CryptidTrackerKY/1.0"})
    with urllib.request.urlopen(req, context=ssl_context) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    # Filter to Kentucky counties only
    ky_features = [
        f for f in data["features"]
        if f["properties"].get("STATE", f["id"][:2]) == "21"
        or (isinstance(f.get("id"), str) and f["id"].startswith("21"))
    ]
    logger.info("Found %d Kentucky county features", len(ky_features))

    ky_geojson = {
        "type": "FeatureCollection",
        "features": ky_features,
    }

    # Save locally for next time
    LOCAL_GEOJSON.parent.mkdir(parents=True, exist_ok=True)
    with open(LOCAL_GEOJSON, "w", encoding="utf-8") as f:
        json.dump(ky_geojson, f)
    logger.info("Saved to %s", LOCAL_GEOJSON)

    return ky_geojson


def load_into_postgis(geojson: dict) -> int:
    """Insert county features into the ky_counties PostGIS table."""
    settings = Settings()
    # Convert asyncpg URI to psycopg2
    db_uri = settings.pg_uri.replace("+asyncpg", "").replace("?ssl=require", "?sslmode=require")
    engine = create_engine(db_uri, echo=False)

    loaded = 0
    with engine.begin() as conn:
        # Ensure table exists
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ky_counties (
                gid SERIAL PRIMARY KEY,
                fips VARCHAR(5) UNIQUE NOT NULL,
                name VARCHAR(100) NOT NULL,
                geom geometry(MultiPolygon, 4326) NOT NULL
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_counties_geom ON ky_counties USING GIST(geom)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_counties_fips ON ky_counties(fips)"))

        for feature in geojson["features"]:
            props = feature.get("properties", {})

            # Extract FIPS code - handle different formats
            fips = (
                feature.get("id")
                or props.get("GEOID")
                or props.get("FIPS")
                or props.get("fips")
                or f"21{props.get('COUNTYFP', '000')}"
            )
            fips = str(fips).zfill(5)

            # Extract name
            name = (
                props.get("NAME")
                or props.get("name")
                or props.get("NAMELSAD", "").replace(" County", "")
                or "Unknown"
            )

            # Convert geometry to GeoJSON string
            geom_json = json.dumps(feature["geometry"])

            # Ensure MultiPolygon (some may be Polygon)
            geom_type = feature["geometry"]["type"]

            try:
                if geom_type == "Polygon":
                    # Wrap in MultiPolygon
                    conn.execute(text("""
                        INSERT INTO ky_counties (fips, name, geom)
                        VALUES (
                            :fips,
                            :name,
                            ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326))
                        )
                        ON CONFLICT (fips) DO UPDATE SET
                            name = EXCLUDED.name,
                            geom = EXCLUDED.geom
                    """), {"fips": fips, "name": name, "geom": geom_json})
                else:
                    conn.execute(text("""
                        INSERT INTO ky_counties (fips, name, geom)
                        VALUES (
                            :fips,
                            :name,
                            ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326)
                        )
                        ON CONFLICT (fips) DO UPDATE SET
                            name = EXCLUDED.name,
                            geom = EXCLUDED.geom
                    """), {"fips": fips, "name": name, "geom": geom_json})

                loaded += 1
            except Exception as e:
                logger.error("Failed to load county %s (%s): %s", fips, name, e)

    logger.info("Loaded %d counties into PostGIS", loaded)
    return loaded


def main():
    """Download and load KY county boundaries."""
    logger.info("=== Loading Kentucky County Boundaries ===")
    geojson = download_ky_counties()
    count = load_into_postgis(geojson)
    logger.info("Done. %d counties loaded.", count)


if __name__ == "__main__":
    main()
