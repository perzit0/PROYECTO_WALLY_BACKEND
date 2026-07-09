from flask import Blueprint, request, jsonify, send_file
from datetime import datetime, timedelta
from models import db
from models.monitoreo import MonitoreoZonal
from models.lectura import Lectura, UltimaLectura
from models.dispositivo import Dispositivo
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


def verificar_permiso_dispositivo(device_id, payload):
    """Un dispositivo sin dueño puede ser operado por cualquier usuario logueado
    (robot todavía no vinculado). Si ya tiene dueño, solo el dueño o un admin
    pueden iniciar/finalizar/exportar sus monitoreos."""
    dispositivo = Dispositivo.query.filter_by(device_id=device_id).first()
    if not dispositivo or dispositivo.usuario_id is None:
        return True
    return payload["id"] == dispositivo.usuario_id or payload.get("rol") == "admin"


@monitoreo_bp.route("/publico/zonas", methods=["GET"])
def zonas_publicas():
    """Devuelve todos los monitoreos finalizados con círculo (centro+radio) para
    pintarlos en el mapa público. No requiere login: son datos ambientales
    agregados, sin información personal."""
    monitoreos = (
        MonitoreoZonal.query.filter_by(estado="finalizado")
        .filter(MonitoreoZonal.centro_lat.isnot(None))
        .order_by(MonitoreoZonal.hora_fin.desc())
        .limit(300)
        .all()
    )

    orden_severidad = {"bueno": 0, "moderado": 1, "malo": 2, "critico": 3, None: -1}

    zonas = [
        {
            "id": m.id,
            "nombre": m.nombre,
            "centro_lat": m.centro_lat,
            "centro_lng": m.centro_lng,
            "radio_metros": m.radio_metros,
            "nivel_color": m.nivel_color,
            "color_hex": m.color_hex,
            "hora_fin": m.hora_fin.isoformat() + "Z" if m.hora_fin else None,
            "promedio_co": m.promedio_co,
            "promedio_mq135": m.promedio_mq135,
        }
        for m in monitoreos
    ]

    # Las zonas peores se ordenan al final para que se dibujen ENCIMA cuando
    # dos círculos se solapan: en Leaflet, el último elemento añadido queda
    # visualmente arriba. Así, si un área fue A(amarillo) y B(rojo) se cruzan,
    # el rojo (más crítico) siempre gana visualmente en la zona compartida.
    zonas.sort(key=lambda z: orden_severidad.get(z["nivel_color"], -1))

    return jsonify(zonas), 200


@monitoreo_bp.route("/publico/ranking", methods=["GET"])
def ranking_zonas():
    """Top de zonas con mejor y peor calidad de aire registrada históricamente.
    Es un valor agregado informativo (no en vivo, no repetitivo con el mapa)."""
    monitoreos = (
        MonitoreoZonal.query.filter_by(estado="finalizado")
        .filter(MonitoreoZonal.nivel_color.isnot(None))
        .all()
    )

    orden_severidad = {"bueno": 0, "moderado": 1, "malo": 2, "critico": 3}
    validos = [m for m in monitoreos if m.nivel_color in orden_severidad]

    def a_dict(m):
        return {
            "id": m.id,
            "nombre": m.nombre or f"Zona cerca de ({round(m.centro_lat, 4)}, {round(m.centro_lng, 4)})",
            "nivel_color": m.nivel_color,
            "color_hex": m.color_hex,
            "promedio_co": m.promedio_co,
            "promedio_mq135": m.promedio_mq135,
            "hora_fin": m.hora_fin.isoformat() + "Z" if m.hora_fin else None,
        }

    mejores = sorted(validos, key=lambda m: orden_severidad[m.nivel_color])[:5]
    peores = sorted(validos, key=lambda m: -orden_severidad[m.nivel_color])[:5]

    return jsonify({
        "total_zonas_medidas": len(validos),
        "mejores": [a_dict(m) for m in mejores],
        "peores": [a_dict(m) for m in peores],
    }), 200


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
    if not payload:
        return jsonify({"error": "Debes iniciar sesión para iniciar un monitoreo zonal"}), 401

    data = request.get_json()
    device_id = data.get("device_id")
    nombre = data.get("nombre")

    if not device_id:
        return jsonify({"error": "device_id es obligatorio"}), 400

    if not verificar_permiso_dispositivo(device_id, payload):
        return jsonify({"error": "No tienes permiso para operar este robot"}), 403

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
    payload = obtener_usuario_actual()
    if not payload:
        return jsonify({"error": "Debes iniciar sesión"}), 401

    monitoreo = MonitoreoZonal.query.get(monitoreo_id)
    if not monitoreo:
        return jsonify({"error": "Monitoreo no encontrado"}), 404

    if not verificar_permiso_dispositivo(monitoreo.device_id, payload):
        return jsonify({"error": "No tienes permiso sobre este monitoreo"}), 403

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
    payload = obtener_usuario_actual()
    if not payload:
        return jsonify({"error": "Debes iniciar sesión"}), 401

    monitoreo = MonitoreoZonal.query.get(monitoreo_id)
    if not monitoreo:
        return jsonify({"error": "Monitoreo no encontrado"}), 404

    if not verificar_permiso_dispositivo(monitoreo.device_id, payload):
        return jsonify({"error": "No tienes permiso sobre este monitoreo"}), 403

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
