"""
Shared FastAPI dependencies for route handlers.
Avoids circular imports by accessing app.state at request time.
"""

import redis.asyncio as aioredis
from confluent_kafka import Producer
from fastapi import Request


def get_kafka_producer(request: Request) -> Producer:
    """Get the shared Kafka producer from app state."""
    producer = getattr(request.app.state, "kafka_producer", None)
    if producer is None:
        raise RuntimeError("Kafka producer not initialized")
    return producer


def get_valkey(request: Request) -> aioredis.Redis:
    """Get the shared Valkey client from app state."""
    client = getattr(request.app.state, "valkey_client", None)
    if client is None:
        raise RuntimeError("Valkey client not initialized")
    return client
