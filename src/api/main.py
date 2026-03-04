"""
Cryptid Tracker KY — FastAPI application entry point.

Serves the REST API and static frontend files.
"""

import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path

import redis.asyncio as aioredis
from confluent_kafka import Producer
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from src.api.config import settings
from src.api.models.database import pg_engine, mysql_engine
from src.api.models.schemas import HealthResponse
from src.api.routes import counties, cryptids, sightings, stats, community

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown of shared resources."""

    # --- Startup ---
    logger.info("Starting Cryptid Tracker KY...")

    # Kafka producer
    try:
        kafka_config = {
            "bootstrap.servers": settings.kafka_bootstrap_servers,
            "security.protocol": settings.kafka_security_protocol,
            "ssl.ca.location": settings.kafka_ssl_cafile,
            "ssl.certificate.location": settings.kafka_ssl_certfile,
            "ssl.key.location": settings.kafka_ssl_keyfile,
            "client.id": "cryptid-tracker-api",
        }
        app.state.kafka_producer = Producer(kafka_config)
        logger.info("Kafka producer initialized")
    except Exception:
        logger.exception("Failed to initialize Kafka producer")
        app.state.kafka_producer = None

    # Valkey client
    try:
        app.state.valkey_client = aioredis.from_url(
            settings.valkey_uri,
            decode_responses=True,
            socket_connect_timeout=5,
        )
        await app.state.valkey_client.ping()
        logger.info("Valkey client connected")
    except Exception:
        logger.exception("Failed to connect to Valkey")
        app.state.valkey_client = None

    yield

    # --- Shutdown ---
    logger.info("Shutting down Cryptid Tracker KY...")

    if getattr(app.state, "kafka_producer", None):
        app.state.kafka_producer.flush(timeout=5)
        logger.info("Kafka producer flushed")

    if getattr(app.state, "valkey_client", None):
        await app.state.valkey_client.close()
        logger.info("Valkey client closed")

    await pg_engine.dispose()
    if mysql_engine:
        await mysql_engine.dispose()
    logger.info("Database engines disposed")


# --- App factory ---

app = FastAPI(
    title="Cryptid Tracker KY",
    description="Real-time Kentucky cryptid sighting tracker",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — wide open for demo purposes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routes ---
app.include_router(sightings.router, prefix="/api")
app.include_router(cryptids.router, prefix="/api")
app.include_router(stats.router, prefix="/api")
app.include_router(counties.router, prefix="/api")
app.include_router(community.router, prefix="/api")

# --- Static frontend ---
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@app.get("/", response_class=FileResponse, include_in_schema=False)
async def serve_index():
    """Serve the frontend index.html at the root URL."""
    return FileResponse(str(FRONTEND_DIR / "index.html"))


if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/api/health", response_model=HealthResponse, tags=["system"])
async def health_check():
    """Check connectivity to all backend services."""
    service_status = {}

    # PostgreSQL
    try:
        async with pg_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        service_status["postgresql"] = "ok"
    except Exception:
        service_status["postgresql"] = "error"

    # Valkey
    try:
        vc = getattr(app.state, "valkey_client", None)
        if vc:
            await vc.ping()
            service_status["valkey"] = "ok"
        else:
            service_status["valkey"] = "not_initialized"
    except Exception:
        service_status["valkey"] = "error"

    # Kafka (basic check — producer exists)
    service_status["kafka"] = "ok" if getattr(app.state, "kafka_producer", None) else "not_initialized"

    # MySQL
    try:
        if mysql_engine:
            async with mysql_engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            service_status["mysql"] = "ok"
        else:
            service_status["mysql"] = "not_configured"
    except Exception:
        service_status["mysql"] = "error"

    overall = "ok" if all(v == "ok" for v in service_status.values()) else "degraded"
    return HealthResponse(status=overall, services=service_status)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
