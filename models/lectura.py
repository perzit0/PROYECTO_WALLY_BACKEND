from models import db
from datetime import datetime


class Lectura(db.Model):
    __tablename__ = "lecturas"

    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(50), nullable=False)
    co = db.Column(db.Float, nullable=True)
    mq135 = db.Column(db.Float, nullable=True)
    pm = db.Column(db.Float, nullable=True)
    co_raw = db.Column(db.Integer, nullable=True)
    mq135_raw = db.Column(db.Integer, nullable=True)
    pm_raw = db.Column(db.Integer, nullable=True)
    lat = db.Column(db.Float, nullable=True)
    lng = db.Column(db.Float, nullable=True)
    gps_interpolado = db.Column(db.Boolean, default=False, nullable=False)
    velocidad_kmh = db.Column(db.Float, nullable=True)
    rumbo = db.Column(db.Float, nullable=True)
    monitoreo_id = db.Column(db.Integer, db.ForeignKey("monitoreos_zonales.id"), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "device_id": self.device_id,
            "co": self.co,
            "mq135": self.mq135,
            "pm": self.pm,
            "co_raw": self.co_raw,
            "mq135_raw": self.mq135_raw,
            "pm_raw": self.pm_raw,
            "lat": self.lat,
            "lng": self.lng,
            "gps_interpolado": self.gps_interpolado,
            "velocidad_kmh": self.velocidad_kmh,
            "rumbo": self.rumbo,
            "monitoreo_id": self.monitoreo_id,
            "timestamp": self.timestamp.isoformat() + "Z",
        }


class UltimaLectura(db.Model):
    """Guarda solo el dato más reciente por dispositivo, se sobrescribe siempre.
    Sirve para el mapa en vivo sin llenar la tabla de historial.
    lat/lng representan la última ubicación CONOCIDA (real o heredada si se
    perdió señal GPS), nunca un valor inventado."""
    __tablename__ = "ultima_lectura"

    device_id = db.Column(db.String(50), primary_key=True)
    co = db.Column(db.Float, nullable=True)
    mq135 = db.Column(db.Float, nullable=True)
    pm = db.Column(db.Float, nullable=True)
    co_raw = db.Column(db.Integer, nullable=True)
    mq135_raw = db.Column(db.Integer, nullable=True)
    pm_raw = db.Column(db.Integer, nullable=True)
    lat = db.Column(db.Float, nullable=True)
    lng = db.Column(db.Float, nullable=True)
    gps_interpolado = db.Column(db.Boolean, default=False, nullable=False)
    gps_ultimo_fix = db.Column(db.DateTime, nullable=True)  # última vez que hubo señal real
    velocidad_kmh = db.Column(db.Float, nullable=True)
    rumbo = db.Column(db.Float, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "device_id": self.device_id,
            "co": self.co,
            "mq135": self.mq135,
            "pm": self.pm,
            "co_raw": self.co_raw,
            "mq135_raw": self.mq135_raw,
            "pm_raw": self.pm_raw,
            "lat": self.lat,
            "lng": self.lng,
            "gps_interpolado": self.gps_interpolado,
            "gps_ultimo_fix": self.gps_ultimo_fix.isoformat() + "Z" if self.gps_ultimo_fix else None,
            "velocidad_kmh": self.velocidad_kmh,
            "rumbo": self.rumbo,
            "timestamp": self.timestamp.isoformat() + "Z",
        }
