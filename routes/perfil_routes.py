from flask import Blueprint, request, jsonify, send_file
from models import db
from models.usuario import Usuario
from models.dispositivo import Dispositivo
from models.lectura import Lectura
from services.auth_service import verificar_token
from services.export_service import exportar_historial_excel
from datetime import datetime, timedelta
from models.usuario import CodigoVerificacion
from services.email_service import generar_codigo, enviar_codigo_verificacion

perfil_bp = Blueprint("perfil", __name__, url_prefix="/api/perfil")


def usuario_actual():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ")[1]
    payload = verificar_token(token)
    if not payload:
        return None
    return Usuario.query.get(payload["id"])


@perfil_bp.route("/actualizar-nombre", methods=["PUT"])
def actualizar_nombre():
    usuario = usuario_actual()
    if not usuario:
        return jsonify({"error": "Debes iniciar sesión"}), 401

    data = request.get_json()
    nombre = data.get("nombre", "").strip()

    if not nombre or len(nombre) < 2:
        return jsonify({"error": "El nombre debe tener al menos 2 caracteres"}), 400

    usuario.nombre = nombre[:100]
    db.session.commit()

    return jsonify({"mensaje": "Nombre actualizado", "usuario": usuario.to_dict()}), 200


@perfil_bp.route("/solicitar-cambio-password", methods=["POST"])
def solicitar_cambio_password():
    usuario = usuario_actual()
    if not usuario:
        return jsonify({"error": "Debes iniciar sesión"}), 401

    codigo = generar_codigo()
    nuevo_codigo = CodigoVerificacion(email=usuario.email, codigo=codigo, tipo="cambio_password")
    db.session.add(nuevo_codigo)
    db.session.commit()

    enviar_codigo_verificacion(usuario.email, codigo, tipo="reset_password")

    return jsonify({"mensaje": "Código enviado a tu correo"}), 200


@perfil_bp.route("/confirmar-cambio-password", methods=["PUT"])
def confirmar_cambio_password():
    usuario = usuario_actual()
    if not usuario:
        return jsonify({"error": "Debes iniciar sesión"}), 401

    data = request.get_json()
    codigo = data.get("codigo", "")
    password_actual = data.get("password_actual", "")
    password_nueva = data.get("password_nueva", "")

    registro = (
        CodigoVerificacion.query.filter_by(
            email=usuario.email, codigo=codigo, tipo="cambio_password", usado=False
        )
        .order_by(CodigoVerificacion.creado_en.desc())
        .first()
    )

    if not registro:
        return jsonify({"error": "Código inválido"}), 400

    if datetime.utcnow() - registro.creado_en > timedelta(minutes=10):
        return jsonify({"error": "El código ha expirado"}), 400

    if not usuario.check_password(password_actual):
        return jsonify({"error": "La contraseña actual es incorrecta"}), 401

    if len(password_nueva) < 6:
        return jsonify({"error": "La nueva contraseña debe tener al menos 6 caracteres"}), 400

    usuario.set_password(password_nueva)
    registro.usado = True
    db.session.commit()

    return jsonify({"mensaje": "Contraseña actualizada correctamente"}), 200


@perfil_bp.route("/exportar/<device_id>", methods=["GET"])
def exportar_mis_datos(device_id):
    usuario = usuario_actual()
    if not usuario:
        return jsonify({"error": "Debes iniciar sesión"}), 401

    dispositivo = Dispositivo.query.filter_by(device_id=device_id).first()
    if not dispositivo:
        return jsonify({"error": "Robot no encontrado"}), 404

    if dispositivo.usuario_id != usuario.id and usuario.rol != "admin":
        return jsonify({"error": "No tienes permiso para exportar este robot"}), 403

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