"""Auth schemas - Credenciales que el broker MQTT envía al plugin de autenticación."""
from pydantic import BaseModel, Field


class MqttAuthRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=512)
