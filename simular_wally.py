"""
SIMULADOR DE WALLY — solo para probar la alarma en el celular.

Hace de robot falso: manda una lectura normal y enseguida una lectura con
salto brusco de CO y MQ-135, lo que dispara la alarma push (ntfy) en tu
celular. NO toca la base de datos real: usa una base SQLite temporal que
se borra sola al terminar. La notificación push sí es real.

Uso (desde la carpeta del proyecto):
    venv\\Scripts\\python simular_wally.py

Cuando termines de probar, simplemente borra este archivo.
"""

import os
import time
import tempfile

# IMPORTANTE: apuntar a una base temporal ANTES de importar la app,
# para no escribir datos falsos en la base de producción (Supabase).
_db_temporal = os.path.join(tempfile.gettempdir(), "wally_simulador.db")
os.environ["DATABASE_URL"] = "sqlite:///" + _db_temporal.replace("\\", "/")
os.environ["ADMIN_EMAIL"] = ""  # no crear admin en la base temporal

from app import create_app  # noqa: E402


def main():
    print("=" * 60)
    print("  SIMULADOR DE WALLY - prueba de alarma en el celular")
    print("=" * 60)

    app = create_app()
    client = app.test_client()

    # 1) Lectura normal (aire limpio)
    print("\n[1/2] Enviando lectura NORMAL (CO: 5 ppm, MQ-135: 150 ppm)...")
    r = client.post("/api/datos", json={
        "device_id": "WALLY_SIMULADO",
        "co": 5.0,
        "mq135": 150.0,
    })
    print(f"      Respuesta del backend: {r.status_code}")

    time.sleep(2)

    # 2) Salto brusco (como si acercaras humo a los sensores)
    print("[2/2] Enviando lectura con SALTO BRUSCO (CO: 45 ppm, MQ-135: 600 ppm)...")
    r = client.post("/api/datos", json={
        "device_id": "WALLY_SIMULADO",
        "co": 45.0,
        "mq135": 600.0,
    })
    print(f"      Respuesta del backend: {r.status_code}")

    # Dar tiempo a que el hilo del push termine de enviar a ntfy.sh
    print("\nEnviando alarma a tu celular...")
    time.sleep(4)

    print("Listo. Tu celular deberia estar sonando/vibrando ahora mismo")
    print('con la notificacion "Variacion brusca - WALLY_SIMULADO".')
    print("\nSi no sono, revisa que en la app ntfy estes suscrito a:")
    print("    wally-alertas-f1d4f6b1f961")

    # Ademas, probar la alarma INTEGRADA en la app WALLY (web push) en
    # produccion: suena en todos los celulares que tocaron "Activar
    # alarmas" dentro de la app.
    print("\nProbando tambien la alarma integrada en la app WALLY...")
    import json
    import urllib.request
    try:
        req = urllib.request.Request(
            "https://proyecto-wally-backend.onrender.com/api/push/probar",
            data=b"{}", headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            print("      " + json.loads(resp.read()).get("mensaje", "OK"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print("      Ningun celular tiene las alarmas activadas dentro de la app")
            print("      (abre la app WALLY y toca el boton 'Activar alarmas').")
        elif e.code == 503:
            print("      El servidor de Render aun no tiene las claves VAPID configuradas.")
        else:
            print(f"      Error del servidor: {e.code}")
    except Exception as e:
        print(f"      No se pudo contactar al servidor de Render: {e}")

    print("\nPuedes volver a ejecutar este script las veces que quieras.")


if __name__ == "__main__":
    try:
        main()
    finally:
        # Borrar la base temporal para no dejar rastro
        try:
            os.remove(_db_temporal)
        except OSError:
            pass
