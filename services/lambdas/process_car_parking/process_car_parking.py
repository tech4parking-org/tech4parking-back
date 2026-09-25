"""Lambda de vagas do Tech4Parking.

Recebe dois tipos de evento:
- Mensagens do sensor (regra IoT no tópico `parking_sensor`):
  {"spot_id": "A-01", "status": "ocupada" | "disponível", "distance": 12.3}
  -> atualiza a disponibilidade da vaga.
- Requisições HTTP da API Gateway (`/spots`), usadas pelo front:
  GET    /spots                -> lista as vagas
  POST   /spots                -> cadastra uma vaga {name, latitude, longitude, availability}
  DELETE /spots?spot_id=<id>   -> remove uma vaga
"""
import json
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import boto3

TABLE_NAME = os.environ.get("TABLE_NAME", "ParkingSpots")
VALID_STATUS = {"ocupada", "disponível"}

table = boto3.resource("dynamodb").Table(TABLE_NAME)

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET,POST,DELETE,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def to_json(value):
    if isinstance(value, list):
        return [to_json(v) for v in value]
    if isinstance(value, dict):
        return {k: to_json(v) for k, v in value.items()}
    if isinstance(value, Decimal):
        return float(value)
    return value


def response(status_code, body=None):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json", **CORS_HEADERS},
        "body": json.dumps(to_json(body), ensure_ascii=False) if body is not None else "",
    }


def handle_sensor(event):
    spot_id = str(event.get("spot_id", "")).strip()
    status = event.get("status")
    if not spot_id or status not in VALID_STATUS:
        print(f"Mensagem do sensor ignorada: {event}")
        return {"ignored": True}

    table.update_item(
        Key={"spot_id": spot_id},
        UpdateExpression="SET availability = :a, distance = :d, updated_at = :u",
        ExpressionAttributeValues={
            ":a": status,
            ":d": Decimal(str(event.get("distance", 0))),
            ":u": now_iso(),
        },
    )
    print(f"Vaga {spot_id} -> {status}")
    return {"spot_id": spot_id, "availability": status}


def list_spots():
    items = []
    scan = table.scan()
    items.extend(scan.get("Items", []))
    while "LastEvaluatedKey" in scan:
        scan = table.scan(ExclusiveStartKey=scan["LastEvaluatedKey"])
        items.extend(scan.get("Items", []))
    return response(200, items)


def create_spot(event):
    try:
        data = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return response(400, {"message": "JSON inválido"})

    name = str(data.get("name", "")).strip()
    try:
        latitude = Decimal(str(data["latitude"]))
        longitude = Decimal(str(data["longitude"]))
    except (KeyError, ArithmeticError):
        return response(400, {"message": "latitude e longitude são obrigatórias"})
    availability = data.get("availability", "disponível")
    if not name or availability not in VALID_STATUS:
        return response(400, {"message": "name e availability (ocupada|disponível) são obrigatórios"})

    spot = {
        "spot_id": str(data.get("spot_id") or uuid.uuid4()),
        "name": name,
        "latitude": latitude,
        "longitude": longitude,
        "availability": availability,
        "updated_at": now_iso(),
    }
    table.put_item(Item=spot)
    return response(201, spot)


def delete_spot(event):
    spot_id = (event.get("queryStringParameters") or {}).get("spot_id")
    if not spot_id:
        return response(400, {"message": "informe ?spot_id="})
    table.delete_item(Key={"spot_id": spot_id})
    return response(204)


def handle_http(event):
    method = event.get("httpMethod")
    if method == "OPTIONS":
        return response(200, {})
    if method == "GET":
        return list_spots()
    if method == "POST":
        return create_spot(event)
    if method == "DELETE":
        return delete_spot(event)
    return response(405, {"message": f"método {method} não suportado"})


def lambda_handler(event, context):
    if "httpMethod" in event:
        return handle_http(event)
    return handle_sensor(event)
