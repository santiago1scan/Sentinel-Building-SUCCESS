"""Configuración del bridge desde variables de entorno (prefijo SENTINEL_).

Los nombres de las variables coinciden con los que usaba bridge_service.py.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SENTINEL_", extra="ignore")

    data_dir: Path = Path("data_bridge")
    building_code: str = "SB-001"
    interval: float = 30.0
    catalogo_json: str | None = None

    api_url: str | None = None
    api_path: str = "/telemetry/aggregate"
    api_timeout: float = 10.0

    node_tokens: str | None = None

    mqtt_host: str | None = None
    mqtt_port: int = 1883
    mqtt_tls: bool = False
    mqtt_ca_file: str | None = None

    lora_loss_rate: float = 0.0
    lora_min_delay_ms: int = 100
    lora_max_delay_ms: int = 400
    lora_max_payload_bytes: int = 1200
    lora_seed: int | None = None

    # Firebase Authentication para la página de login. La API key y demás valores son
    # identificadores públicos del proyecto; la seguridad la aplica la verificación del token.
    firebase_api_key: str = ""
    firebase_auth_domain: str = ""
    firebase_project_id: str = ""
    firebase_app_id: str = ""
    firebase_messaging_sender_id: str = ""
    firebase_storage_bucket: str = ""
    firebase_admin_emails: str = ""


def parse_node_tokens(spec: str | None) -> dict[str, str]:
    """Parsea 'NODE-FLOOR-1=token1,NODE-FLOOR-2=token2'. Nunca muestra los tokens."""
    tokens: dict[str, str] = {}
    if not spec:
        return tokens
    for item in spec.split(","):
        item = item.strip()
        if not item:
            continue
        nodo, sep, token = item.partition("=")
        nodo, token = nodo.strip(), token.strip()
        if not sep or not nodo or not token:
            raise ValueError(f"Token de nodo mal formado para '{nodo or '?'}'")
        tokens[nodo] = token
    return tokens


@lru_cache
def get_settings() -> Settings:
    return Settings()
