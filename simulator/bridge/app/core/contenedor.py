"""Ensambla las capas: base de datos, repositorios, canales y servicios."""

from dataclasses import dataclass

from app.core.config import Settings, parse_node_tokens
from app.datos.canales.consulta_client import ConsultaClient
from app.datos.canales.lora_virtual import LoraCanal
from app.datos.canales.mqtt_nodos import EnlaceMqttNodo, topico_nodo
from app.datos.canales.rest_client import RestClient
from app.datos.db import Database
from app.datos.repositorios.bitacora_repo import BitacoraRepo
from app.datos.repositorios.graficas_repo import GraficasRepo
from app.datos.repositorios.lecturas_repo import LecturasRepo
from app.datos.repositorios.outbox_repo import OutboxRepo
from app.datos.repositorios.registro_repo import RegistroRepo
from app.negocio.catalogo import cargar_catalogo
from app.negocio.entrega import Entregador
from app.negocio.graficas import ServicioGraficas
from app.negocio.ingesta import ServicioIngesta
from app.negocio.registro_nodo import ServicioRegistro


@dataclass
class Contenedor:
    db: Database
    ingesta: ServicioIngesta
    enlaces: dict[str, EnlaceMqttNodo]
    graficas: ServicioGraficas
    registro: ServicioRegistro

    def cerrar(self) -> None:
        for enlace in list(self.enlaces.values()):
            enlace.cerrar()
        self.db.close()


def _crear_enlace(ajustes: Settings, nodo: str, token: str) -> EnlaceMqttNodo:
    return EnlaceMqttNodo(
        nodo=nodo, token=token,
        topico=topico_nodo(ajustes.building_code, nodo),
        host=ajustes.mqtt_host, port=ajustes.mqtt_port,
        tls=ajustes.mqtt_tls, ca_file=ajustes.mqtt_ca_file,
    )


def crear_contenedor(ajustes: Settings) -> Contenedor:
    db = Database(ajustes.data_dir / "bridge_local.db")
    bitacora = BitacoraRepo(db)
    outbox = OutboxRepo(db)
    registro_repo = RegistroRepo(db)
    tokens = parse_node_tokens(ajustes.node_tokens)
    # La credencial obtenida por el registro manda sobre la que venga del entorno.
    tokens.update(registro_repo.credenciales())
    catalogo = cargar_catalogo(ajustes.catalogo_json)

    enlaces: dict[str, EnlaceMqttNodo] = {}
    if not ajustes.mqtt_host:
        bitacora.log("WARN", "MQTT deshabilitado: falta SENTINEL_MQTT_HOST")
    else:
        for nodo, token in tokens.items():
            enlaces[nodo] = _crear_enlace(ajustes, nodo, token)
        bitacora.log("INFO", f"MQTT por nodo configurado: {', '.join(sorted(enlaces))}")

    def aplicar_credencial(codigo: str, token: str) -> None:
        """Usa el token recién obtenido en REST y MQTT sin reiniciar el bridge."""
        tokens[codigo] = token  # el Entregador lee este mismo diccionario
        if ajustes.mqtt_host:
            nuevo = _crear_enlace(ajustes, codigo, token)
            anterior = enlaces.get(codigo)
            enlaces[codigo] = nuevo
            if anterior is not None:
                anterior.cerrar()
            bitacora.log("INFO", f"MQTT del nodo {codigo} reconfigurado con la nueva credencial")

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
    nodo = ajustes.node_code or (sorted(tokens)[0] if tokens else sorted(catalogo)[0])
    graficas = ServicioGraficas(GraficasRepo(db), nodo)
    registro = ServicioRegistro(
        repo=registro_repo,
        consulta=ConsultaClient(ajustes.consulta_url, ajustes.consulta_timeout),
        bitacora=bitacora,
        codigo_nodo=nodo,
        aplicar_credencial=aplicar_credencial,
        tiene_token=lambda codigo: codigo in tokens,
    )
    return Contenedor(db=db, ingesta=ingesta, enlaces=enlaces, graficas=graficas, registro=registro)
