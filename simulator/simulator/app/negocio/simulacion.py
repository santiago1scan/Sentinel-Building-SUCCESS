"""Controlador de la simulación: ciclo de envío, escenarios y fallos.

Reemplaza al proceso con comandos por stdin del simulador original: las anomalías
y los fallos son estado en memoria que el ciclo consulta en cada vuelta. Lo único
que sale al exterior es el POST de lecturas al bridge.
"""

import random
import threading
import time
from collections import deque
from typing import Any

from app.core.tiempo import utc_ahora
from app.datos.cliente_bridge import ClienteBridge, ClienteBridgeError
from app.negocio.escenarios.definiciones import ESCENARIOS, nodos_por_defecto
from app.negocio.generacion.sobres import eventos_nodo
from app.negocio.sensores import resolver_sensor


def _metricas_bridge(salud: dict[str, Any] | None) -> dict[str, Any]:
    """Traduce el /health del bridge a las métricas que muestra el panel."""
    vacio = {
        "ready": False,
        "message": "Bridge not reachable",
        "raw_readings": 0,
        "aggregates_total": 0,
        "sent_rest": 0,
        "pending": 0,
        "last_priority": None,
        "last_message_uid": None,
    }
    if salud is None:
        return vacio
    almacenamiento = salud.get("storage", {})
    pendientes = int(almacenamiento.get("pending", 0))
    enviados = int(almacenamiento.get("sent", 0))
    return {
        **vacio,
        "ready": True,
        "message": "Bridge available",
        "raw_readings": int(almacenamiento.get("raw_readings", 0)),
        "aggregates_total": pendientes + enviados,
        # El bridge cuenta como enviado todo lo que ya no está pendiente (REST o MQTT).
        "sent_rest": enviados,
        "pending": pendientes,
    }


class ControladorSimulacion:
    def __init__(self, *, nodos: list[str], intervalo_s: float, cliente: ClienteBridge,
                 semilla: int | None = None) -> None:
        self.nodos = list(nodos)
        self.intervalo_s = intervalo_s
        self.cliente = cliente
        self._rng = random.Random(semilla)
        self._candado = threading.RLock()
        self._hilo: threading.Thread | None = None
        self._parar = threading.Event()
        self._despertar = threading.Event()
        self._ejecutando = False
        self._anomalias: dict[str, set[str]] = {nodo: set() for nodo in self.nodos}
        self._silenciados: set[tuple[str, str]] = set()
        self._apagados: set[str] = set()
        self._escenario: dict[str, Any] | None = None
        self._token_escenario = 0
        self._salida: deque[str] = deque(maxlen=100)
        self._eventos: deque[dict[str, str]] = deque(maxlen=200)
        self._ultima_salida: str | None = None

    # ------------------------------------------------------------------ registro

    def _evento(self, accion: str, detalle: str) -> None:
        self._eventos.append({"timestamp": utc_ahora(), "action": accion, "detail": detalle})

    def _linea(self, texto: str) -> None:
        with self._candado:
            self._salida.append(f"[{utc_ahora()}] {texto}")

    # ------------------------------------------------------------------ validación

    def normalizar_nodos(self, valor: Any) -> list[str]:
        if not isinstance(valor, list):
            raise ValueError("'nodes' debe ser una lista")
        nodos: list[str] = []
        for item in valor:
            if not isinstance(item, str):
                raise ValueError("Cada nodo debe ser una cadena de texto")
            nodo = item.strip()
            if nodo not in self.nodos:
                raise ValueError(f"Nodo no permitido: {nodo}")
            if nodo not in nodos:
                nodos.append(nodo)
        return nodos

    def _validar_nodo(self, nodo: str) -> str:
        if nodo not in self.nodos:
            raise ValueError(f"Nodo no permitido: {nodo}")
        return nodo

    # ------------------------------------------------------------------ simulador

    def iniciar(self) -> dict[str, Any]:
        with self._candado:
            if self._ejecutando:
                return {"ok": False, "error": "The simulator is already running."}
            self._parar.clear()
            self._despertar.clear()
            self._ejecutando = True
            self._ultima_salida = None
            self._evento("Simulator", "Simulator started.")
            self._hilo = threading.Thread(target=self._bucle, name="simulador-ciclo", daemon=True)
            self._hilo.start()
        return {"ok": True, "message": "Simulator started."}

    def detener(self) -> dict[str, Any]:
        with self._candado:
            if not self._ejecutando:
                return {"ok": False, "error": "The simulator is not running."}
            if self._escenario is not None:
                self._detener_escenario_bloqueado()
            self._limpiar_todo_bloqueado()
            hilo = self._hilo
            self._parar.set()
            self._despertar.set()

        forzado = False
        if hilo is not None:
            hilo.join(timeout=self.cliente.timeout + 5)
            forzado = hilo.is_alive()

        with self._candado:
            self._ejecutando = False
            self._hilo = None
            self._invalidar_escenario()
            self._ultima_salida = "Simulator stopped."
            self._evento("Simulator", "Simulator stopped." + (" The cycle did not stop in time." if forzado else ""))
        return {"ok": True, "message": "Simulator stopped.", "forced": forzado}

    def _bucle(self) -> None:
        """Ciclo normal cada intervalo; una anomalía despierta el ciclo para enviar de inmediato."""
        self._linea(
            f"Simulador iniciado | nodos={','.join(self.nodos)} | "
            f"intervalo_normal={self.intervalo_s}s | emergencias=inmediatas | destino=bridge")
        secuencia = 0
        try:
            while not self._parar.is_set():
                secuencia += 1
                try:
                    self._ciclo(secuencia)
                except Exception as exc:  # Un ciclo fallido no debe detener la simulación.
                    self._linea(f"cycle={secuencia:05d} | error={exc!r}")
                self._despertar.wait(self.intervalo_s)
                self._despertar.clear()
        finally:
            with self._candado:
                if self._hilo is threading.current_thread():
                    self._ejecutando = False
                    self._ultima_salida = self._ultima_salida or "Simulator stopped."
            self._linea("Simulador detenido.")

    def _ciclo(self, secuencia: int) -> None:
        with self._candado:
            anomalias = {nodo: set(valores) for nodo, valores in self._anomalias.items()}
            silenciados = set(self._silenciados)
            apagados = set(self._apagados)

        lecturas: list[dict[str, Any]] = []
        for nodo in self.nodos:
            if nodo in apagados:
                continue
            lecturas.extend(eventos_nodo(nodo, secuencia, anomalias[nodo], silenciados, self._rng))

        if not lecturas:
            self._linea(f"cycle={secuencia:05d} | sin lecturas (nodos apagados o sensores sin respuesta)")
            return
        try:
            resultado = self.cliente.enviar_lecturas(lecturas)
        except ClienteBridgeError as exc:
            self._linea(f"cycle={secuencia:05d} | bridge_unavailable={exc}")
            return
        self._linea(
            f"cycle={secuencia:05d} | generated={len(lecturas):02d} readings | "
            f"bridge_inserted={resultado.get('raw_inserted', 0):02d} | "
            f"rest={resultado.get('rest_realtime', 0)} | "
            f"mqtt_catchup={resultado.get('mqtt_catch_up', 0):02d} | "
            f"lora={'ON' if resultado.get('lora_summary') else 'OFF'}")

    # ------------------------------------------------------------------ anomalías

    def _poner_anomalia_bloqueado(self, nodo: str, alias: str) -> None:
        self._anomalias[nodo].add(resolver_sensor(alias))
        self._evento("Command", f"anomaly {nodo} {alias}")
        self._despertar.set()  # No espera al siguiente intervalo: la emergencia sale ya.

    def _limpiar_pares_bloqueado(self, pares: list[tuple[str, str]]) -> None:
        for nodo, alias in pares:
            self._anomalias[nodo].discard(resolver_sensor(alias))

    def _limpiar_todo_bloqueado(self) -> None:
        for valores in self._anomalias.values():
            valores.clear()

    def poner_anomalia(self, nodo: str, sensor: str) -> dict[str, Any]:
        with self._candado:
            self._validar_nodo(nodo)
            resolver_sensor(sensor)
            self._poner_anomalia_bloqueado(nodo, sensor.strip().lower())
        return {"ok": True, "message": f"Anomaly set on {nodo} / {sensor}."}

    def limpiar_anomalia(self, nodo: str, sensor: str) -> dict[str, Any]:
        with self._candado:
            self._validar_nodo(nodo)
            self._anomalias[nodo].discard(resolver_sensor(sensor))
            self._evento("Command", f"clear {nodo} {sensor}")
        return {"ok": True, "message": f"Anomaly cleared on {nodo} / {sensor}."}

    # ------------------------------------------------------------------ fallos

    def apagar_nodo(self, nodo: str) -> dict[str, Any]:
        with self._candado:
            self._apagados.add(self._validar_nodo(nodo))
            self._evento("Fault", f"Node {nodo} powered off; it stops sending readings.")
        return {"ok": True, "message": f"{nodo} powered off."}

    def encender_nodo(self, nodo: str) -> dict[str, Any]:
        with self._candado:
            self._apagados.discard(self._validar_nodo(nodo))
            self._evento("Fault", f"Node {nodo} powered on.")
        return {"ok": True, "message": f"{nodo} powered on."}

    def silenciar_sensor(self, nodo: str, sensor: str) -> dict[str, Any]:
        with self._candado:
            self._silenciados.add((self._validar_nodo(nodo), resolver_sensor(sensor)))
            self._evento("Fault", f"Sensor {sensor} on {nodo} stopped responding.")
        return {"ok": True, "message": f"{sensor} on {nodo} stopped responding."}

    def reactivar_sensor(self, nodo: str, sensor: str) -> dict[str, Any]:
        with self._candado:
            self._silenciados.discard((self._validar_nodo(nodo), resolver_sensor(sensor)))
            self._evento("Fault", f"Sensor {sensor} on {nodo} responds again.")
        return {"ok": True, "message": f"{sensor} on {nodo} responds again."}

    def fallos(self) -> dict[str, Any]:
        with self._candado:
            return {
                "nodos_apagados": sorted(self._apagados),
                "sensores_silenciados": [
                    {"node": nodo, "sensor": tipo} for nodo, tipo in sorted(self._silenciados)],
                "anomalias": {nodo: sorted(valores) for nodo, valores in self._anomalias.items()},
            }

    # ------------------------------------------------------------------ escenarios

    def iniciar_escenario_desde(self, cuerpo: dict[str, Any]) -> dict[str, Any]:
        """Valida el cuerpo de la petición del panel y activa el escenario."""
        nombre = cuerpo.get("scenario")
        if not isinstance(nombre, str):
            raise ValueError("'scenario' must be a string.")
        nombre = nombre.strip().lower()
        if nombre not in ESCENARIOS:
            raise ValueError("Unknown scenario. Use fire, earthquake, or power_failure.")

        nodos = self.normalizar_nodos(cuerpo.get("nodes", []))
        if nombre == "power_failure":
            if len(nodos) != 1:
                raise ValueError("Power failure requires exactly one selected node.")
        elif not nodos:
            nodos = nodos_por_defecto(nombre, self.nodos)

        duracion = cuerpo.get("duration_s")
        if duracion is not None:
            if isinstance(duracion, bool) or not isinstance(duracion, int) or duracion <= 0:
                raise ValueError("'duration_s' must be a positive integer or null.")
        return self.iniciar_escenario(nombre, nodos, duracion)

    def iniciar_escenario(self, nombre: str, nodos: list[str], duracion_s: int | None) -> dict[str, Any]:
        with self._candado:
            if not self._ejecutando:
                return {"ok": False, "error": "Start the simulator before activating a scenario."}
            if self._escenario is not None:
                self._detener_escenario_bloqueado()

            self._token_escenario += 1
            token = self._token_escenario
            definicion = ESCENARIOS[nombre]
            sensores = tuple(definicion["sensors"])
            pares = [(nodo, sensor) for nodo in nodos for sensor in sensores]
            self._escenario = {
                "name": nombre,
                "label": definicion["label"],
                "nodes": list(nodos),
                "sensors": list(sensores),
                "pairs": pares,
                "duration_s": duracion_s,
                "started_at": utc_ahora(),
                "started_monotonic": time.monotonic(),
                "token": token,
            }
            self._evento(
                "Scenario",
                f"Activated {nombre}; nodes={', '.join(nodos)}; "
                f"duration={'manual' if duracion_s is None else str(duracion_s) + ' s'}")

        threading.Thread(
            target=self._ejecutar_escenario, args=(nombre, pares, duracion_s, token),
            name=f"escenario-{nombre}", daemon=True).start()
        return {"ok": True, "message": "Scenario activated."}

    def _ejecutar_escenario(self, nombre: str, pares: list[tuple[str, str]],
                            duracion_s: int | None, token: int) -> None:
        """Activa las anomalías una a una y administra la duración."""
        for indice, (nodo, sensor) in enumerate(pares):
            with self._candado:
                if (self._escenario is None or self._escenario.get("token") != token
                        or not self._ejecutando):
                    return
                self._poner_anomalia_bloqueado(nodo, sensor)
            if indice < len(pares) - 1:
                time.sleep(0.3)

        if duracion_s is None:
            return

        limite = time.monotonic() + duracion_s
        while time.monotonic() < limite:
            with self._candado:
                if self._escenario is None or self._escenario.get("token") != token:
                    return
            time.sleep(min(0.2, max(0.0, limite - time.monotonic())))

        with self._candado:
            activo = self._escenario
            if activo is None or activo.get("token") != token:
                return
            self._limpiar_pares_bloqueado(pares)
            self._escenario = None
            self._token_escenario += 1
            self._evento("Scenario", f"Duration complete; cleared {nombre}.")

    def _detener_escenario_bloqueado(self) -> None:
        """Detiene y limpia únicamente los sensores del escenario activo."""
        escenario = self._escenario
        self._token_escenario += 1
        self._escenario = None
        if escenario is None:
            return
        self._limpiar_pares_bloqueado(escenario.get("pairs", []))
        self._evento("Scenario", f"Stopped and cleared {escenario.get('name', 'active scenario')}.")

    def _invalidar_escenario(self) -> None:
        self._token_escenario += 1
        self._escenario = None

    def detener_escenario(self) -> dict[str, Any]:
        with self._candado:
            if self._escenario is not None:
                self._detener_escenario_bloqueado()
            else:
                self._token_escenario += 1
            self._limpiar_todo_bloqueado()
            self._evento("Scenario", "All scenario sensor combinations cleared.")
        return {"ok": True, "message": "All scenarios stopped; sensors cleared."}

    # ------------------------------------------------------------------ estado

    def estado(self) -> dict[str, Any]:
        with self._candado:
            escenario = self._escenario
            info_escenario = None
            if escenario is not None:
                transcurrido = time.monotonic() - escenario["started_monotonic"]
                duracion = escenario["duration_s"]
                info_escenario = {
                    "name": escenario["name"],
                    "label": escenario["label"],
                    "nodes": list(escenario["nodes"]),
                    "sensors": list(escenario["sensors"]),
                    "duration_s": duracion,
                    "started_at": escenario["started_at"],
                    "elapsed_s": round(max(0.0, transcurrido), 1),
                    "countdown_s": None if duracion is None else max(0, int(duracion - transcurrido)),
                }
            return {
                "simulator_running": self._ejecutando,
                # El simulador es este mismo servicio: nunca hay un proceso externo que avisar.
                "started_by_panel": self._ejecutando,
                "simulator_pid": None,
                "scenario": info_escenario,
                "log": list(self._salida),
                "events": list(self._eventos),
                "last_process_exit": self._ultima_salida,
            }

    def estado_panel(self) -> dict[str, Any]:
        """Estado completo para el panel: el simulador más lo que informa el bridge por HTTP."""
        salud = self.cliente.estado()
        return {
            "status": self.estado(),
            "bridge": _metricas_bridge(salud),
            "bridge_active": salud is not None,
            "warning": "",
        }

    def registrar_error(self, detalle: str) -> None:
        self._linea(f"error={detalle}")

    def apagar(self) -> None:
        """Cierre ordenado del servicio: limpia anomalías y detiene el ciclo."""
        if self._ejecutando:
            self.detener()
