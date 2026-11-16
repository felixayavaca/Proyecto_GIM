from flask import Blueprint, flash, redirect, render_template, request, url_for
from controllers.funciones_socios import (
    ErrorSocios, listar_socios, crear_socio, actualizar_socio, eliminar_socio,
)
from routers.router_login import requiere_permiso, validar_csrf

socios_bp = Blueprint('socios', __name__)


@socios_bp.get('/socios')
@requiere_permiso('socios.ver')
def lista():
    try:
        socios = listar_socios()
    except ErrorSocios as exc:
        flash(str(exc), 'danger')
        return render_template('socios/lista_socios.html', socios=[], disponible=False), 503
    return render_template('socios/lista_socios.html', socios=socios, disponible=True)


def _guardar(operacion, mensaje, *args):
    validar_csrf()
    try:
        operacion(*args)
        flash(mensaje, 'success')
    except ErrorSocios as exc:
        flash(str(exc), 'danger')
    return redirect(url_for('socios.lista'))


@socios_bp.post('/socios/crear')
@requiere_permiso('socios.gestionar')
def crear():
    return _guardar(crear_socio, 'Socio creado correctamente.', request.form)


@socios_bp.post('/socios/editar/<int:socio_id>')
@requiere_permiso('socios.gestionar')
def editar(socio_id):
    return _guardar(actualizar_socio, 'Socio actualizado correctamente.', socio_id, request.form)


@socios_bp.post('/socios/eliminar/<int:socio_id>')
@requiere_permiso('socios.gestionar')
def eliminar(socio_id):
    return _guardar(eliminar_socio, 'Socio eliminado correctamente.', socio_id)
