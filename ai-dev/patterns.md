# Patterns — Cryptid Tracker KY

## Code Patterns

### FastAPI Route with PostGIS Spatial Query

```python
@router.get("/sightings", response_model=GeoJSONFeatureCollection)
async def get_sightings(
    bbox: str | None = Query(None, description="minLon,minLat,maxLon,maxLat"),
    cryptid: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve sightings as GeoJSON FeatureCollection with optional spatial filter."""
    query = select(Sighting).join(Cryptid)

    if bbox:
        try:
            min_lon, min_lat, max_lon, max_lat = [float(v) for v in bbox.split(",")]
            bbox_wkt = f"POLYGON(({min_lon} {min_lat}, {max_lon} {min_lat}, {max_lon} {max_lat}, {min_lon} {max_lat}, {min_lon} {min_lat}))"
            query = query.where(
                func.ST_Intersects(
                    Sighting.geom,
                    func.ST_GeomFromText(bbox_wkt, 4326)
                )
            )
        except ValueError:
            raise HTTPException(400, "Invalid bbox format")

    if cryptid:
        query = query.where(Cryptid.slug == cryptid)

    query = query.order_by(Sighting.sighting_date.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    sightings = result.scalars().all()

    return to_geojson_collection(sightings)
```

### Kafka Producer Pattern

```python
import json
import logging
from confluent_kafka import Producer

logger = logging.getLogger(__name__)

class SightingProducer:
    """Publishes sighting events to Kafka."""

    def __init__(self, config: dict):
        self._producer = Producer(config)

    def produce_sighting(self, sighting: dict) -> None:
        """Publish a sighting to the sighting-raw topic."""
        try:
            self._producer.produce(
                topic="sighting-raw",
                key=sighting["sighting_id"],
                value=json.dumps(sighting).encode("utf-8"),
                callback=self._delivery_callback,
            )
            self._producer.poll(0)  # Trigger callbacks
        except Exception:
            logger.exception("Failed to produce sighting %s", sighting.get("sighting_id"))
            raise

    def flush(self, timeout: float = 10.0) -> None:
        """Flush pending messages."""
        remaining = self._producer.flush(timeout)
        if remaining > 0:
            logger.warning("%d messages still in queue after flush", remaining)

    @staticmethod
    def _delivery_callback(err, msg):
        if err:
            logger.error("Delivery failed for %s: %s", msg.key(), err)
        else:
            logger.debug("Delivered %s to %s [%d]", msg.key(), msg.topic(), msg.partition())
```

### Kafka Consumer Pattern

```python
import json
import logging
from confluent_kafka import Consumer, KafkaError

logger = logging.getLogger(__name__)

def run_consumer(config: dict, handlers: SightingHandlers):
    """Main consumer loop. Reads sighting-raw, validates, persists."""
    consumer = Consumer(config)
    consumer.subscribe(["sighting-raw"])
    logger.info("Consumer started, subscribed to sighting-raw")

    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                logger.error("Consumer error: %s", msg.error())
                continue

            try:
                sighting = json.loads(msg.value().decode("utf-8"))
                logger.info("Processing sighting %s", sighting.get("sighting_id"))
                handlers.process_sighting(sighting)
            except json.JSONDecodeError:
                logger.error("Invalid JSON in message: %s", msg.key())
            except Exception:
                logger.exception("Error processing sighting %s", msg.key())
    finally:
        consumer.close()
        logger.info("Consumer shut down")
```

### Valkey Cache Pattern

```python
import json
import logging
import redis

logger = logging.getLogger(__name__)

class StatsCache:
    """Valkey-backed cache for live stats and threat levels."""

    def __init__(self, url: str):
        self._r = redis.from_url(url, decode_responses=True)

    def update_on_new_sighting(self, sighting: dict) -> None:
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

            pipe.execute()
        except Exception:
            logger.exception("Failed to update caches for sighting %s", sighting.get("sighting_id"))

    def set_threat_level(self, fips: str, threat_data: dict, ttl: int = 300) -> None:
        """Set county threat level with TTL."""
        try:
            key = f"threat:{fips}"
            self._r.hset(key, mapping=threat_data)
            self._r.expire(key, ttl)
        except Exception:
            logger.exception("Failed to set threat level for county %s", fips)

    def get_recent_sightings(self, count: int = 50) -> list[dict]:
        """Get the most recent sightings from cache."""
        try:
            raw = self._r.lrange("recent:sightings", 0, count - 1)
            return [json.loads(item) for item in raw]
        except Exception:
            logger.exception("Failed to get recent sightings")
            return []
```

### GeoJSON Serialization Pattern

```python
def sighting_to_geojson_feature(sighting) -> dict:
    """Convert a SQLAlchemy Sighting model to a GeoJSON Feature."""
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [
                sighting.longitude,  # GeoJSON is [lon, lat]
                sighting.latitude,
            ],
        },
        "properties": {
            "id": str(sighting.id),
            "cryptid_slug": sighting.cryptid.slug,
            "cryptid_name": sighting.cryptid.name,
            "cryptid_color": sighting.cryptid.color,
            "reporter_name": sighting.reporter_name,
            "description": sighting.description,
            "evidence_level": sighting.evidence_level,
            "evidence_label": EVIDENCE_LABELS.get(sighting.evidence_level, "unknown"),
            "sighting_date": sighting.sighting_date.isoformat(),
            "county_name": sighting.county_name,
            "source": sighting.source,
        },
    }
```

---

## Anti-Patterns

### ❌ Spatial query without index

```python
# WRONG — full table scan
query = text("SELECT * FROM sightings WHERE ST_Distance(geom, ST_MakePoint(:lon, :lat)) < 1000")
```

```python
# ✅ CORRECT — uses GiST index via ST_DWithin
query = text("""
    SELECT * FROM sightings
    WHERE ST_DWithin(geom::geography, ST_MakePoint(:lon, :lat)::geography, 1000)
""")
```

### ❌ GeoJSON coordinate order confusion

```python
# WRONG — GeoJSON is [longitude, latitude] not [lat, lon]
coordinates = [sighting.latitude, sighting.longitude]

# ✅ CORRECT
coordinates = [sighting.longitude, sighting.latitude]
```

### ❌ Unbounded Valkey cache

```python
# WRONG — list grows forever
r.lpush("recent:sightings", data)

# ✅ CORRECT — cap the list
pipe = r.pipeline()
pipe.lpush("recent:sightings", data)
pipe.ltrim("recent:sightings", 0, 49)
pipe.execute()
```

### ❌ Blocking Kafka produce in API request

```python
# WRONG — blocks the async request handler
producer.produce(topic, value=data)
producer.flush()  # Blocks until delivered

# ✅ CORRECT — fire and forget with periodic flush
producer.produce(topic, value=data, callback=delivery_cb)
producer.poll(0)  # Non-blocking callback trigger
# Flush in a background task or lifespan shutdown
```

### ❌ Hardcoded connection strings

```python
# WRONG
engine = create_async_engine("postgresql+asyncpg://user:pass@host:port/db")

# ✅ CORRECT
from .config import settings
engine = create_async_engine(settings.pg_uri)
```
