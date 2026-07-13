from models import db
from datetime import datetime


class PushSuscripcion(db.Model):
    """Suscripción web push de un navegador/celular con la app WALLY.
    Cada celular que activa las alarmas dentro de la app genera una fila.
    Si el envío devuelve 404/410 la suscripción murió y se elimina."""
    __tablename__ = "push_suscripciones"

    id = db.Column(db.Integer, primary_key=True)
    endpoint = db.Column(db.Text, nullable=False, unique=True)
    p256dh = db.Column(db.Text, nullable=False)
    auth = db.Column(db.Text, nullable=False)
    creado = db.Column(db.DateTime, default=datetime.utcnow)

    def to_subscription_info(self):
        return {
            "endpoint": self.endpoint,
            "keys": {"p256dh": self.p256dh, "auth": self.auth},
        }
