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
    # TLS: el broker del repositorio solo escucha en 8883. mqtt_ca_file es la CA que firmó su certificado.
    mqtt_tls: bool = False
    mqtt_ca_file: str | None = None
    building_code: str = "SB-001"

    # Tiempo que una solicitud de registro de nodo espera aprobación (y una aprobación espera
    # a que el bridge recoja el token). Las solicitudes viven en memoria: un solo proceso.
    registration_ttl_seconds: int = 300

    # Autenticación del panel: el frontend inicia sesión con Firebase y envía el ID token en
    # `Authorization: Bearer`. Se verifica contra el id del proyecto (no hace falta la API key).
    # Sin FIREBASE_PROJECT_ID las rutas protegidas responden 503: no quedan abiertas por omisión.
    firebase_project_id: str | None = None
    # Correos autorizados, separados por coma. Vacío = cualquier usuario autenticado por Firebase.
    firebase_admin_emails: str = ""

    # Orígenes del frontend que pueden llamar a la API (separados por coma).
    # Por defecto abierto ("*"). En producción conviene limitarlo: CORS_ORIGINS=https://panel.ejemplo.com
    cors_origins: str = "*"


settings = Settings()
