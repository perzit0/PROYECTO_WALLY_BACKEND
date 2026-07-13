from flask import Blueprint, request, jsonify
from models import db
from models.push_suscripcion import PushSuscripcion
from services.push_service import VAPID_PUBLIC_KEY, enviar_webpush_a_todos

push_bp = Blueprint("push", __name__, url_prefix="/api/push")


@push_bp.route("/clave-publica", methods=["GET"])
def clave_publica():
    """Clave pública VAPID que el navegador necesita para suscribirse."""
    if not VAPID_PUBLIC_KEY:
        return jsonify({"error": "Web push no configurado en el servidor"}), 503
    return jsonify({"clave": VAPID_PUBLIC_KEY}), 200


@push_bp.route("/suscribir", methods=["POST"])
def suscribir():
    data = request.get_json() or {}
    endpoint = data.get("endpoint")
    keys = data.get("keys") or {}
    p256dh = keys.get("p256dh")
    auth = keys.get("auth")

    if not endpoint or not p256dh or not auth:
        return jsonify({"error": "Suscripción incompleta"}), 400

    sub = PushSuscripcion.query.filter_by(endpoint=endpoint).first()
    if sub:
        sub.p256dh = p256dh
        sub.auth = auth
    else:
        sub = PushSuscripcion(endpoint=endpoint, p256dh=p256dh, auth=auth)
        db.session.add(sub)
    db.session.commit()

    return jsonify({"mensaje": "Alarmas activadas en este dispositivo"}), 201


@push_bp.route("/desuscribir", methods=["POST"])
def desuscribir():
    data = request.get_json() or {}
    endpoint = data.get("endpoint")
    if endpoint:
        PushSuscripcion.query.filter_by(endpoint=endpoint).delete()
        db.session.commit()
    return jsonify({"mensaje": "Alarmas desactivadas en este dispositivo"}), 200


@push_bp.route("/probar", methods=["POST"])
def probar():
    """Manda una alarma de prueba a todos los celulares suscritos."""
    total = PushSuscripcion.query.count()
    if total == 0:
        return jsonify({"error": "Ningún dispositivo tiene las alarmas activadas"}), 404

    enviar_webpush_a_todos(
        titulo="🚨 Prueba de alarma WALLY",
        mensaje="Si estás viendo esto, las alarmas en tu celular funcionan.",
    )
    return jsonify({"mensaje": f"Alarma de prueba enviada a {total} dispositivo(s)"}), 200
