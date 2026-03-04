"""
Valkey (Redis) cache operations for live stats, threat levels, and recent sightings.

See ai-dev/architecture.md for key design and TTL policy.
"""

import json
import logging
from typing import Any

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


class StatsCache:
    """Valkey-backed cache for live stats and threat levels."""

    def __init__(self, client: aioredis.Redis):
        self._r = client

    async def update_on_new_sighting(self, sighting: dict) -> None:
        """Update all caches when a new sighting is validated."""
        pipe = self._r.pipeline()
        try:
            # Global stats
            pipe.hincrby("stats:global", "total_sightings", 1)
            pipe.hincrby("stats:global", f"{sighting['cryptid_slug']}_count", 1)

            # Recent sightings list (capped at 50)
            pipe.lpush("recent:sightings", json.dumps(sighting))
            pipe.ltrim("recent:sightings", 0, 49)

            # Reporter leaderboard
            pipe.zincrby("leaderboard:reporters", 1, sighting["reporter_name"])

            await pipe.execute()
            logger.debug("Updated caches for sighting %s", sighting.get("sighting_id"))
        except Exception:
            logger.exception(
                "Failed to update caches for sighting %s",
                sighting.get("sighting_id"),
            )

    async def set_threat_level(
        self, fips: str, threat_data: dict[str, Any], ttl: int = 300
    ) -> None:
        """Set county threat level with TTL."""
        try:
            key = f"threat:{fips}"
            await self._r.hset(key, mapping=threat_data)
            await self._r.expire(key, ttl)
        except Exception:
            logger.exception("Failed to set threat level for county %s", fips)

    async def get_recent_sightings(self, count: int = 50) -> list[dict]:
        """Get the most recent sightings from cache."""
        try:
            raw = await self._r.lrange("recent:sightings", 0, count - 1)
            return [json.loads(item) for item in raw]
        except Exception:
            logger.exception("Failed to get recent sightings")
            return []

    async def get_stats(self) -> dict[str, Any]:
        """Get global statistics hash."""
        try:
            return await self._r.hgetall("stats:global") or {}
        except Exception:
            logger.exception("Failed to get stats")
            return {}

    async def get_leaderboard(self, count: int = 10) -> list[tuple[str, float]]:
        """Get top reporters sorted set."""
        try:
            return await self._r.zrevrange(
                "leaderboard:reporters", 0, count - 1, withscores=True
            )
        except Exception:
            logger.exception("Failed to get leaderboard")
            return []
