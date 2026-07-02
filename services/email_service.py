import smtplib
import random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app


def generar_codigo():
    return str(random.randint(100000, 999999))


def enviar_correo(destinatario, asunto, cuerpo_html):
    remitente = current_app.config["GMAIL_USER"]
    password = current_app.config["GMAIL_APP_PASSWORD"]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = asunto
    msg["From"] = remitente
    msg["To"] = destinatario
    msg.attach(MIMEText(cuerpo_html, "html"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(remitente, password)
            server.sendmail(remitente, destinatario, msg.as_string())
        return True
    except Exception as e:
        print(f"Error enviando correo: {e}")
        return False


def enviar_codigo_verificacion(destinatario, codigo, tipo="registro"):
    if tipo == "registro":
        asunto = "WALLY - Código de verificación"
        titulo = "Verifica tu cuenta"
    else:
        asunto = "WALLY - Recuperar contraseña"
        titulo = "Restablece tu contraseña"

    cuerpo_html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 500px; margin: auto;">
        <h2>{titulo}</h2>
        <p>Tu código de verificación es:</p>
        <h1 style="letter-spacing: 5px;">{codigo}</h1>
        <p>Este código expira en 10 minutos.</p>
    </div>
    """
    return enviar_correo(destinatario, asunto, cuerpo_html)

def enviar_alerta_contaminacion(destinatario, nombre_robot, alertas):
    asunto = f"⚠️ CUIDADO - {nombre_robot} detectó niveles altos"

    lista_html = "".join([
        f"<li><strong>{a['nombre']}</strong>: {a['valor']} {a['unidad']} (límite: {a['limite']} {a['unidad']})</li>"
        for a in alertas
    ])

    cuerpo_html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 500px; margin: auto;">
        <h2 style="color: #dc2626;">⚠️ Alerta de calidad del aire</h2>
        <p>Tu robot <strong>{nombre_robot}</strong> detectó niveles altos de contaminación:</p>
        <ul>{lista_html}</ul>
        <p style="font-size: 13px; color: #6b7280;">
            Revisa el mapa en tiempo real en la aplicación WALLY para más detalles.
        </p>
    </div>
    """
    return enviar_correo(destinatario, asunto, cuerpo_html)