from flask import Blueprint, request, jsonify
from models import db
from models.dispositivo import Dispositivo
from services.auth_service import verificar_token

dispositivo_bp = Blueprint("dispositivo", __name__, url_prefix="/api/dispositivos")


def obtener_usuario_actual():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ")[1]
    payload = verificar_token(token)
    return payload


@dispositivo_bp.route("/mios", methods=["GET"])
def mis_dispositivos():
    payload = obtener_usuario_actual()
    if not payload:
        return jsonify({"error": "Debes iniciar sesión"}), 401

    dispositivos = Dispositivo.query.filter_by(usuario_id=payload["id"]).all()
    return jsonify([d.to_dict() for d in dispositivos]), 200


@dispositivo_bp.route("/vincular", methods=["POST"])
def vincular_dispositivo():
    payload = obtener_usuario_actual()
    if not payload:
        return jsonify({"error": "Debes iniciar sesión"}), 401

    data = request.get_json()
    device_id = data.get("device_id", "").strip()

    if not device_id:
        return jsonify({"error": "device_id es obligatorio"}), 400

    dispositivo = Dispositivo.query.filter_by(device_id=device_id).first()

    if not dispositivo:
        return jsonify({"error": "Este robot aún no ha enviado datos. Enciéndelo primero e intenta de nuevo."}), 404

    if dispositivo.usuario_id is not None:
        return jsonify({"error": "Este robot ya está vinculado a otra cuenta"}), 409

    dispositivo.usuario_id = payload["id"]
    db.session.commit()

    return jsonify({"mensaje": "Robot vinculado correctamente", "dispositivo": dispositivo.to_dict()}), 200


@dispositivo_bp.route("/<device_id>", methods=["PUT"])
def editar_dispositivo(device_id):
    payload = obtener_usuario_actual()
    if not payload:
        return jsonify({"error": "Debes iniciar sesión"}), 401

    dispositivo = Dispositivo.query.filter_by(device_id=device_id).first()
    if not dispositivo:
        return jsonify({"error": "Robot no encontrado"}), 404

    if dispositivo.usuario_id != payload["id"] and payload.get("rol") != "admin":
        return jsonify({"error": "No tienes permiso para editar este robot"}), 403

    data = request.get_json()
    nombre = data.get("nombre")
    color = data.get("color")

    if nombre:
        dispositivo.nombre = nombre[:100]
    if color:
        dispositivo.color = color

    db.session.commit()
    return jsonify({"mensaje": "Robot actualizado", "dispositivo": dispositivo.to_dict()}), 200


@dispositivo_bp.route("/<device_id>/desvincular", methods=["POST"])
def desvincular_dispositivo(device_id):
    payload = obtener_usuario_actual()
    if not payload:
        return jsonify({"error": "Debes iniciar sesión"}), 401

    dispositivo = Dispositivo.query.filter_by(device_id=device_id).first()
    if not dispositivo:
        return jsonify({"error": "Robot no encontrado"}), 404

    if dispositivo.usuario_id != payload["id"] and payload.get("rol") != "admin":
        return jsonify({"error": "No tienes permiso"}), 403

    dispositivo.usuario_id = None
    db.session.commit()
    return jsonify({"mensaje": "Robot desvinculado"}), 200