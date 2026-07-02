from models import db
from datetime import datetime

class Dispositivo(db.Model):
    __tablename__ = "dispositivos"

    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(50), unique=True, nullable=False)
    nombre = db.Column(db.String(100), nullable=True)
    color = db.Column(db.String(7), nullable=False, default="#38bdf8")
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    ultima_alerta_enviada = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "device_id": self.device_id,
            "nombre": self.nombre,
            "color": self.color,
            "usuario_id": self.usuario_id,
            "creado_en": self.creado_en.isoformat() + "Z" if self.creado_en else None,
        }