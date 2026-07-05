from models import db
from datetime import datetime
import bcrypt

class Usuario(db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(20), nullable=False, default="usuario")  # "usuario" o "admin"
    email_verificado = db.Column(db.Boolean, default=False)
    foto_base64 = db.Column(db.Text, nullable=True)  # imagen pequeña en base64 (data URL)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

    def check_password(self, password):
        return bcrypt.checkpw(
            password.encode("utf-8"), self.password_hash.encode("utf-8")
        )

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "email": self.email,
            "rol": self.rol,
            "email_verificado": self.email_verificado,
            "foto_base64": self.foto_base64,
        }


class CodigoVerificacion(db.Model):
    __tablename__ = "codigos_verificacion"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    codigo = db.Column(db.String(6), nullable=False)
    tipo = db.Column(db.String(30), nullable=False)  # "registro" o "reset_password"
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    usado = db.Column(db.Boolean, default=False)