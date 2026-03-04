"""
SQLAlchemy ORM models for PostgreSQL + PostGIS.

See ai-dev/field-schema.md for complete schema definitions.
"""

import uuid

from geoalchemy2 import Geometry
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Declarative base for all PostgreSQL models."""
    pass


class Cryptid(Base):
    """Kentucky cryptid reference table."""

    __tablename__ = "cryptids"

    id = Column(Integer, primary_key=True, autoincrement=True)
    slug = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    danger_rating = Column(Integer, nullable=False)
    habitat = Column(String(50))
    icon_url = Column(String(255))
    color = Column(String(7))
    first_sighted = Column(Integer)
    notable_location = Column(String(200))
    source_type = Column(String(20))

    sightings = relationship("Sighting", back_populates="cryptid", lazy="selectin")

    def to_dict(self) -> dict:
        """Serialize cryptid to dictionary."""
        return {
            "id": self.id,
            "slug": self.slug,
            "name": self.name,
            "description": self.description,
            "danger_rating": self.danger_rating,
            "habitat": self.habitat,
            "icon_url": self.icon_url,
            "color": self.color,
            "first_sighted": self.first_sighted,
            "notable_location": self.notable_location,
            "source_type": self.source_type,
        }


class Sighting(Base):
    """Cryptid sighting event — the main data table."""

    __tablename__ = "sightings"
    __table_args__ = (
        Index("idx_sightings_geom", "geom", postgresql_using="gist"),
        Index("idx_sightings_cryptid_date", "cryptid_id", "sighting_date"),
        Index("idx_sightings_created", "created_at"),
        Index("idx_sightings_county", "county_fips"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cryptid_id = Column(Integer, ForeignKey("cryptids.id"), nullable=False)
    geom = Column(Geometry("POINT", srid=4326), nullable=False)
    reporter_name = Column(String(100), nullable=False)
    description = Column(Text)
    evidence_level = Column(Integer, default=1)
    sighting_date = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    season = Column(String(10))
    source = Column(String(20), default="user")
    source_id = Column(String(100))
    county_fips = Column(String(5))
    is_validated = Column(Boolean, default=True)
    raw_kafka_key = Column(String(100))

    cryptid = relationship("Cryptid", back_populates="sightings", lazy="selectin")


class KYCounty(Base):
    """Kentucky county boundary polygons for spatial joins."""

    __tablename__ = "ky_counties"
    __table_args__ = (
        Index("idx_counties_geom", "geom", postgresql_using="gist"),
        Index("idx_counties_fips", "fips"),
    )

    gid = Column(Integer, primary_key=True, autoincrement=True)
    fips = Column(String(5), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    geom = Column(Geometry("MULTIPOLYGON", srid=4326), nullable=False)


# Evidence level labels for API responses
EVIDENCE_LABELS = {
    1: "rustling_bushes",
    2: "strange_sound",
    3: "blurry_photo",
    4: "clear_photo",
    5: "physical_evidence",
}

# Threat level thresholds
THREAT_LEVELS = {
    "none": {"min": 0, "max": 0, "color": "#2D5016"},
    "low": {"min": 1, "max": 9, "color": "#7CB342"},
    "moderate": {"min": 10, "max": 29, "color": "#FFB300"},
    "high": {"min": 30, "max": 59, "color": "#E65100"},
    "extreme": {"min": 60, "max": float("inf"), "color": "#7B0000"},
}


def score_to_threat_level(score: float) -> str:
    """Convert a numeric threat score to a threat level string."""
    if score <= 0:
        return "none"
    elif score < 10:
        return "low"
    elif score < 30:
        return "moderate"
    elif score < 60:
        return "high"
    else:
        return "extreme"
