import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import crear_app


@pytest.fixture
def ajustes(tmp_path):
    """Configuración aislada: base en tmp, sin REST, sin MQTT y LoRa sin pérdida ni espera."""
    return Settings(
        data_dir=tmp_path,
        api_url=None,
        node_tokens=None,
        mqtt_host=None,
        lora_loss_rate=0.0,
        lora_min_delay_ms=0,
        lora_max_delay_ms=0,
        lora_seed=1,
    )


@pytest.fixture
def cliente(ajustes):
    with TestClient(crear_app(ajustes)) as c:
        yield c
