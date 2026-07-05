from flask import Flask
from flask_cors import CORS
from config import Config
from models import db
from models.usuario import Usuario
from models.monitoreo import MonitoreoZonal  # noqa: F401 (necesario para db.create_all)

from routes.auth_routes import auth_bp
from routes.datos_routes import datos_bp
from routes.admin_routes import admin_bp
from routes.alertas_routes import alertas_bp

from routes.dispositivo_routes import dispositivo_bp
from routes.perfil_routes import perfil_bp
from routes.monitoreo_routes import monitoreo_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app, origins=["https://frontend-wally.vercel.app", "http://localhost:5173"])
    db.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(datos_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(alertas_bp)
    app.register_blueprint(dispositivo_bp)
    app.register_blueprint(perfil_bp)
    app.register_blueprint(monitoreo_bp)

    with app.app_context():
        db.create_all()
        _seed_admin_si_no_existe(app)

    return app


def _seed_admin_si_no_existe(app):
    admin_email = app.config["ADMIN_EMAIL"]
    admin_password = app.config["ADMIN_PASSWORD"]

    if not admin_email or not admin_password:
        return

    admin = Usuario.query.filter_by(email=admin_email).first()
    if not admin:
        admin = Usuario(nombre="Administrador WALLY", email=admin_email, rol="admin")
        admin.set_password(admin_password)
        admin.email_verificado = True
        db.session.add(admin)
        db.session.commit()
        print(f"Admin creado: {admin_email}")


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)