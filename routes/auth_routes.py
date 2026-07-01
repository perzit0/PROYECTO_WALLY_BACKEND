from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from models import db
from models.usuario import Usuario, CodigoVerificacion
from services.auth_service import generar_token, verificar_token
from services.email_service import generar_codigo, enviar_codigo_verificacion

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/registro", methods=["POST"])
def registro():
    data = request.get_json()
    nombre = data.get("nombre")
    email = data.get("email")
    password = data.get("password")

    if not nombre or not email or not password:
        return jsonify({"error": "Faltan campos obligatorios"}), 400

    if Usuario.query.filter_by(email=email).first():
        return jsonify({"error": "Este correo ya está registrado"}), 409

    nuevo_usuario = Usuario(nombre=nombre, email=email, rol="usuario")
    nuevo_usuario.set_password(password)

    try:
        db.session.add(nuevo_usuario)
        db.session.commit()

        codigo = generar_codigo()
        codigo_registro = CodigoVerificacion(email=email, codigo=codigo, tipo="registro")
        db.session.add(codigo_registro)
        db.session.commit()

        enviado = enviar_codigo_verificacion(email, codigo, tipo="registro")
        if not enviado:
            print(f"Advertencia: no se pudo enviar el correo a {email}")

        return jsonify({"mensaje": "Usuario registrado. Revisa tu correo para verificar tu cuenta."}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Error al registrar: {str(e)}"}), 500


@auth_bp.route("/verificar-codigo", methods=["POST"])
def verificar_codigo():
    data = request.get_json()
    email = data.get("email")
    codigo = data.get("codigo")

    registro = (
        CodigoVerificacion.query.filter_by(email=email, codigo=codigo, tipo="registro", usado=False)
        .order_by(CodigoVerificacion.creado_en.desc())
        .first()
    )

    if not registro:
        return jsonify({"error": "Código inválido"}), 400

    if datetime.utcnow() - registro.creado_en > timedelta(minutes=10):
        return jsonify({"error": "El código ha expirado"}), 400

    usuario = Usuario.query.filter_by(email=email).first()
    if not usuario:
        return jsonify({"error": "Usuario no encontrado"}), 404

    usuario.email_verificado = True
    registro.usado = True
    db.session.commit()

    return jsonify({"mensaje": "Cuenta verificada correctamente"}), 200


@auth_bp.route("/reenviar-codigo", methods=["POST"])
def reenviar_codigo():
    data = request.get_json()
    email = data.get("email")

    ultimo = (
        CodigoVerificacion.query.filter_by(email=email)
        .order_by(CodigoVerificacion.creado_en.desc())
        .first()
    )
    if ultimo and (datetime.utcnow() - ultimo.creado_en) < timedelta(seconds=30):
        return jsonify({"error": "Espera 30 segundos antes de reenviar el código"}), 429

    codigo = generar_codigo()
    nuevo = CodigoVerificacion(email=email, codigo=codigo, tipo="registro")
    db.session.add(nuevo)
    db.session.commit()

    enviar_codigo_verificacion(email, codigo, tipo="registro")
    return jsonify({"mensaje": "Código reenviado"}), 200


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    usuario = Usuario.query.filter_by(email=email).first()

    if not usuario or not usuario.check_password(password):
        return jsonify({"error": "Correo o contraseña incorrectos"}), 401

    if not usuario.email_verificado:
        return jsonify({"error": "Debes verificar tu correo antes de iniciar sesión"}), 403

    token = generar_token(usuario)

    return jsonify({
        "token": token,
        "usuario": usuario.to_dict()
    }), 200


@auth_bp.route("/olvide-password", methods=["POST"])
def olvide_password():
    data = request.get_json()
    email = data.get("email")

    usuario = Usuario.query.filter_by(email=email).first()
    if not usuario:
        # No revelar si el correo existe o no, por seguridad
        return jsonify({"mensaje": "Si el correo existe, se envió un código"}), 200

    codigo = generar_codigo()
    nuevo = CodigoVerificacion(email=email, codigo=codigo, tipo="reset_password")
    db.session.add(nuevo)
    db.session.commit()

    enviar_codigo_verificacion(email, codigo, tipo="reset_password")
    return jsonify({"mensaje": "Si el correo existe, se envió un código"}), 200


@auth_bp.route("/resetear-password", methods=["POST"])
def resetear_password():
    data = request.get_json()
    email = data.get("email")
    codigo = data.get("codigo")
    nueva_password = data.get("nueva_password")

    registro = (
        CodigoVerificacion.query.filter_by(email=email, codigo=codigo, tipo="reset_password", usado=False)
        .order_by(CodigoVerificacion.creado_en.desc())
        .first()
    )

    if not registro:
        return jsonify({"error": "Código inválido"}), 400

    if datetime.utcnow() - registro.creado_en > timedelta(minutes=10):
        return jsonify({"error": "El código ha expirado"}), 400

    usuario = Usuario.query.filter_by(email=email).first()
    if not usuario:
        return jsonify({"error": "Usuario no encontrado"}), 404

    usuario.set_password(nueva_password)
    registro.usado = True
    db.session.commit()

    return jsonify({"mensaje": "Contraseña actualizada correctamente"}), 200


@auth_bp.route("/me", methods=["GET"])
def me():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"error": "Token no proporcionado"}), 401

    token = auth_header.split(" ")[1]
    payload = verificar_token(token)
    if not payload:
        return jsonify({"error": "Token inválido o expirado"}), 401

    usuario = Usuario.query.get(payload["id"])
    if not usuario:
        return jsonify({"error": "Usuario no encontrado"}), 404

    return jsonify({"usuario": usuario.to_dict()}), 200