from flask import Blueprint, request, jsonify
from models import db
from models.dispositivo import Dispositivo
from models.lectura import UltimaLectura
from services.auth_service import verificar_token
from functools import wraps

alertas_bp = Blueprint("alertas", __name__, url_prefix="/api/alertas")

UMBRALES = {
    "co": 50,
    "mq135": 300,
    "pm": 100,
}


def requiere_admin(f):
    @wraps(f)
    def decorador(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Token no proporcionado"}), 401
        token = auth_header.split(" ")[1]
        payload = verificar_token(token)
        if not payload or payload.get("rol") != "admin":
            return jsonify({"error": "Acceso solo para administradores"}), 403
        return f(*args, **kwargs)
    return decorador


@alertas_bp.route("/umbrales", methods=["GET"])
def obtener_umbrales():
    return jsonify(UMBRALES), 200


@alertas_bp.route("/activas", methods=["GET"])
def alertas_activas():
    """Devuelve todos los dispositivos cuya última lectura supera algún umbral."""
    dispositivos = Dispositivo.query.all()
    alertas = []

    for d in dispositivos:
        ultima = UltimaLectura.query.filter_by(device_id=d.device_id).first()
        if not ultima:
            continue

        superados = []
        if ultima.co is not None and ultima.co > UMBRALES["co"]:
            superados.append({"tipo": "co", "valor": ultima.co, "umbral": UMBRALES["co"]})
        if ultima.mq135 is not None and ultima.mq135 > UMBRALES["mq135"]:
            superados.append({"tipo": "mq135", "valor": ultima.mq135, "umbral": UMBRALES["mq135"]})
        if ultima.pm is not None and ultima.pm > UMBRALES["pm"]:
            superados.append({"tipo": "pm", "valor": ultima.pm, "umbral": UMBRALES["pm"]})

        if superados:
            alertas.append({
                "device_id": d.device_id,
                "nombre": d.nombre or d.device_id,
                "superados": superados,
                "timestamp": ultima.timestamp.isoformat() + "Z",
            })

    return jsonify(alertas), 200