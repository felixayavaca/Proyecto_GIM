from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from controllers.exportar_excel import generar_excel
from controllers.funciones_instructores import (
    TIPOS_CONTRATO, ErrorInstructores, actualizar_instructor, cambiar_estado_instructor,
    crear_instructor, listar_instructores, listar_usuarios_entrenadores,
)
from routers.router_login import login_requerido, requiere_permiso, validar_csrf


instructores_bp = Blueprint('instructores', __name__)
GESTIONAR = 'instructores.gestionar'


def _filtros():
    return {campo: request.args[campo] for campo in (
        'q', 'estado', 'cedula', 'instructor', 'telefono', 'especialidad',
        'tipo_contrato', 'direccion', 'contacto_emergencia', 'socios_min',
    )
            if request.args.get(campo)}


@instructores_bp.get('/instructores')
@login_requerido
def lista():
    permisos = session['usuario']['permisos']
    gestionar = GESTIONAR in permisos
    if not gestionar and 'socios.ver' not in permisos:
        abort(403)
    filtros = _filtros()
    try:
        instructores = listar_instructores(**filtros)
        usuarios = listar_usuarios_entrenadores() if gestionar else []
    except ValueError as exc:
        abort(400, description=str(exc))
    except ErrorInstructores as exc:
        flash(str(exc), 'danger')
        return render_template('instructores/lista_instructores.html', disponible=False), 503
    return render_template(
        'instructores/lista_instructores.html', disponible=True, instructores=instructores,
        usuarios=usuarios, filtros=filtros, gestionar=gestionar, tipos_contrato=TIPOS_CONTRATO,
    )


def _guardar(operacion, mensaje, *args):
    validar_csrf()
    try:
        operacion(*args)
        flash(mensaje, 'success')
    except ErrorInstructores as exc:
        flash(str(exc), 'danger')
    return redirect(url_for('instructores.lista', **_filtros()))


@instructores_bp.post('/instructores/crear')
@requiere_permiso(GESTIONAR)
def crear():
    return _guardar(crear_instructor, 'Instructor creado.', request.form)


@instructores_bp.post('/instructores/editar/<int:instructor_id>')
@requiere_permiso(GESTIONAR)
def editar(instructor_id):
    return _guardar(actualizar_instructor, 'Instructor actualizado.', instructor_id, request.form)


@instructores_bp.post('/instructores/estado/<int:instructor_id>')
@requiere_permiso(GESTIONAR)
def estado(instructor_id):
    return _guardar(cambiar_estado_instructor, 'Estado del instructor actualizado.',
                    instructor_id, request.form.get('activo'))


@instructores_bp.get('/instructores/exportar')
@requiere_permiso('reportes.exportar')
def exportar():
    try:
        instructores = listar_instructores(**_filtros())
    except ValueError as exc:
        abort(400, description=str(exc))
    except ErrorInstructores as exc:
        abort(503, description=str(exc))
    encabezados = ('ID', 'Cédula', 'Nombre', 'Apellido', 'Teléfono', 'Especialidad',
                   'Contrato', 'Dirección', 'Contacto de emergencia',
                   'Fecha de contratación', 'Estado', 'Socios asignados', 'Cuenta vinculada')
    filas = (
        (i['id'], i['cedula'], i['nombre'], i['apellido'], i['telefono'], i['especialidad'],
         i['tipo_contrato'], i['direccion'], i['contacto_emergencia'],
         i['fecha_contratacion'], 'Activo' if i['activo'] else 'Inactivo',
         i['socios_asignados'], i['usuario_email'])
        for i in instructores
    )
    return generar_excel('instructores.xlsx', encabezados, filas)
