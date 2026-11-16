"""Application configuration using Pydantic Settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str
    app_env: str = "development"

    # Cuenta del consumidor MQTT en el broker (permiso de solo lectura sobre telemetría).
    mqtt_host: str = "mosquitto"
    mqtt_port: int = 1883
    mqtt_username: str | None = None
    mqtt_password: str | None = None
    # TLS: el broker del repositorio solo escucha en 8883. mqtt_ca_file es la CA que firmó su certificado.
    mqtt_tls: bool = False
    mqtt_ca_file: str | None = None

    # A node with no message for longer than this gets a NODE_SILENT technical alert.
    # The bridge sends a summary every 30 min, so 35 min = one missed summary plus margin.
    silence_threshold_minutes: int = 35
    silence_check_seconds: int = 300


settings = Settings()
