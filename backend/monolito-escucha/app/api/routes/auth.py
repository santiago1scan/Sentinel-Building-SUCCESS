"""Auth routes - Endpoint interno que consulta el plugin de autenticación de Mosquitto.

Solo debe ser alcanzable desde la red interna de Docker, nunca desde el exterior.
"""
from fastapi import APIRouter, Depends

from app.api.deps import get_node_auth_service
from app.schemas.auth import MqttAuthRequest
from app.services.node_auth_service import NodeAuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/node", status_code=200)
async def authenticate_mqtt_node(
    credentials: MqttAuthRequest,
    service: NodeAuthService = Depends(get_node_auth_service),
):
    """
    Permite o rechaza una conexión MQTT de nodo.

    - **200**: el usuario es el código de un nodo activo y la contraseña es su token
    - **401**: token desconocido, revocado o usuario que no corresponde al token
    """
    await service.authenticate_mqtt(credentials.username, credentials.password)
    return {"allowed": True}
