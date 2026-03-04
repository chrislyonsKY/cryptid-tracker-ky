"""
Shared FastAPI dependencies for route handlers.
Avoids circular imports by accessing app.state at request time.
"""

import logging

import redis.asyncio as aioredis
from confluent_kafka import Producer
from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)


def get_kafka_producer(request: Request) -> Producer:
    """Get the shared Kafka producer from app state."""
    producer = getattr(request.app.state, "kafka_producer", None)
    if producer is None:
        logger.error("Kafka producer not available — was not initialized at startup")
        raise HTTPException(status_code=503, detail="Sighting submission temporarily unavailable")
    return producer


def get_valkey(request: Request) -> aioredis.Redis | None:
    """Get the shared Valkey client from app state. Returns None if unavailable."""
    return getattr(request.app.state, "valkey_client", None)
