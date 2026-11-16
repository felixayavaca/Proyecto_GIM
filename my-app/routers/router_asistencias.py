from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from controllers.funciones_asistencias import (
    ErrorAsistencias, listar_asistencias, registrar_asistencia, eliminar_asistencia,
)
from controllers.funciones_socios import ErrorSocios, listar_socios
from routers.router_login import requiere_permiso, validar_csrf

asistencias_bp = Blueprint('asistencias', __name__)


@asistencias_bp.get('/asistencias')
@requiere_permiso('asistencias.ver')
def lista():
    try:
        asistencias = listar_asistencias()
        socios = listar_socios() if 'asistencias.registrar' in session['usuario']['permisos'] else []
    except (ErrorAsistencias, ErrorSocios) as exc:
        flash(str(exc), 'danger')
        return render_template('asistencias/control_asistencias.html', disponible=False), 503
    return render_template('asistencias/control_asistencias.html', disponible=True,
                           asistencias=asistencias, socios=socios)


@asistencias_bp.post('/asistencias/registrar')
@requiere_permiso('asistencias.registrar')
def registrar():
    validar_csrf()
    try:
        exito, mensaje = registrar_asistencia(request.form.get('socio_id'), session['usuario']['id'])
        categoria = 'warning' if 'ADVERTENCIA' in mensaje else 'success'
        flash(mensaje, categoria if exito else 'danger')
    except ErrorAsistencias as exc:
        flash(str(exc), 'danger')
    return redirect(url_for('asistencias.lista'))


@asistencias_bp.post('/asistencias/eliminar/<int:asistencia_id>')
@requiere_permiso('asistencias.registrar')
def eliminar(asistencia_id):
    validar_csrf()
    try:
        eliminar_asistencia(asistencia_id)
        flash('Asistencia eliminada correctamente.', 'success')
    except ErrorAsistencias as exc:
        flash(str(exc), 'danger')
    return redirect(url_for('asistencias.lista'))
