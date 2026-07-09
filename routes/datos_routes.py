from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from models import db
from models.lectura import Lectura, UltimaLectura
from models.dispositivo import Dispositivo
from models.usuario import Usuario
from models.monitoreo import MonitoreoZonal
from services.email_service import enviar_alerta_contaminacion
from services.geo_service import haversine_m, calcular_centroide_y_radio, clasificar_nivel

datos_bp = Blueprint("datos", __name__, url_prefix="/api")

INTERVALO_GUARDADO = timedelta(minutes=1)
COOLDOWN_ALERTA = timedelta(minutes=15)
DURACION_MAXIMA_MONITOREO = timedelta(minutes=30)

LIMITE_CO = 35
LIMITE_MQ135 = 1200


def gps_es_valido(lat, lng):
    """Un fix GPS real nunca es exactamente (0,0) ni None. El NEO-6M manda
    (0,0) o valores None cuando no tiene señal."""
    if lat is None or lng is None:
        return False
    if abs(lat) < 0.0001 and abs(lng) < 0.0001:
        return False
    return True


@datos_bp.route("/datos", methods=["POST"])
def recibir_datos():
    data = request.get_json()
    device_id = data.get("device_id")

    if not device_id:
        return jsonify({"error": "device_id es obligatorio"}), 400

    dispositivo = Dispositivo.query.filter_by(device_id=device_id).first()
    if not dispositivo:
        dispositivo = Dispositivo(device_id=device_id)
        db.session.add(dispositivo)

    co = data.get("co")
    mq135 = data.get("mq135")
    co_raw = data.get("co_raw")
    mq135_raw = data.get("mq135_raw")

    lat_recibido = data.get("lat")
    lng_recibido = data.get("lng")
    velocidad_kmh = data.get("velocidad_kmh")
    rumbo = data.get("rumbo")

    ahora = datetime.utcnow()

    ultima = UltimaLectura.query.filter_by(device_id=device_id).first()

    fix_valido = gps_es_valido(lat_recibido, lng_recibido)

    if fix_valido:
        lat = lat_recibido
        lng = lng_recibido
        gps_interpolado = False
    else:
        # Sin señal: heredamos la última ubicación conocida en vez de
        # inventar o resetear a un punto fijo.
        lat = ultima.lat if ultima else None
        lng = ultima.lng if ultima else None
        gps_interpolado = True

    # Si no hay velocidad/rumbo del propio GPS, la calculamos con la
    # distancia al punto anterior (solo si el fix es real, para no medir
    # "velocidad" contra un punto heredado).
    if fix_valido and velocidad_kmh is None and ultima and ultima.lat is not None and not ultima.gps_interpolado:
        segundos = max((ahora - ultima.timestamp).total_seconds(), 1)
        distancia = haversine_m(ultima.lat, ultima.lng, lat, lng)
        velocidad_kmh = round((distancia / segundos) * 3.6, 2)

    # 1) Siempre actualizamos la "última lectura" (mapa en vivo)
    if ultima:
        ultima.co = co
        ultima.mq135 = mq135
        ultima.co_raw = co_raw
        ultima.mq135_raw = mq135_raw
        ultima.lat = lat
        ultima.lng = lng
        ultima.gps_interpolado = gps_interpolado
        ultima.velocidad_kmh = velocidad_kmh
        ultima.rumbo = rumbo
        ultima.timestamp = ahora
        if fix_valido:
            ultima.gps_ultimo_fix = ahora
    else:
        ultima = UltimaLectura(
            device_id=device_id, co=co, mq135=mq135,
            co_raw=co_raw, mq135_raw=mq135_raw,
            lat=lat, lng=lng, gps_interpolado=gps_interpolado,
            velocidad_kmh=velocidad_kmh, rumbo=rumbo,
            gps_ultimo_fix=ahora if fix_valido else None,
            timestamp=ahora,
        )
        db.session.add(ultima)

    # 2) ¿Hay un monitoreo zonal activo para este robot? Si sí, guardamos
    # CADA lectura (para trazar el recorrido) y verificamos auto-cierre.
    monitoreo_activo = (
        MonitoreoZonal.query
        .filter_by(device_id=device_id, estado="activo")
        .order_by(MonitoreoZonal.hora_inicio.desc())
        .first()
    )

    guardado_historial = False
    monitoreo_id_para_lectura = None

    if monitoreo_activo:
        if (ahora - monitoreo_activo.hora_inicio) >= DURACION_MAXIMA_MONITOREO:
            _finalizar_monitoreo(monitoreo_activo, ahora)
        else:
            monitoreo_id_para_lectura = monitoreo_activo.id

    if monitoreo_id_para_lectura:
        nueva_lectura = Lectura(
            device_id=device_id, co=co, mq135=mq135,
            co_raw=co_raw, mq135_raw=mq135_raw,
            lat=lat, lng=lng, gps_interpolado=gps_interpolado,
            velocidad_kmh=velocidad_kmh, rumbo=rumbo,
            monitoreo_id=monitoreo_id_para_lectura, timestamp=ahora,
        )
        db.session.add(nueva_lectura)
        guardado_historial = True
    else:
        # 2b) Guardado normal de historial (fuera de un monitoreo): cada 1 min
        ultimo_historial = (
            Lectura.query.filter_by(device_id=device_id, monitoreo_id=None)
            .order_by(Lectura.timestamp.desc())
            .first()
        )
        if not ultimo_historial or (ahora - ultimo_historial.timestamp) >= INTERVALO_GUARDADO:
            nueva_lectura = Lectura(
                device_id=device_id, co=co, mq135=mq135,
                co_raw=co_raw, mq135_raw=mq135_raw,
                lat=lat, lng=lng, gps_interpolado=gps_interpolado,
                velocidad_kmh=velocidad_kmh, rumbo=rumbo, timestamp=ahora,
            )
            db.session.add(nueva_lectura)
            guardado_historial = True

    db.session.commit()

    # 3) Verificar alertas y enviar correo al dueño si aplica
    alertas = []
    if co is not None and co > LIMITE_CO:
        alertas.append({"nombre": "Monóxido de carbono (CO)", "valor": round(co, 2), "unidad": "ppm", "limite": LIMITE_CO})
    if mq135 is not None and mq135 > LIMITE_MQ135:
        alertas.append({"nombre": "Gases (MQ135)", "valor": round(mq135, 2), "unidad": "ppm", "limite": LIMITE_MQ135})

    if alertas and dispositivo.usuario_id:
        puede_enviar = (
            dispositivo.ultima_alerta_enviada is None
            or (ahora - dispositivo.ultima_alerta_enviada) >= COOLDOWN_ALERTA
        )
        if puede_enviar:
            propietario = Usuario.query.get(dispositivo.usuario_id)
            if propietario:
                nombre_robot = dispositivo.nombre or dispositivo.device_id
                enviar_alerta_contaminacion(propietario.email, nombre_robot, alertas)
                dispositivo.ultima_alerta_enviada = ahora
                db.session.commit()

    return jsonify({
        "mensaje": "Datos recibidos correctamente",
        "guardado_en_historial": guardado_historial,
        "gps_interpolado": gps_interpolado,
        "monitoreo_activo": monitoreo_id_para_lectura,
    }), 201


def _finalizar_monitoreo(monitoreo, ahora):
    """Cierra automáticamente un monitoreo que excedió los 30 min y calcula
    sus métricas finales. Se usa tanto en auto-cierre como en cierre manual."""
    lecturas = (
        Lectura.query.filter_by(monitoreo_id=monitoreo.id)
        .order_by(Lectura.timestamp.asc())
        .all()
    )

    valores_co = [l.co for l in lecturas if l.co is not None]
    valores_mq135 = [l.mq135 for l in lecturas if l.mq135 is not None]
    velocidades = [l.velocidad_kmh for l in lecturas if l.velocidad_kmh is not None]

    puntos = [(l.lat, l.lng) for l in lecturas]
    centro_lat, centro_lng, radio, distancia_total = calcular_centroide_y_radio(puntos)

    promedio_co = round(sum(valores_co) / len(valores_co), 2) if valores_co else None
    promedio_mq135 = round(sum(valores_mq135) / len(valores_mq135), 2) if valores_mq135 else None
    nivel, color_hex = clasificar_nivel(promedio_co, promedio_mq135)

    monitoreo.estado = "finalizado"
    monitoreo.hora_fin = ahora
    monitoreo.lat_fin = lecturas[-1].lat if lecturas else monitoreo.lat_inicio
    monitoreo.lng_fin = lecturas[-1].lng if lecturas else monitoreo.lng_inicio
    monitoreo.promedio_co = promedio_co
    monitoreo.promedio_mq135 = promedio_mq135
    monitoreo.nivel_color = nivel
    monitoreo.color_hex = color_hex
    monitoreo.centro_lat = centro_lat
    monitoreo.centro_lng = centro_lng
    monitoreo.radio_metros = round(radio, 1) if radio else None
    monitoreo.distancia_total_m = round(distancia_total, 1)
    monitoreo.velocidad_promedio_kmh = round(sum(velocidades) / len(velocidades), 2) if velocidades else None
    monitoreo.total_puntos = len(lecturas)

    db.session.commit()
    return monitoreo


@datos_bp.route("/historial/<device_id>", methods=["GET"])
def historial(device_id):
    limite = request.args.get("limite", 100, type=int)
    lecturas = (
        Lectura.query.filter_by(device_id=device_id)
        .order_by(Lectura.timestamp.desc())
        .limit(limite)
        .all()
    )
    return jsonify([l.to_dict() for l in lecturas]), 200


@datos_bp.route("/dispositivos", methods=["GET"])
def listar_dispositivos():
    dispositivos = Dispositivo.query.all()
    resultado = []
    for d in dispositivos:
        ultima = UltimaLectura.query.filter_by(device_id=d.device_id).first()
        resultado.append({
            **d.to_dict(),
            "ultima_lectura": ultima.to_dict() if ultima else None,
        })
    return jsonify(resultado), 200
