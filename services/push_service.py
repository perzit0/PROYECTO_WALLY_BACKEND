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
