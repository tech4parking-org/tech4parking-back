"""Servidor local da API de vagas, sem AWS.

Roda o mesmo `lambda_handler` da Lambda, com uma tabela em memória no lugar do
DynamoDB, e publica a documentação no Swagger UI.

Uso:
    pip install boto3
    python services/lambdas/process_car_parking/local_server.py
    # http://localhost:8000/docs
"""
import json
import os
import sys
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import process_car_parking as lambda_module  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
OPENAPI = os.path.join(ROOT, "docs", "openapi.yaml")
PORT = int(os.environ.get("PORT", "8000"))


class InMemoryTable:
    """Implementa só o que a Lambda usa da tabela do DynamoDB."""

    def __init__(self, items):
        self.items = {i["spot_id"]: i for i in items}

    def scan(self, **_):
        return {"Items": list(self.items.values())}

    def put_item(self, Item):
        self.items[Item["spot_id"]] = Item

    def delete_item(self, Key):
        self.items.pop(Key["spot_id"], None)

    def update_item(self, Key, ExpressionAttributeValues, **_):
        item = self.items.setdefault(Key["spot_id"], {"spot_id": Key["spot_id"]})
        item.update(availability=ExpressionAttributeValues[":a"],
                    distance=ExpressionAttributeValues[":d"],
                    updated_at=ExpressionAttributeValues[":u"])


def seed():
    d = Decimal
    return [
        {"spot_id": "A-01", "name": "Vaga A-01 · Av. Paulista, 1000", "latitude": d("-23.5614"), "longitude": d("-46.6559"), "availability": "disponível"},
        {"spot_id": "A-02", "name": "Vaga A-02 · Av. Paulista, 1000", "latitude": d("-23.5615"), "longitude": d("-46.6560"), "availability": "ocupada", "distance": d("12.4")},
        {"spot_id": "C-07", "name": "Vaga C-07 · FIAP Paulista", "latitude": d("-23.5640"), "longitude": d("-46.6525"), "availability": "disponível"},
    ]


lambda_module.table = InMemoryTable(seed())

DOCS_HTML = """<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><title>Tech4Parking · API de vagas</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css"></head>
<body><div id="swagger"></div>
<script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
<script>SwaggerUIBundle({url: "/openapi.yaml", dom_id: "#swagger", deepLinking: true, tryItOutEnabled: true});</script>
</body></html>"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body=b"", ctype="application/json", headers=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _lambda(self, method):
        url = urlparse(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        event = {
            "httpMethod": method,
            "path": url.path,
            "queryStringParameters": {k: v[0] for k, v in parse_qs(url.query).items()} or None,
            "body": self.rfile.read(length).decode() if length else None,
        }
        resp = lambda_module.lambda_handler(event, None)
        headers = {k: v for k, v in resp.get("headers", {}).items() if k.lower() != "content-type"}
        self._send(resp["statusCode"], resp.get("body", "").encode(), headers=headers)

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/docs"):
            return self._send(200, DOCS_HTML.encode(), "text/html; charset=utf-8")
        if path == "/openapi.yaml":
            return self._send(200, open(OPENAPI, "rb").read(), "application/yaml")
        if path == "/spots":
            return self._lambda("GET")
        self._send(404, json.dumps({"message": "not found"}).encode())

    def do_POST(self):
        self._lambda("POST")

    def do_DELETE(self):
        self._lambda("DELETE")

    def do_OPTIONS(self):
        self._lambda("OPTIONS")

    def log_message(self, fmt, *args):
        print(f"{self.command} {self.path} -> {args[1] if len(args) > 1 else ''}")


if __name__ == "__main__":
    print(f"API local em http://localhost:{PORT}/docs")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
