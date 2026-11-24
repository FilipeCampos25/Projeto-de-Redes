"""Servidor HTTP didático. Execute somente em laboratório controlado."""

import argparse
import logging

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException, UnsupportedMediaType
from werkzeug.serving import WSGIRequestHandler


class LaboratoryRequestHandler(WSGIRequestHandler):
    """Evita o log duplicado do Werkzeug, que inclui IP e query string."""

    def log_request(self, code="-", size="-"):
        pass  # O after_request registra somente método, caminho e status.


def create_app():
    """Cria a aplicação sem abrir sockets nem iniciar threads."""
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024

    @app.get("/")
    def index():
        return jsonify(
            servico="http",
            status="ok",
            mensagem="Servidor HTTP do laboratório de redes ativo",
        )

    @app.post("/echo")
    def echo():
        if not request.is_json:
            raise UnsupportedMediaType()
        return jsonify(status="recebido", dados=request.get_json())

    @app.errorhandler(HTTPException)
    def http_error(error):
        # Preserva os cabeçalhos do protocolo, inclusive Allow no erro 405.
        response = error.get_response()
        response.data = app.json.dumps({"erro": error.name, "codigo": error.code})
        response.content_type = "application/json"
        return response

    @app.after_request
    def log_response(response):
        app.logger.info("HTTP %s %r %s", request.method, request.path, response.status_code)
        return response

    return app


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1", help="Endereço de bind (padrão: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8080, help="Porta TCP (padrão: 8080)")
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("--port deve estar entre 1 e 65535")

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    app = create_app()
    app.logger.info("Iniciando servidor HTTP em %s:%s", args.host, args.port)
    app.run(
        host=args.host,
        port=args.port,
        debug=False,
        use_reloader=False,
        request_handler=LaboratoryRequestHandler,
    )


if __name__ == "__main__":
    main()
