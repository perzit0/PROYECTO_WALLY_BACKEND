import os
import json
import threading
import urllib.request

# Servidor y canal de ntfy.sh para mandar notificaciones push al celular.
# El celular debe tener instalada la app ntfy (Play Store / F-Droid) y estar
# suscrito al mismo topic. Si NTFY_TOPIC no está configurado, el push se
# desactiva silenciosamente (el resto del backend sigue funcionando igual).
NTFY_SERVER = os.getenv("NTFY_SERVER", "https://ntfy.sh")
NTFY_TOPIC = os.getenv("NTFY_TOPIC")

# Claves VAPID para web push: alarmas que llegan DENTRO de la app WALLY
# (PWA) sin necesidad de ntfy. Si faltan, el web push queda desactivado.
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY")
VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY")
VAPID_CLAIM_EMAIL = os.getenv("VAPID_CLAIM_EMAIL", "admin@wally.app")


def enviar_push(titulo, mensaje, prioridad=5, tags=None):
    """Envía una notificación push al celular vía ntfy.

    prioridad 5 = máxima: en la app ntfy dispara sonido de alarma y
    vibración aunque el teléfono esté en silencio (si el usuario activó
    "Insistent max priority" en los ajustes de la app).

    El envío se hace en un hilo aparte para no demorar la respuesta al
    dispositivo que está mandando las lecturas.
    """
    if not NTFY_TOPIC:
        return

    payload = {
        "topic": NTFY_TOPIC,
        "title": titulo,
        "message": mensaje,
        "priority": prioridad,
        "tags": tags or ["rotating_light"],
    }

    hilo = threading.Thread(target=_enviar, args=(payload,), daemon=True)
    hilo.start()


def _enviar(payload):
    try:
        req = urllib.request.Request(
            NTFY_SERVER,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
    except Exception as e:
        # Un fallo del push nunca debe tumbar la recepción de datos
        print(f"Error enviando push ntfy: {e}")


def enviar_webpush_a_todos(titulo, mensaje, tag="wally-alarma"):
    """Manda una notificación web push a TODOS los celulares que activaron
    las alarmas dentro de la app WALLY. Debe llamarse dentro de un request
    (usa la sesión de BD); el envío real ocurre en un hilo aparte.

    Las suscripciones muertas (celular que desinstaló la app, permiso
    revocado) devuelven 404/410 y se eliminan automáticamente."""
    if not VAPID_PRIVATE_KEY:
        return

    from flask import current_app
    from models.push_suscripcion import PushSuscripcion

    subs = [(s.id, s.to_subscription_info()) for s in PushSuscripcion.query.all()]
    if not subs:
        return

    app = current_app._get_current_object()
    hilo = threading.Thread(
        target=_enviar_webpush, args=(app, subs, titulo, mensaje, tag), daemon=True
    )
    hilo.start()


def _enviar_webpush(app, subs, titulo, mensaje, tag):
    from pywebpush import webpush, WebPushException

    datos = json.dumps({"title": titulo, "body": mensaje, "tag": tag})
    muertas = []

    for sub_id, info in subs:
        try:
            webpush(
                subscription_info=info,
                data=datos,
                vapid_private_key=VAPID_PRIVATE_KEY,
                # dict nuevo en cada envío: pywebpush lo muta (agrega aud/exp)
                vapid_claims={"sub": f"mailto:{VAPID_CLAIM_EMAIL}"},
                ttl=300,
            )
        except WebPushException as e:
            status = e.response.status_code if e.response is not None else None
            if status in (404, 410):
                muertas.append(sub_id)
            else:
                print(f"Error web push (sub {sub_id}): {e}")
        except Exception as e:
            print(f"Error web push (sub {sub_id}): {e}")

    if muertas:
        with app.app_context():
            from models import db
            from models.push_suscripcion import PushSuscripcion
            PushSuscripcion.query.filter(PushSuscripcion.id.in_(muertas)).delete(
                synchronize_session=False
            )
            db.session.commit()
