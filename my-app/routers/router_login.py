from functools import wraps
import secrets
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, session, url_for
from controllers.funciones_login import validar_usuario

login_bp = Blueprint('login', __name__)


def login_requerido(vista):
    @wraps(vista)
    def protegida(*args, **kwargs):
        if not session.get('usuario'):
            flash('Inicia sesión para continuar.', 'warning')
            return redirect(url_for('login.login'))
        return vista(*args, **kwargs)
    return protegida


def requiere_permiso(clave_permiso):
    def decorar(vista):
        @wraps(vista)
        @login_requerido
        def protegida(*args, **kwargs):
            if clave_permiso not in session['usuario'].get('permisos', []):
                flash('No tienes permiso para realizar esta acción.', 'danger')
                abort(403)
            return vista(*args, **kwargs)
        return protegida
    return decorar


def csrf_token():
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(32)
    return session['csrf_token']


def validar_csrf():
    esperado = session.get('csrf_token')
    recibido = request.form.get('csrf_token', '')
    if not esperado or not secrets.compare_digest(esperado, recibido):
        abort(400, description='Formulario vencido o inválido. Recarga la página.')


@login_bp.get('/')
def inicio():
    return redirect(url_for('home.dashboard' if session.get('usuario') else 'login.login'))


@login_bp.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('usuario'):
        return redirect(url_for('home.dashboard'))
    if request.method == 'POST':
        validar_csrf()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        if not email or not password or len(email) > 120 or len(password) > 1024:
            flash('Introduce un correo y una contraseña válidos.', 'danger')
        else:
            try:
                usuario = validar_usuario(email, password)
            except ConnectionError:
                current_app.logger.error('No se pudo consultar la autenticación en MySQL.')
                flash('Servicio no disponible. Inténtalo más tarde.', 'danger')
                return render_template('login/login.html'), 503
            if usuario:
                session.clear()
                session['usuario'] = usuario
                session.permanent = True
                return redirect(url_for('home.dashboard'))
            flash('Credenciales incorrectas o usuario inactivo.', 'danger')
    return render_template('login/login.html')


@login_bp.post('/logout')
@login_requerido
def logout():
    validar_csrf()
    session.clear()
    flash('Sesión cerrada correctamente.', 'success')
    return redirect(url_for('login.login'))
