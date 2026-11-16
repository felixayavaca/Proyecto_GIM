from flask import Blueprint, current_app, flash, render_template
from controllers.funciones_home import obtener_resumen
from routers.router_login import login_requerido

home_bp = Blueprint('home', __name__)


@home_bp.get('/dashboard')
@login_requerido
def dashboard():
    try:
        resumen = obtener_resumen()
    except ConnectionError:
        current_app.logger.error('No se pudo consultar el resumen en MySQL.')
        flash('No se pudo cargar el resumen. Inténtalo más tarde.', 'danger')
        return render_template('home/dashboard.html', resumen=None), 503
    return render_template('home/dashboard.html', resumen=resumen)
