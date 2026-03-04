"""
Pydantic request/response schemas for the API.

See ai-dev/field-schema.md for the canonical field definitions.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# --- Request schemas ---

class SightingSubmit(BaseModel):
    """Request body for POST /api/sightings."""

    cryptid_slug: str = Field(..., description="Slug of the cryptid type")
    latitude: float = Field(..., ge=36.49, le=39.15, description="WGS84 latitude")
    longitude: float = Field(..., ge=-89.57, le=-81.96, description="WGS84 longitude")
    reporter_name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=2000)
    evidence_level: int = Field(1, ge=1, le=5)
    sighting_date: datetime | None = None


class CommentCreate(BaseModel):
    """Request body for creating a comment."""

    sighting_id: str
    user_id: int
    body: str = Field(..., min_length=1, max_length=5000)


class VoteCreate(BaseModel):
    """Request body for voting on a sighting."""

    sighting_id: str
    user_id: int
    value: int = Field(..., ge=-1, le=1)


# --- Response schemas ---

class CryptidResponse(BaseModel):
    """Cryptid reference data."""

    id: int
    slug: str
    name: str
    description: str | None = None
    danger_rating: int
    habitat: str | None = None
    icon_url: str | None = None
    color: str | None = None
    first_sighted: int | None = None
    notable_location: str | None = None
    source_type: str | None = None


class SightingProperties(BaseModel):
    """Properties block inside a GeoJSON Feature for a sighting."""

    id: str
    cryptid_slug: str
    cryptid_name: str
    cryptid_color: str | None = None
    reporter_name: str
    description: str | None = None
    evidence_level: int
    evidence_label: str
    sighting_date: str
    county_name: str | None = None
    source: str | None = None


class GeoJSONGeometry(BaseModel):
    """GeoJSON geometry object."""

    type: str
    coordinates: list[Any]


class GeoJSONFeature(BaseModel):
    """GeoJSON Feature."""

    type: str = "Feature"
    geometry: GeoJSONGeometry
    properties: dict[str, Any]


class GeoJSONFeatureCollection(BaseModel):
    """GeoJSON FeatureCollection."""

    type: str = "FeatureCollection"
    features: list[GeoJSONFeature]


class StatsResponse(BaseModel):
    """Global statistics response."""

    total_sightings: int = 0
    sightings_30d: int = 0
    most_sighted: dict[str, Any] | None = None
    most_active_county: dict[str, Any] | None = None
    most_dangerous_county: dict[str, Any] | None = None
    evidence_breakdown: dict[str, int] = {}


class ThreatResponse(BaseModel):
    """County threat level response."""

    fips: str
    name: str
    threat_level: str
    threat_score: float
    sighting_count: int
    top_cryptid: str | None = None


class SightingAccepted(BaseModel):
    """Response for POST /api/sightings (202 Accepted)."""

    sighting_id: str
    status: str = "pending"


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
    service: str = "cryptid-tracker-ky"
    services: dict[str, str] = {}
