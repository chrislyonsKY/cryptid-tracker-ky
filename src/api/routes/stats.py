"""Live stats and leaderboard routes (Valkey-backed)."""

import logging

from fastapi import APIRouter, Depends

from src.api.deps import get_valkey

logger = logging.getLogger(__name__)
router = APIRouter(tags=["stats"])


_EMPTY_STATS = {
    "total_sightings": 0,
    "sightings_30d": 0,
    "most_sighted": None,
    "most_active_county": None,
    "most_dangerous_county": None,
    "evidence_breakdown": {},
}


@router.get("/stats")
async def get_stats(valkey=Depends(get_valkey)):
    """Get global sighting statistics from Valkey cache."""
    if not valkey:
        return _EMPTY_STATS
    try:
        raw = await valkey.hgetall("stats:global")

        if not raw:
            return {
                "total_sightings": 0,
                "sightings_30d": 0,
                "most_sighted": None,
                "most_active_county": None,
                "most_dangerous_county": None,
                "evidence_breakdown": {},
            }

        total = int(raw.get("total_sightings", 0))

        # Find most-sighted cryptid from the *_count keys
        cryptid_counts = {}
        for key, val in raw.items():
            if key.endswith("_count"):
                slug = key.replace("_count", "")
                cryptid_counts[slug] = int(val)

        most_sighted = None
        if cryptid_counts:
            top_slug = max(cryptid_counts, key=cryptid_counts.get)
            most_sighted = {"slug": top_slug, "count": cryptid_counts[top_slug]}

        return {
            "total_sightings": total,
            "sightings_30d": int(raw.get("sightings_30d", total)),
            "most_sighted": most_sighted,
            "most_active_county": None,
            "most_dangerous_county": None,
            "evidence_breakdown": {},
        }
    except Exception:
        logger.exception("Failed to get stats from Valkey")
        return {
            "total_sightings": 0,
            "sightings_30d": 0,
            "most_sighted": None,
            "most_active_county": None,
            "most_dangerous_county": None,
            "evidence_breakdown": {},
        }


@router.get("/stats/leaderboard")
async def get_leaderboard(valkey=Depends(get_valkey)):
    """Get top sighting reporters from Valkey sorted set."""
    if not valkey:
        return []
    try:
        # ZREVRANGE with scores — top 10 reporters
        entries = await valkey.zrevrange("leaderboard:reporters", 0, 9, withscores=True)
        return [
            {"reporter_name": name, "sighting_count": int(score)}
            for name, score in entries
        ]
    except Exception:
        logger.exception("Failed to get leaderboard from Valkey")
        return []
