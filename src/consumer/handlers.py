"""
Sighting handlers — DB write + Valkey cache updates after validation.

Called by the consumer when a sighting passes validation.
"""

import json
import logging
from datetime import datetime, timezone

import redis
from confluent_kafka import Producer
from geoalchemy2.functions import ST_Contains
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from src.api.config import settings
from src.api.models import Cryptid, KYCounty, Sighting, EVIDENCE_LABELS

logger = logging.getLogger(__name__)


class SightingHandlers:
    """Handles validated sightings: DB insert, cache update, republish."""

    def __init__(
        self,
        db_session_factory: sessionmaker,
        valkey_client: redis.Redis,
        kafka_producer: Producer,
    ):
        self._Session = db_session_factory
        self._valkey = valkey_client
        self._producer = kafka_producer

    def process_sighting(self, sighting: dict) -> None:
        """Insert valid sighting into PostGIS, update Valkey, republish."""
        sighting_id = sighting.get("sighting_id", "unknown")
        logger.info("Processing validated sighting %s", sighting_id)

        with self._Session() as session:
            try:
                # Resolve cryptid_id from slug
                cryptid = session.execute(
                    select(Cryptid).where(Cryptid.slug == sighting["cryptid_slug"])
                ).scalar_one_or_none()

                if not cryptid:
                    logger.error("Cryptid slug %s not found", sighting["cryptid_slug"])
                    return

                lat = float(sighting["latitude"])
                lon = float(sighting["longitude"])

                # Determine county via spatial join
                county_fips = None
                county_name = None
                county_row = session.execute(
                    select(KYCounty.fips, KYCounty.name).where(
                        ST_Contains(
                            KYCounty.geom,
                            text(f"ST_SetSRID(ST_MakePoint({lon}, {lat}), 4326)")
                        )
                    )
                ).first()

                if county_row:
                    county_fips = county_row.fips
                    county_name = county_row.name

                # Determine season
                sighting_date_str = sighting.get("sighting_date")
                if sighting_date_str:
                    try:
                        dt = datetime.fromisoformat(sighting_date_str.replace("Z", "+00:00"))
                    except ValueError:
                        dt = datetime.now(timezone.utc)
                else:
                    dt = datetime.now(timezone.utc)

                month = dt.month
                if month in (3, 4, 5):
                    season = "spring"
                elif month in (6, 7, 8):
                    season = "summer"
                elif month in (9, 10, 11):
                    season = "fall"
                else:
                    season = "winter"

                # INSERT into sightings table
                new_sighting = Sighting(
                    id=sighting_id,
                    cryptid_id=cryptid.id,
                    geom=text(f"ST_SetSRID(ST_MakePoint({lon}, {lat}), 4326)"),
                    reporter_name=sighting["reporter_name"],
                    description=sighting.get("description"),
                    evidence_level=int(sighting.get("evidence_level", 1)),
                    sighting_date=dt,
                    season=season,
                    source=sighting.get("source", "user"),
                    source_id=sighting.get("source_id"),
                    county_fips=county_fips,
                    is_validated=True,
                    raw_kafka_key=sighting_id,
                )
                session.add(new_sighting)
                session.commit()
                logger.info("Inserted sighting %s into PostgreSQL", sighting_id)

                # Update Valkey caches
                self._update_caches(sighting, cryptid, county_fips, county_name)

                # Publish to sighting-validated topic
                validated_msg = {
                    **sighting,
                    "county_fips": county_fips,
                    "county_name": county_name,
                    "cryptid_id": cryptid.id,
                    "validated_at": datetime.now(timezone.utc).isoformat(),
                }
                self._producer.produce(
                    topic="sighting-validated",
                    key=sighting_id.encode("utf-8"),
                    value=json.dumps(validated_msg).encode("utf-8"),
                )
                self._producer.poll(0)

            except Exception:
                session.rollback()
                logger.exception("Error processing sighting %s", sighting_id)

    def _update_caches(
        self, sighting: dict, cryptid: Cryptid, county_fips: str | None, county_name: str | None
    ) -> None:
        """Update Valkey caches after successful DB insert."""
        try:
            pipe = self._valkey.pipeline()

            # Global stats
            pipe.hincrby("stats:global", "total_sightings", 1)
            pipe.hincrby("stats:global", f"{sighting['cryptid_slug']}_count", 1)

            # Recent sightings (capped at 50)
            recent_entry = {
                "sighting_id": sighting["sighting_id"],
                "cryptid_slug": sighting["cryptid_slug"],
                "cryptid_name": cryptid.name,
                "cryptid_color": cryptid.color,
                "reporter_name": sighting["reporter_name"],
                "description": sighting.get("description"),
                "evidence_level": int(sighting.get("evidence_level", 1)),
                "evidence_label": EVIDENCE_LABELS.get(int(sighting.get("evidence_level", 1)), "unknown"),
                "latitude": float(sighting["latitude"]),
                "longitude": float(sighting["longitude"]),
                "county_name": county_name,
                "sighting_date": sighting.get("sighting_date"),
                "source": sighting.get("source", "user"),
            }
            pipe.lpush("recent:sightings", json.dumps(recent_entry))
            pipe.ltrim("recent:sightings", 0, 49)

            # Reporter leaderboard
            pipe.zincrby("leaderboard:reporters", 1, sighting["reporter_name"])

            pipe.execute()
            logger.debug("Updated Valkey caches for sighting %s", sighting["sighting_id"])
        except Exception:
            logger.exception("Failed to update Valkey caches")
