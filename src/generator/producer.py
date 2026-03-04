"""
Kafka producer wrapper for the sighting generator.

Handles SSL configuration and delivery callbacks.
"""

import json
import logging

from confluent_kafka import Producer

from src.api.config import settings

logger = logging.getLogger(__name__)


def create_producer() -> Producer:
    """Create a configured Kafka producer for sighting generation."""
    config = {
        "bootstrap.servers": settings.kafka_bootstrap_servers,
        "security.protocol": settings.kafka_security_protocol,
        "ssl.ca.location": settings.kafka_ssl_cafile,
        "ssl.certificate.location": settings.kafka_ssl_certfile,
        "ssl.key.location": settings.kafka_ssl_keyfile,
        "client.id": "cryptid-generator",
    }
    return Producer(config)


def _delivery_callback(err, msg):
    """Log Kafka delivery results."""
    if err:
        logger.error("Delivery failed for %s: %s", msg.key(), err)
    else:
        logger.debug("Delivered %s to %s [%d]", msg.key(), msg.topic(), msg.partition())


def produce_sighting(producer: Producer, sighting: dict) -> None:
    """Publish a sighting to the sighting-raw topic."""
    try:
        producer.produce(
            topic="sighting-raw",
            key=sighting["sighting_id"].encode("utf-8"),
            value=json.dumps(sighting).encode("utf-8"),
            callback=_delivery_callback,
        )
        producer.poll(0)
    except Exception:
        logger.exception("Failed to produce sighting %s", sighting.get("sighting_id"))
        raise
