"""County boundaries and threat level routes."""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from geoalchemy2.functions import ST_AsGeoJSON, ST_SimplifyPreserveTopology
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_valkey
from src.api.models import KYCounty, THREAT_LEVELS, score_to_threat_level
from src.api.models.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(tags=["counties"])

# In-memory cache for county GeoJSON (rarely changes)
_counties_cache: dict | None = None


@router.get("/counties")
async def get_counties(db: AsyncSession = Depends(get_db), valkey=Depends(get_valkey)):
    """Get all KY counties as GeoJSON with threat level properties."""
    global _counties_cache

    # Check if we have cached base geometries
    if _counties_cache is None:
        query = select(
            KYCounty.fips,
            KYCounty.name,
            ST_AsGeoJSON(
                ST_SimplifyPreserveTopology(KYCounty.geom, 0.005)
            ).label("geojson"),
        )
        result = await db.execute(query)
        rows = result.all()
        _counties_cache = [
            {"fips": row.fips, "name": row.name, "geometry": json.loads(row.geojson)}
            for row in rows
        ]
        logger.info("Cached %d county geometries", len(_counties_cache))

    features = []
    for county in _counties_cache:
        # Get cached threat data
        threat_data = {}
        try:
            threat_data = await valkey.hgetall(f"threat:{county['fips']}")
        except Exception:
            pass

        threat_level = threat_data.get("level", "none")
        threat_score = float(threat_data.get("score", 0))
        sighting_count = int(threat_data.get("sighting_count", 0))
        color = THREAT_LEVELS.get(threat_level, THREAT_LEVELS["none"])["color"]

        features.append({
            "type": "Feature",
            "geometry": county["geometry"],
            "properties": {
                "fips": county["fips"],
                "name": county["name"],
                "threat_level": threat_level,
                "threat_score": threat_score,
                "sighting_count": sighting_count,
                "top_cryptid": threat_data.get("top_cryptid"),
                "color": color,
            },
        })

    return {"type": "FeatureCollection", "features": features}


@router.get("/counties/{fips}/threat")
async def get_county_threat(fips: str, valkey=Depends(get_valkey)):
    """Get threat level detail for a specific county."""
    try:
        threat_data = await valkey.hgetall(f"threat:{fips}")

        if not threat_data:
            return {
                "fips": fips,
                "threat_level": "none",
                "threat_score": 0,
                "sighting_count": 0,
                "top_cryptid": None,
            }

        return {
            "fips": fips,
            "name": threat_data.get("name", ""),
            "threat_level": threat_data.get("level", "none"),
            "threat_score": float(threat_data.get("score", 0)),
            "sighting_count": int(threat_data.get("sighting_count", 0)),
            "top_cryptid": threat_data.get("top_cryptid"),
        }
    except Exception:
        logger.exception("Failed to get threat for county %s", fips)
        raise HTTPException(503, "Threat data temporarily unavailable")
