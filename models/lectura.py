from models import db
from datetime import datetime

class Lectura(db.Model):
    __tablename__ = "lecturas"

    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(50), nullable=False)
    co = db.Column(db.Float, nullable=True)
    mq135 = db.Column(db.Float, nullable=True)
    pm = db.Column(db.Float, nullable=True)
    lat = db.Column(db.Float, nullable=True)
    lng = db.Column(db.Float, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "device_id": self.device_id,
            "co": self.co,
            "mq135": self.mq135,
            "pm": self.pm,
            "lat": self.lat,
            "lng": self.lng,
            "timestamp": self.timestamp.isoformat() + "Z",
        }


class UltimaLectura(db.Model):
    """Guarda solo el dato más reciente por dispositivo, se sobrescribe siempre.
    Sirve para el mapa en vivo sin llenar la tabla de historial."""
    __tablename__ = "ultima_lectura"

    device_id = db.Column(db.String(50), primary_key=True)
    co = db.Column(db.Float, nullable=True)
    mq135 = db.Column(db.Float, nullable=True)
    pm = db.Column(db.Float, nullable=True)
    lat = db.Column(db.Float, nullable=True)
    lng = db.Column(db.Float, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "device_id": self.device_id,
            "co": self.co,
            "mq135": self.mq135,
            "pm": self.pm,
            "lat": self.lat,
            "lng": self.lng,
            "timestamp": self.timestamp.isoformat() + "Z",
        }