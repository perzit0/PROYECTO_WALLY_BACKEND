import statistics
from flask import Blueprint, request, jsonify, send_file
from functools import wraps
from models import db
from models.usuario import Usuario
from models.dispositivo import Dispositivo
from models.lectura import Lectura, UltimaLectura
from services.auth_service import verificar_token
from services.export_service import exportar_historial_excel, exportar_usuarios_excel

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


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


@admin_bp.route("/resumen", methods=["GET"])
@requiere_admin
def resumen():
    total_usuarios = Usuario.query.count()
    total_dispositivos = Dispositivo.query.count()
    total_lecturas = Lectura.query.count()

    return jsonify({
        "total_usuarios": total_usuarios,
        "total_dispositivos": total_dispositivos,
        "total_lecturas": total_lecturas,
    }), 200


@admin_bp.route("/usuarios", methods=["GET"])
@requiere_admin
def listar_usuarios():
    usuarios = Usuario.query.all()
    return jsonify([u.to_dict() for u in usuarios]), 200


@admin_bp.route("/dispositivos", methods=["GET"])
@requiere_admin
def listar_dispositivos_admin():
    dispositivos = Dispositivo.query.all()
    return jsonify([d.to_dict() for d in dispositivos]), 200


@admin_bp.route("/graficos/<device_id>", methods=["GET"])
@requiere_admin
def graficos(device_id):
    limite = request.args.get("limite", 200, type=int)
    lecturas = (
        Lectura.query.filter_by(device_id=device_id)
        .order_by(Lectura.timestamp.asc())
        .limit(limite)
        .all()
    )
    return jsonify([l.to_dict() for l in lecturas]), 200


@admin_bp.route("/metricas-adc/<device_id>", methods=["GET"])
@requiere_admin
def metricas_adc(device_id):
    limite = request.args.get("limite", 50, type=int)
    lecturas = (
        Lectura.query.filter_by(device_id=device_id)
        .order_by(Lectura.timestamp.desc())
        .limit(limite)
        .all()
    )

    def calcular_stats(valores):
        valores_validos = [v for v in valores if v is not None]
        if not valores_validos:
            return None
        return {
            "media": round(statistics.mean(valores_validos), 1),
            "minimo": min(valores_validos),
            "maximo": max(valores_validos),
            "desviacion_estandar": round(statistics.pstdev(valores_validos), 2) if len(valores_validos) > 1 else 0,
            "muestras": len(valores_validos),
        }

    co_raw = [l.co_raw for l in lecturas]
    mq135_raw = [l.mq135_raw for l in lecturas]

    return jsonify({
        "device_id": device_id,
        "mq7": calcular_stats(co_raw),
        "mq135": calcular_stats(mq135_raw),
    }), 200


@admin_bp.route("/exportar/historial/<device_id>", methods=["GET"])
@requiere_admin
def exportar_historial(device_id):
    lecturas = (
        Lectura.query.filter_by(device_id=device_id)
        .order_by(Lectura.timestamp.desc())
        .all()
    )
    buffer = exportar_historial_excel(lecturas, device_id)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"historial_{device_id}.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@admin_bp.route("/exportar/usuarios", methods=["GET"])
@requiere_admin
def exportar_usuarios():
    usuarios = Usuario.query.all()
    buffer = exportar_usuarios_excel(usuarios)
    return send_file(
        buffer,
        as_attachment=True,
        download_name="usuarios_wally.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )