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

    # Broker MQTT (plugin dynamic-security). El backend usa la cuenta de administración
    # para crear y deshabilitar clientes de nodo. Sin estas variables, las operaciones de
    # nodo que tocan el broker responden 503.
    mqtt_host: str = "mosquitto"
    mqtt_port: int = 1883
    mqtt_admin_username: str | None = None
    mqtt_admin_password: str | None = None
    building_code: str = "SB-001"


settings = Settings()
