import jwt
from datetime import datetime, timedelta
from flask import current_app


def generar_token(usuario):
    payload = {
        "id": usuario.id,
        "email": usuario.email,
        "rol": usuario.rol,
        "exp": datetime.utcnow() + timedelta(
            hours=current_app.config["JWT_EXPIRATION_HOURS"]
        ),
    }
    return jwt.encode(payload, current_app.config["JWT_SECRET_KEY"], algorithm="HS256")


def verificar_token(token):
    try:
        payload = jwt.decode(
            token, current_app.config["JWT_SECRET_KEY"], algorithms=["HS256"]
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None