from models import db
from datetime import datetime


class MonitoreoZonal(db.Model):
    """Representa una sesión de 'monitoreo zonal': un recorrido a pie/vehículo
    donde se etiquetan las lecturas del robot para trazar el camino en el mapa,
    calcular promedios y marcar una zona con su nivel de calidad de aire."""
    __tablename__ = "monitoreos_zonales"

    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(50), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    nombre = db.Column(db.String(150), nullable=True)  # ej: "Miraflores - Av. Larco"

    estado = db.Column(db.String(20), nullable=False, default="activo")  # activo | finalizado

    hora_inicio = db.Column(db.DateTime, default=datetime.utcnow)
    hora_fin = db.Column(db.DateTime, nullable=True)

    lat_inicio = db.Column(db.Float, nullable=True)
    lng_inicio = db.Column(db.Float, nullable=True)
    lat_fin = db.Column(db.Float, nullable=True)
    lng_fin = db.Column(db.Float, nullable=True)

    # Resultados calculados al finalizar
    promedio_co = db.Column(db.Float, nullable=True)
    promedio_mq135 = db.Column(db.Float, nullable=True)
    promedio_pm = db.Column(db.Float, nullable=True)
    nivel_color = db.Column(db.String(20), nullable=True)  # bueno | moderado | malo | critico
    color_hex = db.Column(db.String(7), nullable=True)

    centro_lat = db.Column(db.Float, nullable=True)
    centro_lng = db.Column(db.Float, nullable=True)
    radio_metros = db.Column(db.Float, nullable=True)
    distancia_total_m = db.Column(db.Float, nullable=True)
    velocidad_promedio_kmh = db.Column(db.Float, nullable=True)
    total_puntos = db.Column(db.Integer, default=0)

    def to_dict(self):
        return {
            "id": self.id,
            "device_id": self.device_id,
            "usuario_id": self.usuario_id,
            "nombre": self.nombre,
            "estado": self.estado,
            "hora_inicio": self.hora_inicio.isoformat() + "Z" if self.hora_inicio else None,
            "hora_fin": self.hora_fin.isoformat() + "Z" if self.hora_fin else None,
            "lat_inicio": self.lat_inicio,
            "lng_inicio": self.lng_inicio,
            "lat_fin": self.lat_fin,
            "lng_fin": self.lng_fin,
            "promedio_co": self.promedio_co,
            "promedio_mq135": self.promedio_mq135,
            "promedio_pm": self.promedio_pm,
            "nivel_color": self.nivel_color,
            "color_hex": self.color_hex,
            "centro_lat": self.centro_lat,
            "centro_lng": self.centro_lng,
            "radio_metros": self.radio_metros,
            "distancia_total_m": self.distancia_total_m,
            "velocidad_promedio_kmh": self.velocidad_promedio_kmh,
            "total_puntos": self.total_puntos,
        }
