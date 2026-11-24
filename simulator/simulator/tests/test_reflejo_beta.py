"""Las anomalías del panel de escenarios se reflejan en la API de control de Beta."""
import json
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from app.datos.cliente_beta import ClienteBeta
from app.datos.cliente_bridge import ClienteBridge
from app.negocio.reflejo_beta import ReflejoBeta
from app.negocio.simulacion import ControladorSimulacion

NODOS = ["NODE-FLOOR-1", "NODE-FLOOR-2"]


class BetaFalso(BaseHTTPRequestHandler):
    recibidos: list[dict] = []
    responder_error = False

    def do_POST(self) -> None:  # noqa: N802
        cuerpo = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path != "/api/control":
            self.send_response(404)
            self.end_headers()
            return
        if BetaFalso.responder_error:
            self.send_response(503)
            self.end_headers()
            return
        BetaFalso.recibidos.append(cuerpo)
        datos = json.dumps({"ok": True}).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(datos)))
        self.end_headers()
        self.wfile.write(datos)

    def log_message(self, *_args: object) -> None:
        pass


class ReflejoBetaTest(unittest.TestCase):
    def setUp(self) -> None:
        BetaFalso.recibidos, BetaFalso.responder_error = [], False
        self.servidor = ThreadingHTTPServer(("127.0.0.1", 0), BetaFalso)
        threading.Thread(target=self.servidor.serve_forever, daemon=True).start()
        self.addCleanup(self.servidor.server_close)
        self.addCleanup(self.servidor.shutdown)
        self.lineas: list[str] = []
        url = f"http://127.0.0.1:{self.servidor.server_port}"
        self.reflejo = ReflejoBeta(ClienteBeta(url, 2.0), self.lineas.append)
        # El cliente del bridge no se usa: no se inicia el ciclo.
        self.controlador = ControladorSimulacion(
            nodos=NODOS, intervalo_s=30, cliente=ClienteBridge("http://127.0.0.1:1", 1), reflejo=self.reflejo)

    def enviados(self) -> set[tuple[str, str, bool]]:
        self.reflejo.esperar()
        return {(c["target"], c["sensor"], c["value"]) for c in BetaFalso.recibidos}

    def test_fire_sets_thermal_and_gas_anomalies_on_every_node(self) -> None:
        self.controlador._ejecutando = True
        self.controlador.iniciar_escenario("fire", NODOS, None)
        time.sleep(1.5)  # el escenario activa un par cada 0.3 s
        self.assertEqual(self.enviados(), {
            (nodo, tipo, True) for nodo in NODOS for tipo in ("thermal_array", "gas_environmental")})
        self.assertTrue(all(c["action"] == "anomaly" for c in BetaFalso.recibidos))

    def test_stopping_the_scenario_clears_only_what_was_set(self) -> None:
        self.controlador._ejecutando = True
        self.controlador.iniciar_escenario("earthquake", ["NODE-FLOOR-1"], None)
        time.sleep(0.8)
        self.controlador.detener_escenario()
        self.assertEqual(self.enviados(), {
            ("NODE-FLOOR-1", "accelerometer", True), ("NODE-FLOOR-1", "accelerometer", False)})

    def test_normal_scenarios_are_not_mirrored_in_beta(self) -> None:
        # 24-nov-2026: Beta only knows "anomaly on a sensor" and would generate its fire values: a candle mirrored
        # there reached the backend as a fire. Only the real-event mode ("fire") is mirrored.
        self.controlador._ejecutando = True
        self.controlador.iniciar_escenario("candle", NODOS, None)
        time.sleep(0.8)
        self.controlador.detener_escenario()
        self.controlador.iniciar_escenario("spray", NODOS, None)
        time.sleep(0.8)
        self.controlador.detener_escenario()
        self.assertEqual(self.enviados(), set())

    def test_clearing_something_not_set_sends_nothing(self) -> None:
        self.controlador.limpiar_anomalia("NODE-FLOOR-2", "ina219")
        self.controlador.detener_escenario()
        self.assertEqual(self.enviados(), set())

    def test_manual_anomaly_and_clear_are_mirrored_in_order(self) -> None:
        self.controlador.poner_anomalia("NODE-FLOOR-2", "adxl355")
        self.controlador.limpiar_anomalia("NODE-FLOOR-2", "adxl355")
        self.reflejo.esperar()
        self.assertEqual([c["value"] for c in BetaFalso.recibidos], [True, False])

    def test_beta_failure_is_logged_and_never_breaks_the_simulation(self) -> None:
        BetaFalso.responder_error = True
        self.controlador.poner_anomalia("NODE-FLOOR-1", "grideye")
        self.reflejo.esperar()
        self.assertIn("thermal_array", self.controlador.fallos()["anomalias"]["NODE-FLOOR-1"])
        self.assertTrue(any("no se pudo reflejar" in linea for linea in self.lineas))

    def test_disabled_when_no_url_is_configured(self) -> None:
        reflejo = ReflejoBeta(ClienteBeta(""))
        self.assertFalse(reflejo.activo)
        reflejo.anomalia("NODE-FLOOR-1", "thermal_array", True)  # no hace nada ni falla


if __name__ == "__main__":
    unittest.main()
