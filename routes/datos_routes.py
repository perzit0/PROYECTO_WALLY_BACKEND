from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from models import db
from models.lectura import Lectura, UltimaLectura
from models.dispositivo import Dispositivo

datos_bp = Blueprint("datos", __name__, url_prefix="/api")

INTERVALO_GUARDADO = timedelta(minutes=30)


@datos_bp.route("/datos", methods=["POST"])
def recibir_datos():
    data = request.get_json()
    device_id = data.get("device_id")

    if not device_id:
        return jsonify({"error": "device_id es obligatorio"}), 400

    # Registrar dispositivo si no existe
    dispositivo = Dispositivo.query.filter_by(device_id=device_id).first()
    if not dispositivo:
        dispositivo = Dispositivo(device_id=device_id)
        db.session.add(dispositivo)

    co = data.get("co")
    mq135 = data.get("mq135")
    pm = data.get("pm")

# Plaza Dos de Mayo, Lima - coordenadas por defecto mientras el GPS obtiene fix
    lat = data.get("lat") or -12.055100
    lng = data.get("lng") or -77.047900 
    ahora = datetime.utcnow()

    # 1) Siempre actualizamos la "última lectura" (mapa en vivo)
    ultima = UltimaLectura.query.filter_by(device_id=device_id).first()
    if ultima:
        ultima.co = co
        ultima.mq135 = mq135
        ultima.pm = pm
        ultima.lat = lat
        ultima.lng = lng
        ultima.timestamp = ahora
    else:
        ultima = UltimaLectura(
            device_id=device_id, co=co, mq135=mq135, pm=pm, lat=lat, lng=lng, timestamp=ahora
        )
        db.session.add(ultima)

    # 2) Solo guardamos en el historial si pasaron 30 min desde el último guardado
    ultimo_historial = (
        Lectura.query.filter_by(device_id=device_id)
        .order_by(Lectura.timestamp.desc())
        .first()
    )

    guardado_historial = False
    if not ultimo_historial or (ahora - ultimo_historial.timestamp) >= INTERVALO_GUARDADO:
        nueva_lectura = Lectura(
            device_id=device_id, co=co, mq135=mq135, pm=pm, lat=lat, lng=lng, timestamp=ahora
        )
        db.session.add(nueva_lectura)
        guardado_historial = True

    db.session.commit()

    return jsonify({
        "mensaje": "Datos recibidos correctamente",
        "guardado_en_historial": guardado_historial,
    }), 201


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