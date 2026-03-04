"""
Compute county-level threat levels from recent sighting data.
Writes results to Valkey for fast API access.

Usage:
    python -m scripts.compute_threat_levels
"""

import json
import logging
import sys
from pathlib import Path

import redis
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.api.config import Settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

THREAT_LEVEL_SQL = """
WITH recent_sightings AS (
    SELECT s.geom, s.evidence_level, s.cryptid_id, c.danger_rating, c.slug AS cryptid_slug
    FROM sightings s
    JOIN cryptids c ON s.cryptid_id = c.id
    WHERE s.created_at > NOW() - INTERVAL '30 days'
),
county_scores AS (
    SELECT
        k.fips,
        k.name,
        COUNT(rs.*) AS sighting_count,
        COALESCE(AVG(rs.evidence_level), 0) AS avg_evidence,
        COALESCE(MAX(rs.danger_rating), 0) AS max_danger,
        COUNT(rs.*) * COALESCE(AVG(rs.evidence_level), 0) * GREATEST(COALESCE(MAX(rs.danger_rating), 1), 1) AS threat_score,
        (
            SELECT rs2.cryptid_slug
            FROM recent_sightings rs2
            WHERE ST_Contains(k.geom, rs2.geom)
            GROUP BY rs2.cryptid_slug
            ORDER BY COUNT(*) DESC
            LIMIT 1
        ) AS top_cryptid
    FROM ky_counties k
    LEFT JOIN recent_sightings rs ON ST_Contains(k.geom, rs.geom)
    GROUP BY k.fips, k.name, k.geom
)
SELECT
    fips,
    name,
    sighting_count,
    ROUND(threat_score::numeric, 1) AS threat_score,
    top_cryptid,
    CASE
        WHEN threat_score = 0 THEN 'none'
        WHEN threat_score < 10 THEN 'low'
        WHEN threat_score < 30 THEN 'moderate'
        WHEN threat_score < 60 THEN 'high'
        WHEN threat_score < 100 THEN 'critical'
        ELSE 'apocalyptic'
    END AS threat_level
FROM county_scores
ORDER BY threat_score DESC
"""


def compute_and_cache():
    """Run the threat computation SQL and cache results in Valkey."""
    settings = Settings()

    # Sync PG engine
    db_uri = settings.pg_uri.replace("+asyncpg", "").replace("?ssl=require", "?sslmode=require")
    engine = create_engine(db_uri, echo=False)

    # Valkey connection
    valkey = redis.from_url(settings.valkey_uri, decode_responses=True)

    logger.info("Computing threat levels from PostGIS...")
    with engine.connect() as conn:
        result = conn.execute(text(THREAT_LEVEL_SQL))
        rows = result.fetchall()

    logger.info("Got %d county threat scores", len(rows))

    # Batch write to Valkey
    pipe = valkey.pipeline()
    threat_summary = {"none": 0, "low": 0, "moderate": 0, "high": 0, "critical": 0, "apocalyptic": 0}

    for row in rows:
        fips = row[0]
        name = row[1]
        sighting_count = int(row[2])
        threat_score = float(row[3])
        top_cryptid = row[4] or "none"
        threat_level = row[5]

        threat_data = {
            "level": threat_level,
            "score": str(threat_score),
            "sighting_count": str(sighting_count),
            "top_cryptid": top_cryptid,
            "county_name": name,
        }

        pipe.hset(f"threat:{fips}", mapping=threat_data)
        pipe.expire(f"threat:{fips}", 300)  # 5 min TTL

        threat_summary[threat_level] = threat_summary.get(threat_level, 0) + 1

        if threat_level not in ("none", "low"):
            logger.info(
                "  %s County (%s): %s (score=%.1f, %d sightings, top=%s)",
                name, fips, threat_level.upper(), threat_score, sighting_count, top_cryptid
            )

    pipe.execute()
    valkey.close()

    logger.info("Threat level summary: %s", threat_summary)
    logger.info("Cached to Valkey with 300s TTL.")


def main():
    """Run threat level computation."""
    logger.info("=== Computing County Threat Levels ===")
    compute_and_cache()
    logger.info("Done.")


if __name__ == "__main__":
    main()
