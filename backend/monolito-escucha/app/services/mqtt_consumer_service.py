"""MQTT Consumer Service - Listen to sensor telemetry from MQTT broker."""
import json
import logging
import threading
from typing import Callable

import paho.mqtt.client as mqtt

from app.services.DTOS.telemetry_dto import TelemetryAggregateDTO

logger = logging.getLogger(__name__)


class MQTTConsumerService:
    """Service to consume telemetry messages from MQTT broker."""

    def __init__(
        self,
        broker_host: str = "localhost",
        broker_port: int = 1883,
        client_id: str = "sentinel-monolito-escucha",
        username: str | None = None,
        password: str | None = None,
    ):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.client_id = client_id
        self.username = username
        self.password = password
        self.client = None
        self.is_running = False
        self.message_handler: Callable[[TelemetryAggregateDTO], None] | None = None
        self.connection_thread: threading.Thread | None = None

    def set_message_handler(self, handler: Callable[[TelemetryAggregateDTO], None]) -> None:
        """Set the callback function to handle incoming messages."""
        self.message_handler = handler

    def _on_connect(
        self, client: mqtt.Client, userdata: dict, flags: dict, rc: int
    ) -> None:
        """Callback for when the client connects to the broker."""
        if rc == 0:
            logger.info(f"✅ Conectado a MQTT broker en {self.broker_host}:{self.broker_port}")
            client.subscribe("sentinel/v1/SB-001/#", qos=1)
            logger.info("📡 Suscrito a: sentinel/v1/SB-001/#")
        else:
            logger.error(f"❌ Error conectando a MQTT broker: código {rc}")

    def _on_message(self, client: mqtt.Client, userdata: dict, msg: mqtt.MQTTMessage) -> None:
        """Callback for when a message is received."""
        try:
            topic = msg.topic
            payload = msg.payload.decode("utf-8")

            logger.debug(f"📨 Mensaje recibido en: {topic}")

            # Parse JSON payload
            try:
                data = json.loads(payload)
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️  No se pudo parsear JSON en {topic}: {e}")
                return

            # Only process telemetry_aggregate messages
            if data.get("message_type") != "telemetry_aggregate":
                logger.debug(f"⏭️  Ignorando mensaje de tipo: {data.get('message_type')}")
                return

            # Convert to DTO
            try:
                telemetry = TelemetryAggregateDTO(**data)
            except Exception as e:
                logger.warning(f"⚠️  Error al convertir a DTO: {e}")
                return

            # Call handler if set
            if self.message_handler:
                try:
                    # Run handler in a separate thread to avoid blocking MQTT thread
                    handler_thread = threading.Thread(
                        target=self._run_handler, args=(telemetry,), daemon=True
                    )
                    handler_thread.start()
                except Exception as e:
                    logger.error(f"❌ Error ejecutando handler: {e}")

        except Exception as e:
            logger.error(f"❌ Error procesando mensaje MQTT: {e}")

    def _run_handler(self, telemetry: TelemetryAggregateDTO) -> None:
        """Run the message handler in a separate thread."""
        try:
            if self.message_handler:
                self.message_handler(telemetry)
                logger.debug(
                    f"✅ Mensaje procesado: {telemetry.message_uid} "
                    f"({len(telemetry.bridges)} bridges)"
                )
        except Exception as e:
            logger.error(f"❌ Error en handler: {e}")

    def _on_disconnect(
        self, client: mqtt.Client, userdata: dict, rc: int
    ) -> None:
        """Callback for when the client disconnects from the broker."""
        if rc != 0:
            logger.warning(f"⚠️  Desconexión inesperada de MQTT: código {rc}")
        else:
            logger.info("🔌 Desconectado de MQTT broker")

    def _on_subscribe(
        self, client: mqtt.Client, userdata: dict, mid: int, granted_qos: tuple
    ) -> None:
        """Callback for when subscription is confirmed."""
        logger.info(f"✅ Suscripción confirmada con QoS: {granted_qos}")

    def _on_log(self, client: mqtt.Client, userdata: dict, level: int, buf: str) -> None:
        """Callback for MQTT library logs."""
        if level <= mqtt.MQTT_LOG_WARNING:
            logger.debug(f"MQTT: {buf}")

    def start(self) -> None:
        """Start the MQTT consumer service."""
        if self.is_running:
            logger.warning("⚠️  El servicio MQTT ya está en ejecución")
            return

        try:
            self.client = mqtt.Client(client_id=self.client_id)
            self.client.on_connect = self._on_connect
            self.client.on_message = self._on_message
            self.client.on_disconnect = self._on_disconnect
            self.client.on_subscribe = self._on_subscribe
            self.client.on_log = self._on_log

            if self.username and self.password:
                self.client.username_pw_set(self.username, self.password)

            logger.info(f"🔌 Conectando a MQTT broker en {self.broker_host}:{self.broker_port}...")
            self.client.connect(self.broker_host, self.broker_port, keepalive=60)

            # Start the MQTT network loop in a background thread
            self.connection_thread = threading.Thread(
                target=self.client.loop_forever, daemon=True
            )
            self.connection_thread.start()

            self.is_running = True
            logger.info("✅ Servicio MQTT Consumer iniciado")

        except Exception as e:
            logger.error(f"❌ Error iniciando MQTT Consumer: {e}")
            self.is_running = False

    def stop(self) -> None:
        """Stop the MQTT consumer service."""
        if not self.is_running:
            return

        try:
            if self.client:
                self.client.disconnect()
                self.client.loop_stop()
            self.is_running = False
            logger.info("✅ Servicio MQTT Consumer detenido")
        except Exception as e:
            logger.error(f"❌ Error deteniendo MQTT Consumer: {e}")
