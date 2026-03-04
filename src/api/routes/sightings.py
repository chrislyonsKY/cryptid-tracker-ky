"""
Sighting routes — submit and query cryptid sightings.

See ai-dev/field-schema.md for request/response schemas.
See ai-dev/architecture.md for endpoint specifications.
"""

import json
import logging
import uuid
from datetime import datetime, timezone

from confluent_kafka import Producer
from fastapi import APIRouter, Depends, HTTPException, Query
from geoalchemy2.functions import ST_AsGeoJSON, ST_Intersects, ST_MakeEnvelope, ST_X, ST_Y
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.deps import get_kafka_producer, get_valkey
from src.api.models import Cryptid, Sighting, EVIDENCE_LABELS
from src.api.models.database import get_db
from src.api.models.schemas import (
    GeoJSONFeature,
    GeoJSONFeatureCollection,
    GeoJSONGeometry,
    SightingAccepted,
    SightingSubmit,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["sightings"])


def _sighting_to_feature(row) -> dict:
    """Convert a sighting query row (Sighting, lon, lat) to a GeoJSON Feature dict."""
    sighting = row[0]
    lon = row[1]
    lat = row[2]

    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [lon, lat],
        },
        "properties": {
            "id": str(sighting.id),
            "cryptid_slug": sighting.cryptid.slug if sighting.cryptid else None,
            "cryptid_name": sighting.cryptid.name if sighting.cryptid else None,
            "cryptid_color": sighting.cryptid.color if sighting.cryptid else None,
            "reporter_name": sighting.reporter_name,
            "description": sighting.description,
            "evidence_level": sighting.evidence_level,
            "evidence_label": EVIDENCE_LABELS.get(sighting.evidence_level, "unknown"),
            "sighting_date": sighting.sighting_date.isoformat() if sighting.sighting_date else None,
            "county_fips": sighting.county_fips,
            "source": sighting.source,
        },
    }


@router.post("/sightings", response_model=SightingAccepted, status_code=202)
async def submit_sighting(
    body: SightingSubmit,
    producer: Producer = Depends(get_kafka_producer),
):
    """Submit a new sighting — publishes to Kafka for async processing."""
    sighting_id = str(uuid.uuid4())
    message = {
        "sighting_id": sighting_id,
        "cryptid_slug": body.cryptid_slug,
        "latitude": body.latitude,
        "longitude": body.longitude,
        "reporter_name": body.reporter_name,
        "description": body.description,
        "evidence_level": body.evidence_level,
        "sighting_date": (body.sighting_date or datetime.now(timezone.utc)).isoformat(),
        "source": "user",
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        producer.produce(
            topic="sighting-raw",
            key=sighting_id.encode("utf-8"),
            value=json.dumps(message).encode("utf-8"),
            callback=_delivery_callback,
        )
        producer.poll(0)
        logger.info("Produced sighting %s to Kafka", sighting_id)
    except Exception:
        logger.exception("Failed to produce sighting %s", sighting_id)
        raise HTTPException(status_code=503, detail="Sighting submission temporarily unavailable")

    return SightingAccepted(sighting_id=sighting_id, status="pending")


@router.get("/sightings")
async def get_sightings(
    bbox: str | None = Query(None, description="minLon,minLat,maxLon,maxLat"),
    cryptid: str | None = Query(None, description="Filter by cryptid slug"),
    evidence_min: int | None = Query(None, ge=1, le=5),
    after: str | None = Query(None, description="ISO 8601 date"),
    before: str | None = Query(None, description="ISO 8601 date"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve sightings as GeoJSON FeatureCollection with optional spatial filter."""
    query = (
        select(
            Sighting,
            ST_X(Sighting.geom).label("lon"),
            ST_Y(Sighting.geom).label("lat"),
        )
        .options(selectinload(Sighting.cryptid))
        .join(Cryptid, Sighting.cryptid_id == Cryptid.id)
    )

    if bbox:
        try:
            min_lon, min_lat, max_lon, max_lat = [float(v) for v in bbox.split(",")]
            query = query.where(
                ST_Intersects(
                    Sighting.geom,
                    ST_MakeEnvelope(min_lon, min_lat, max_lon, max_lat, 4326),
                )
            )
        except ValueError:
            raise HTTPException(400, "Invalid bbox format. Expected: minLon,minLat,maxLon,maxLat")

    if cryptid:
        query = query.where(Cryptid.slug == cryptid)

    if evidence_min:
        query = query.where(Sighting.evidence_level >= evidence_min)

    if after:
        query = query.where(Sighting.sighting_date >= after)

    if before:
        query = query.where(Sighting.sighting_date <= before)

    query = query.order_by(Sighting.sighting_date.desc()).limit(limit).offset(offset)

    result = await db.execute(query)
    rows = result.all()

    features = [_sighting_to_feature(row) for row in rows]
    return {"type": "FeatureCollection", "features": features}


@router.get("/sightings/recent")
async def get_recent_sightings(valkey=Depends(get_valkey)):
    """Get recent sightings from Valkey cache."""
    try:
        raw = await valkey.lrange("recent:sightings", 0, 49)
        return [json.loads(item) for item in raw]
    except Exception:
        logger.exception("Failed to get recent sightings from cache")
        return []


@router.get("/sightings/{sighting_id}")
async def get_sighting(
    sighting_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a single sighting by UUID."""
    query = (
        select(
            Sighting,
            ST_X(Sighting.geom).label("lon"),
            ST_Y(Sighting.geom).label("lat"),
        )
        .options(selectinload(Sighting.cryptid))
        .join(Cryptid, Sighting.cryptid_id == Cryptid.id)
        .where(Sighting.id == sighting_id)
    )
    result = await db.execute(query)
    row = result.first()

    if not row:
        raise HTTPException(404, "Sighting not found")

    return _sighting_to_feature(row)


def _delivery_callback(err, msg):
    """Kafka delivery report callback."""
    if err:
        logger.error("Kafka delivery failed for %s: %s", msg.key(), err)
    else:
        logger.debug("Delivered %s to %s [%d]", msg.key(), msg.topic(), msg.partition())
