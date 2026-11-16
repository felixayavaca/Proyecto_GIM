import os
from datetime import timedelta
from flask import Flask, render_template
from routers.router_login import csrf_token, login_bp
from routers.router_home import home_bp
from routers.router_socios import socios_bp
from routers.router_membresias import membresias_bp
from routers.router_asistencias import asistencias_bp
from routers.router_instructores import instructores_bp
from routers.router_planes import planes_bp
from routers.router_entrenadores import entrenadores_bp

app = Flask(__name__, template_folder='templates/public', static_folder='static')
app.config.update(
    SECRET_KEY=os.environ['SECRET_KEY'],
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() == 'true',
    PERMANENT_SESSION_LIFETIME=timedelta(minutes=30),
    MAX_CONTENT_LENGTH=16 * 1024,
)
app.jinja_env.globals['csrf_token'] = csrf_token
app.register_blueprint(login_bp)
app.register_blueprint(home_bp)
app.register_blueprint(socios_bp)
app.register_blueprint(membresias_bp)
app.register_blueprint(asistencias_bp)
app.register_blueprint(instructores_bp)
app.register_blueprint(planes_bp)
app.register_blueprint(entrenadores_bp)


@app.after_request
def proteger_respuesta(response):
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    return response


@app.errorhandler(403)
def acceso_denegado(error):
    return render_template('base_cpanel.html', acceso_denegado=True), 403
