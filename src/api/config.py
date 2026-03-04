"""
Application configuration via environment variables.

All Aiven service URIs are loaded from AIVEN_* environment variables.
See .env.example for the expected variable names.
"""

import base64
import logging
import os
import tempfile
from pathlib import Path

from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


def write_kafka_cert(env_var: str, filename: str) -> str:
    """Decode a base64 Kafka cert from env var and write it to a temp file."""
    b64_data = os.environ.get(env_var)
    if not b64_data:
        return ""

    target_path = Path(tempfile.gettempdir()) / filename
    try:
        target_path.write_bytes(base64.b64decode(b64_data))
        return str(target_path)
    except Exception:
        logger.exception("Failed to decode/write Kafka cert from env var %s", env_var)
        return ""


def _resolve_kafka_cert_path(path_env_var: str, b64_env_var: str, default_path: str, temp_filename: str) -> str:
    """Resolve Kafka cert path from explicit path env, then base64 env, then default."""
    explicit_path = os.environ.get(path_env_var)
    if explicit_path:
        return explicit_path

    decoded_path = write_kafka_cert(b64_env_var, temp_filename)
    if decoded_path:
        return decoded_path

    return default_path


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # PostgreSQL + PostGIS
    pg_uri: str

    # Kafka
    kafka_bootstrap_servers: str
    kafka_security_protocol: str = "SSL"
    kafka_ssl_cafile: str = "certs/ca.pem"
    kafka_ssl_certfile: str = "certs/service.cert"
    kafka_ssl_keyfile: str = "certs/service.key"

    # Valkey
    valkey_uri: str

    # MySQL
    mysql_uri: str

    # App
    app_name: str = "Cryptid Tracker KY"
    debug: bool = False

    class Config:
        env_prefix = "AIVEN_"
        env_file = ".env"

    def model_post_init(self, __context) -> None:
        """Finalize derived settings after env loading."""
        self.kafka_ssl_cafile = _resolve_kafka_cert_path(
            "AIVEN_KAFKA_SSL_CAFILE",
            "KAFKA_SSL_CA_BASE64",
            self.kafka_ssl_cafile,
            "kafka-ca.pem",
        )
        self.kafka_ssl_certfile = _resolve_kafka_cert_path(
            "AIVEN_KAFKA_SSL_CERTFILE",
            "KAFKA_SSL_CERT_BASE64",
            self.kafka_ssl_certfile,
            "kafka-service.cert",
        )
        self.kafka_ssl_keyfile = _resolve_kafka_cert_path(
            "AIVEN_KAFKA_SSL_KEYFILE",
            "KAFKA_SSL_KEY_BASE64",
            self.kafka_ssl_keyfile,
            "kafka-service.key",
        )


settings = Settings()
