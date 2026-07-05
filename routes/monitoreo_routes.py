from flask import Blueprint, request, jsonify, send_file
from datetime import datetime, timedelta
from models import db
from models.monitoreo import MonitoreoZonal
from models.lectura import Lectura, UltimaLectura
from services.auth_service import verificar_token
from services.export_service import exportar_monitoreo_excel
from routes.datos_routes import _finalizar_monitoreo, DURACION_MAXIMA_MONITOREO

monitoreo_bp = Blueprint("monitoreo", __name__, url_prefix="/api/monitoreo")

# Un fix se considera "fresco" si llegó en los últimos 15 segundos
FRESCURA_GPS = timedelta(seconds=15)


def obtener_usuario_actual():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ")[1]
    return verificar_token(token)


@monitoreo_bp.route("/verificar-gps/<device_id>", methods=["GET"])
def verificar_gps(device_id):
    """Paso previo obligatorio antes de iniciar: confirma que el robot está
    transmitiendo GPS válido y reciente."""
    ultima = UltimaLectura.query.filter_by(device_id=device_id).first()
    if not ultima:
        return jsonify({"listo": False, "razon": "El robot aún no ha enviado ningún dato."}), 200

    ahora = datetime.utcnow()
    segundos_desde_ultimo_dato = (ahora - ultima.timestamp).total_seconds()

    if segundos_desde_ultimo_dato > 10:
        return jsonify({
            "listo": False,
            "razon": f"El robot no envía datos desde hace {int(segundos_desde_ultimo_dato)}s. Verifica que esté encendido y conectado a WiFi.",
        }), 200

    if ultima.lat is None or ultima.lng is None:
        return jsonify({"listo": False, "razon": "El robot no tiene ninguna ubicación registrada todavía."}), 200

    if not ultima.gps_ultimo_fix or (ahora - ultima.gps_ultimo_fix) > FRESCURA_GPS:
        return jsonify({
            "listo": False,
            "razon": "El GPS no tiene señal fresca en este momento. Muévete a un espacio abierto y espera unos segundos.",
        }), 200

    return jsonify({
        "listo": True,
        "lat": ultima.lat,
        "lng": ultima.lng,
        "timestamp": ultima.timestamp.isoformat() + "Z",
    }), 200


@monitoreo_bp.route("/iniciar", methods=["POST"])
def iniciar_monitoreo():
    payload = obtener_usuario_actual()
    data = request.get_json()
    device_id = data.get("device_id")
    nombre = data.get("nombre")

    if not device_id:
        return jsonify({"error": "device_id es obligatorio"}), 400

    existente = MonitoreoZonal.query.filter_by(device_id=device_id, estado="activo").first()
    if existente:
        return jsonify({"error": "Ya hay un monitoreo activo para este robot", "monitoreo": existente.to_dict()}), 409

    ultima = UltimaLectura.query.filter_by(device_id=device_id).first()
    ahora = datetime.utcnow()

    if not ultima or ultima.lat is None:
        return jsonify({"error": "No se puede iniciar sin una ubicación GPS válida. Verifica primero con /verificar-gps."}), 400

    if not ultima.gps_ultimo_fix or (ahora - ultima.gps_ultimo_fix) > FRESCURA_GPS:
        return jsonify({"error": "El GPS no tiene señal fresca. Espera a tener buena señal antes de iniciar."}), 400

    monitoreo = MonitoreoZonal(
        device_id=device_id,
        usuario_id=payload["id"] if payload else None,
        nombre=nombre,
        estado="activo",
        hora_inicio=ahora,
        lat_inicio=ultima.lat,
        lng_inicio=ultima.lng,
    )
    db.session.add(monitoreo)
    db.session.commit()

    return jsonify({"mensaje": "Monitoreo zonal iniciado", "monitoreo": monitoreo.to_dict()}), 201


@monitoreo_bp.route("/activo/<device_id>", methods=["GET"])
def obtener_activo(device_id):
    """Para que el frontend haga polling y dibuje el trazo en vivo mientras
    el monitoreo está en curso."""
    monitoreo = (
        MonitoreoZonal.query.filter_by(device_id=device_id, estado="activo")
        .order_by(MonitoreoZonal.hora_inicio.desc())
        .first()
    )
    if not monitoreo:
        return jsonify({"activo": False}), 200

    ahora = datetime.utcnow()
    if (ahora - monitoreo.hora_inicio) >= DURACION_MAXIMA_MONITOREO:
        _finalizar_monitoreo(monitoreo, ahora)
        return jsonify({"activo": False, "cerrado_automaticamente": True, "monitoreo": monitoreo.to_dict()}), 200

    puntos = (
        Lectura.query.filter_by(monitoreo_id=monitoreo.id)
        .order_by(Lectura.timestamp.asc())
        .all()
    )

    segundos_restantes = int(DURACION_MAXIMA_MONITOREO.total_seconds() - (ahora - monitoreo.hora_inicio).total_seconds())

    return jsonify({
        "activo": True,
        "monitoreo": monitoreo.to_dict(),
        "segundos_restantes": max(segundos_restantes, 0),
        "trazo": [{"lat": p.lat, "lng": p.lng, "gps_interpolado": p.gps_interpolado, "timestamp": p.timestamp.isoformat() + "Z"} for p in puntos],
    }), 200


@monitoreo_bp.route("/<int:monitoreo_id>/finalizar", methods=["POST"])
def finalizar_monitoreo(monitoreo_id):
    monitoreo = MonitoreoZonal.query.get(monitoreo_id)
    if not monitoreo:
        return jsonify({"error": "Monitoreo no encontrado"}), 404

    if monitoreo.estado == "finalizado":
        return jsonify({"mensaje": "Este monitoreo ya estaba finalizado", "monitoreo": monitoreo.to_dict()}), 200

    _finalizar_monitoreo(monitoreo, datetime.utcnow())
    return jsonify({"mensaje": "Monitoreo finalizado", "monitoreo": monitoreo.to_dict()}), 200


@monitoreo_bp.route("/<int:monitoreo_id>", methods=["GET"])
def detalle_monitoreo(monitoreo_id):
    monitoreo = MonitoreoZonal.query.get(monitoreo_id)
    if not monitoreo:
        return jsonify({"error": "Monitoreo no encontrado"}), 404

    puntos = (
        Lectura.query.filter_by(monitoreo_id=monitoreo.id)
        .order_by(Lectura.timestamp.asc())
        .all()
    )
    return jsonify({
        "monitoreo": monitoreo.to_dict(),
        "lecturas": [p.to_dict() for p in puntos],
    }), 200


@monitoreo_bp.route("/dispositivo/<device_id>", methods=["GET"])
def listar_monitoreos_de_dispositivo(device_id):
    monitoreos = (
        MonitoreoZonal.query.filter_by(device_id=device_id)
        .order_by(MonitoreoZonal.hora_inicio.desc())
        .all()
    )
    return jsonify([m.to_dict() for m in monitoreos]), 200


@monitoreo_bp.route("/<int:monitoreo_id>/exportar", methods=["GET"])
def exportar_monitoreo(monitoreo_id):
    monitoreo = MonitoreoZonal.query.get(monitoreo_id)
    if not monitoreo:
        return jsonify({"error": "Monitoreo no encontrado"}), 404

    puntos = (
        Lectura.query.filter_by(monitoreo_id=monitoreo.id)
        .order_by(Lectura.timestamp.asc())
        .all()
    )
    buffer = exportar_monitoreo_excel(monitoreo, puntos)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"monitoreo_zonal_{monitoreo.id}.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
