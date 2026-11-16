"""Ensambla las capas: base de datos, repositorios, canales y servicios."""

from dataclasses import dataclass

from app.core.config import Settings, parse_node_tokens
from app.datos.canales.lora_virtual import LoraCanal
from app.datos.canales.mqtt_nodos import EnlaceMqttNodo, topico_nodo
from app.datos.canales.rest_client import RestClient
from app.datos.db import Database
from app.datos.repositorios.bitacora_repo import BitacoraRepo
from app.datos.repositorios.lecturas_repo import LecturasRepo
from app.datos.repositorios.outbox_repo import OutboxRepo
from app.negocio.catalogo import cargar_catalogo
from app.negocio.entrega import Entregador
from app.negocio.ingesta import ServicioIngesta


@dataclass
class Contenedor:
    db: Database
    ingesta: ServicioIngesta
    enlaces: dict[str, EnlaceMqttNodo]

    def cerrar(self) -> None:
        for enlace in self.enlaces.values():
            enlace.cerrar()
        self.db.close()


def crear_contenedor(ajustes: Settings) -> Contenedor:
    db = Database(ajustes.data_dir / "bridge_local.db")
    bitacora = BitacoraRepo(db)
    outbox = OutboxRepo(db)
    tokens = parse_node_tokens(ajustes.node_tokens)
    catalogo = cargar_catalogo(ajustes.catalogo_json)

    enlaces: dict[str, EnlaceMqttNodo] = {}
    if not ajustes.mqtt_host:
        bitacora.log("WARN", "MQTT deshabilitado: falta SENTINEL_MQTT_HOST")
    else:
        for nodo, token in tokens.items():
            enlaces[nodo] = EnlaceMqttNodo(
                nodo=nodo, token=token,
                topico=topico_nodo(ajustes.building_code, nodo),
                host=ajustes.mqtt_host, port=ajustes.mqtt_port,
                tls=ajustes.mqtt_tls, ca_file=ajustes.mqtt_ca_file,
            )
        bitacora.log("INFO", f"MQTT por nodo configurado: {', '.join(sorted(enlaces))}")

    entregador = Entregador(
        outbox=outbox,
        bitacora=bitacora,
        rest=RestClient(ajustes.api_url, ajustes.api_path, ajustes.api_timeout),
        enlaces=enlaces,
        tokens=tokens,
        lora=LoraCanal(
            loss_rate=ajustes.lora_loss_rate,
            min_delay_ms=ajustes.lora_min_delay_ms,
            max_delay_ms=ajustes.lora_max_delay_ms,
            max_payload_bytes=ajustes.lora_max_payload_bytes,
            seed=ajustes.lora_seed,
        ),
    )
    ingesta = ServicioIngesta(
        lecturas=LecturasRepo(db),
        outbox=outbox,
        bitacora=bitacora,
        entregador=entregador,
        catalogo=catalogo,
        codigo_edificio=ajustes.building_code,
        intervalo_s=ajustes.interval,
    )
    return Contenedor(db=db, ingesta=ingesta, enlaces=enlaces)
