"""
Application configuration via environment variables.

All Aiven service URIs are loaded from AIVEN_* environment variables.
See .env.example for the expected variable names.
"""

from pydantic_settings import BaseSettings


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


settings = Settings()
