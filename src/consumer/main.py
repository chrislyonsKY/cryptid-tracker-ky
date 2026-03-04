"""
Kafka consumer — reads sighting-raw, validates, persists, caches.

See ai-dev/architecture.md for the validation pipeline.
See ai-dev/patterns.md for the consumer loop pattern.

Usage:
    python -m src.consumer.main
"""

import json
import logging
import signal
import sys

import redis
from confluent_kafka import Consumer, KafkaError, Producer
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from src.api.config import settings
from src.api.models import Cryptid
from src.consumer.handlers import SightingHandlers
from src.consumer.validators import validate_sighting

logger = logging.getLogger(__name__)

# Graceful shutdown
_running = True


def _signal_handler(signum, frame):
    """Handle SIGINT/SIGTERM for graceful shutdown."""
    global _running
    logger.info("Received signal %s, shutting down...", signum)
    _running = False


def _load_known_slugs(session_factory: sessionmaker) -> set[str]:
    """Load all valid cryptid slugs from the database."""
    with session_factory() as session:
        result = session.execute(select(Cryptid.slug))
        slugs = {row[0] for row in result.all()}
        logger.info("Loaded %d known cryptid slugs: %s", len(slugs), slugs)
        return slugs


def run_consumer() -> None:
    """Main consumer loop. Reads sighting-raw, validates, persists."""
    # Synchronous PostgreSQL engine (consumer runs in its own process)
    pg_sync_uri = settings.pg_uri.replace("+asyncpg", "+psycopg2").replace("?ssl=require", "?sslmode=require")
    engine = create_engine(pg_sync_uri, echo=settings.debug)
    Session = sessionmaker(engine)

    # Load known cryptid slugs for validation
    known_slugs = _load_known_slugs(Session)

    # Valkey client (synchronous)
    valkey = redis.from_url(settings.valkey_uri, decode_responses=True)
    try:
        valkey.ping()
        logger.info("Valkey connected")
    except Exception:
        logger.exception("Failed to connect to Valkey")

    # Kafka consumer
    consumer_config = {
        "bootstrap.servers": settings.kafka_bootstrap_servers,
        "security.protocol": settings.kafka_security_protocol,
        "ssl.ca.location": settings.kafka_ssl_cafile,
        "ssl.certificate.location": settings.kafka_ssl_certfile,
        "ssl.key.location": settings.kafka_ssl_keyfile,
        "group.id": "cryptid-consumer-group",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": True,
    }
    consumer = Consumer(consumer_config)
    consumer.subscribe(["sighting-raw"])
    logger.info("Consumer subscribed to sighting-raw")

    # Kafka producer (for publishing validated/rejected)
    producer_config = {
        "bootstrap.servers": settings.kafka_bootstrap_servers,
        "security.protocol": settings.kafka_security_protocol,
        "ssl.ca.location": settings.kafka_ssl_cafile,
        "ssl.certificate.location": settings.kafka_ssl_certfile,
        "ssl.key.location": settings.kafka_ssl_keyfile,
        "client.id": "cryptid-consumer-producer",
    }
    producer = Producer(producer_config)

    # Handlers
    handlers = SightingHandlers(Session, valkey, producer)

    # Signal handlers
    signal.signal(signal.SIGINT, _signal_handler)
    if sys.platform != "win32":
        signal.signal(signal.SIGTERM, _signal_handler)

    logger.info("Consumer loop starting...")
    processed = 0
    rejected = 0

    try:
        while _running:
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
                sighting_id = sighting.get("sighting_id", "unknown")
                logger.info("Received sighting %s", sighting_id)

                # Validate
                is_valid, reason = validate_sighting(sighting, known_slugs)

                if is_valid:
                    handlers.process_sighting(sighting)
                    processed += 1
                    logger.info(
                        "Sighting %s validated and processed [total: %d]",
                        sighting_id, processed,
                    )
                else:
                    rejected += 1
                    logger.warning(
                        "Sighting %s rejected: %s [total rejected: %d]",
                        sighting_id, reason, rejected,
                    )
                    # Publish rejection
                    try:
                        rejection_msg = {
                            "sighting_id": sighting_id,
                            "reason": reason,
                            "original_message": sighting,
                        }
                        producer.produce(
                            topic="sighting-rejected",
                            key=sighting_id.encode("utf-8"),
                            value=json.dumps(rejection_msg).encode("utf-8"),
                        )
                        producer.poll(0)
                    except Exception:
                        logger.exception("Failed to publish rejection for %s", sighting_id)

            except json.JSONDecodeError:
                logger.error("Invalid JSON in message: %s", msg.key())
            except Exception:
                logger.exception("Error processing message: %s", msg.key())

    finally:
        consumer.close()
        producer.flush(timeout=5)
        valkey.close()
        engine.dispose()
        logger.info(
            "Consumer shut down. Processed: %d, Rejected: %d",
            processed, rejected,
        )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    run_consumer()
