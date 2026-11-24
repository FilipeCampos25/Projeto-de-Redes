"""Testes locais sem portas de rede e sem uma segunda máquina."""

import contextlib
import importlib
import io
import unittest
from unittest.mock import patch

from src import server_http


class ServerHTTPTests(unittest.TestCase):
    def setUp(self):
        self.app = server_http.create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def test_get_status(self):
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_get_json(self):
        response = self.client.get("/")
        self.assertEqual(response.mimetype, "application/json")
        self.assertIsInstance(response.get_json(), dict)

    def test_get_fields(self):
        self.assertEqual(self.client.get("/").get_json(), {
            "servico": "http", "status": "ok",
            "mensagem": "Servidor HTTP do laboratório de redes ativo",
        })

    def test_post_status(self):
        self.assertEqual(self.client.post("/echo", json={}).status_code, 200)

    def test_echo_data(self):
        for data in ({"mensagem": "Teste de Redes", "origem": "Cliente A"},
                     [1, "ação", False], "texto", 42, False, None):
            with self.subTest(data=data):
                response = self.client.post("/echo", data=self.app.json.dumps(data),
                                            content_type="application/json")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.get_json(), {"status": "recebido", "dados": data})

    def test_invalid_json(self):
        for body in ('{"incompleto":', ''):
            with self.subTest(body=body):
                response = self.client.post("/echo", data=body, content_type="application/json")
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.get_json()["codigo"], 400)

    def test_unsupported_media(self):
        for content_type in ("text/plain", "application/x-www-form-urlencoded", None):
            with self.subTest(content_type=content_type):
                response = self.client.post("/echo", data='{}', content_type=content_type)
                self.assertEqual(response.status_code, 415)
                self.assertEqual(response.get_json()["codigo"], 415)

    def test_body_limit(self):
        limit = self.app.config["MAX_CONTENT_LENGTH"]
        self.assertEqual(limit, 16384)
        for size, status in ((limit, 200), (limit + 1, 413)):
            with self.subTest(size=size):
                response = self.client.post("/echo", data='"' + 'a' * (size - 2) + '"',
                                            content_type="application/json")
                self.assertEqual(response.status_code, status)
                self.assertTrue(response.is_json)

    def test_method_not_allowed(self):
        response = self.client.post("/")
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.get_json()["codigo"], 405)
        self.assertIn("GET", response.headers["Allow"])

    def test_not_found(self):
        response = self.client.get("/inexistente")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()["codigo"], 404)

    def test_import_does_not_start_server(self):
        with patch("flask.Flask.run") as run, patch("socket.socket") as socket:
            importlib.reload(server_http)
            run.assert_not_called()
            socket.assert_not_called()

    def test_cli_defaults_and_lab(self):
        for args, host, port in (([], "127.0.0.1", 8080),
                                 (["--host", "0.0.0.0", "--port", "80"], "0.0.0.0", 80),
                                 (["--host", "192.0.2.20"], "192.0.2.20", 8080)):
            with self.subTest(args=args), patch("flask.Flask.run") as run:
                server_http.main(args)
                run.assert_called_once_with(host=host, port=port, debug=False,
                                            use_reloader=False,
                                            request_handler=server_http.LaboratoryRequestHandler)

    def test_invalid_port(self):
        for port in ("0", "65536", "abc"):
            with self.subTest(port=port), patch("flask.Flask.run") as run:
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                    server_http.main(["--port", port])
                self.assertEqual(error.exception.code, 2)
                run.assert_not_called()

    def test_logs_omit_body_and_query(self):
        with self.assertLogs(self.app.logger, level="INFO") as logs:
            self.client.post("/echo?token=segredo-query", json={"senha": "segredo-corpo"})
        output = " ".join(logs.output)
        self.assertIn("POST '/echo' 200", output)
        self.assertNotIn("segredo", output)


if __name__ == "__main__":
    unittest.main()
