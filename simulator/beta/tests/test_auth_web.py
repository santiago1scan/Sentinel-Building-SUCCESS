from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from dashboard_react_v2.auth_web import AuthWeb, FirebaseSettings
from simulator_v2.credentials import NodeRegistryStore
from simulator_v2.firebase_auth import FirebaseUser, ForbiddenError, UnauthorizedError
from simulator_v2.registro import ConsultaClient, RegistrationService

NODES = ("NODE-FLOOR-1", "NODE-FLOOR-2")


class FakeVerifier:
    def verify(self, token: str) -> FirebaseUser:
        if token == "prohibido":
            raise ForbiddenError("no")
        if token != "valido":
            raise UnauthorizedError("no")
        return FirebaseUser(uid="u1", email="a@x.com", email_verified=True)


class AuthWebTests(unittest.TestCase):
    def build(self, verifier=None, consulta_url: str = "") -> AuthWeb:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        service = RegistrationService(
            NodeRegistryStore(Path(tmp.name) / "c.json"), ConsultaClient(consulta_url), NODES)
        return AuthWeb(service, FirebaseSettings(project_id="p", api_key="k"), verifier)

    def test_pages_and_public_config_need_no_session(self) -> None:
        web = self.build()
        for path in ("/login", "/perfil", "/static/js/sesion.js", "/static/styles.css",
                     "/paginas/login/login.css", "/paginas/perfil/perfil.css"):
            self.assertEqual(web.get(path, {})[0], 200, path)
        config = json.loads(web.get("/auth/config", {})[2])
        self.assertTrue(config["configurado"])
        self.assertEqual(config["apiKey"], "k")

    def test_api_is_closed_without_firebase_or_valid_token(self) -> None:
        self.assertEqual(self.build(None).get("/api/registro", {})[0], 503)
        web = self.build(FakeVerifier())
        self.assertEqual(web.get("/api/registro", {})[0], 401)
        self.assertEqual(web.get("/api/registro", {"Authorization": "Bearer malo"})[0], 401)
        self.assertEqual(web.get("/auth/me", {"Authorization": "Bearer prohibido"})[0], 403)
        self.assertEqual(web.post("/api/registro", {}, b"{}")[0], 401)

    def test_authenticated_registration_validates_input(self) -> None:
        web = self.build(FakeVerifier())
        headers = {"Authorization": "Bearer valido"}
        self.assertEqual(web.get("/auth/me", headers)[0], 200)
        status = json.loads(web.get("/api/registro?node=NODE-FLOOR-2", headers)[2])
        self.assertEqual(status["nodo"], "NODE-FLOOR-2")
        self.assertEqual(web.get("/api/registro?node=NODE-X", headers)[0], 404)
        self.assertEqual(web.post("/api/registro", headers, b"no es json")[0], 422)
        self.assertEqual(web.post("/api/registro", headers,
                                  b'{"name":"n","building_id":0,"zone_id":1}')[0], 422)
        # Sin URL de consulta configurada el servicio responde 503, no 500.
        self.assertEqual(web.post("/api/registro", headers,
                                  b'{"name":"n","building_id":1,"zone_id":1}')[0], 503)


if __name__ == "__main__":
    unittest.main()
