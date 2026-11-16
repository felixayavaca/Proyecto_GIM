from flask import Blueprint, flash, redirect, render_template, request, url_for
from controllers.funciones_membresias import (
    ErrorMembresias, listar_membresias, listar_planes, crear_plan,
    crear_membresia, cambiar_estado_membresia, eliminar_membresia,
)
from controllers.funciones_socios import ErrorSocios, listar_socios
from routers.router_login import requiere_permiso, validar_csrf

membresias_bp = Blueprint('membresias', __name__)


@membresias_bp.get('/membresias')
@requiere_permiso('membresias.gestionar')
def lista():
    try:
        membresias, planes, socios = listar_membresias(), listar_planes(), listar_socios()
    except (ErrorMembresias, ErrorSocios) as exc:
        flash(str(exc), 'danger')
        return render_template('membresias/lista_membresias.html', disponible=False), 503
    return render_template('membresias/lista_membresias.html', disponible=True,
                           membresias=membresias, planes=planes, socios=socios)


def _guardar(operacion, mensaje, *args):
    validar_csrf()
    try:
        operacion(*args)
        flash(mensaje, 'success')
    except ErrorMembresias as exc:
        flash(str(exc), 'danger')
    return redirect(url_for('membresias.lista'))


@membresias_bp.post('/membresias/crear')
@requiere_permiso('membresias.gestionar')
def crear():
    return _guardar(crear_membresia, 'Membresía asignada correctamente.',
                    request.form.get('socio_id'), request.form.get('plan_id'), request.form.get('fecha_inicio'))


@membresias_bp.post('/membresias/estado/<int:membresia_id>')
@requiere_permiso('membresias.gestionar')
def estado(membresia_id):
    return _guardar(cambiar_estado_membresia, 'Estado actualizado correctamente.',
                    membresia_id, request.form.get('estado'))


@membresias_bp.post('/membresias/eliminar/<int:membresia_id>')
@requiere_permiso('membresias.gestionar')
def eliminar(membresia_id):
    return _guardar(eliminar_membresia, 'Membresía eliminada correctamente.', membresia_id)


@membresias_bp.post('/planes/crear')
@requiere_permiso('planes.gestionar')
def nuevo_plan():
    return _guardar(crear_plan, 'Plan creado correctamente.', request.form.get('nombre'),
                    request.form.get('precio'), request.form.get('duracion_dias'))
