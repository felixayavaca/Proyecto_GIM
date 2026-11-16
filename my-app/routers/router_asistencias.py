from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from controllers.exportar_excel import generar_excel
from controllers.funciones_asistencias import (
    ErrorAsistencias, eliminar_asistencia, listar_asistencias, listar_socios_para_entrada, listar_usuarios_asistencias,
    registrar_entrada, registrar_salida,
)
from routers.router_login import login_requerido, requiere_permiso, validar_csrf


asistencias_bp = Blueprint('asistencias', __name__)


def _filtros():
    return {campo: request.args[campo] for campo in (
        'q', 'fecha_inicio', 'fecha_fin', 'estado_estancia', 'solo_activos',
        'fecha_entrada', 'hora_entrada', 'hora_salida', 'cedula', 'socio', 'registrado_por',
    ) if request.args.get(campo)}


def _consultar(filtros):
    estado = filtros.get('estado_estancia', 'todos')
    activos = filtros.get('solo_activos', '')
    if estado not in ('todos', 'en_gimnasio', 'finalizada') or activos not in ('', '1'):
        abort(400, description='Selecciona filtros válidos.')
    try:
        return listar_asistencias(
            filtros.get('q'), filtros.get('fecha_inicio'), filtros.get('fecha_fin'),
            estado == 'en_gimnasio', solo_activos=activos == '1',
            solo_finalizadas=estado == 'finalizada',
            fecha_entrada=filtros.get('fecha_entrada'), cedula=filtros.get('cedula'),
            socio=filtros.get('socio'), registrado_por=filtros.get('registrado_por'),
            hora_entrada=filtros.get('hora_entrada'), hora_salida=filtros.get('hora_salida'),
        )
    except ValueError as exc:
        abort(400, description=str(exc))


@asistencias_bp.get('/asistencias')
@requiere_permiso('asistencias.ver')
def lista():
    filtros = _filtros()
    try:
        asistencias = _consultar(filtros)
        socios = listar_socios_para_entrada() if 'asistencias.registrar' in session['usuario']['permisos'] else []
        usuarios = listar_usuarios_asistencias()
    except ErrorAsistencias as exc:
        flash(str(exc), 'danger')
        return render_template('asistencias/control_asistencias.html', disponible=False), 503
    return render_template('asistencias/control_asistencias.html', disponible=True,
                           asistencias=asistencias, socios=socios, usuarios=usuarios, filtros=filtros)


def _guardar(operacion, *args):
    validar_csrf()
    try:
        exito, mensaje = operacion(*args)
        categoria = 'warning' if 'ADVERTENCIA' in mensaje else 'success'
        flash(mensaje, categoria if exito else 'danger')
    except ErrorAsistencias as exc:
        flash(str(exc), 'danger')
    return redirect(url_for('asistencias.lista', **_filtros()))


@asistencias_bp.post('/asistencias/entrada')
@requiere_permiso('asistencias.registrar')
def entrada():
    return _guardar(registrar_entrada, request.form.get('socio_id'), session['usuario']['id'])


@asistencias_bp.post('/asistencias/salida/<int:asistencia_id>')
@requiere_permiso('asistencias.registrar')
def salida(asistencia_id):
    return _guardar(registrar_salida, asistencia_id)


@asistencias_bp.post('/asistencias/eliminar/<int:asistencia_id>')
@login_requerido
def eliminar(asistencia_id):
    if session['usuario'].get('rol_nombre') != 'Admin':
        flash('Solo Admin puede eliminar asistencias.', 'danger')
        abort(403)
    validar_csrf()
    try:
        eliminar_asistencia(asistencia_id)
        flash('Asistencia eliminada correctamente.', 'success')
    except ErrorAsistencias as exc:
        flash(str(exc), 'danger')
    return redirect(url_for('asistencias.lista', **_filtros()))


@asistencias_bp.get('/asistencias/exportar')
@requiere_permiso('reportes.exportar')
def exportar():
    try:
        asistencias = _consultar(_filtros())
    except ErrorAsistencias as exc:
        abort(503, description=str(exc))
    encabezados = ('Entrada', 'Salida', 'Estado', 'Estancia (min)', 'Cédula', 'Socio', 'Registrado por')
    filas = (
        (a['fecha_entrada'], a['fecha_salida'], 'En gimnasio' if a['fecha_salida'] is None else 'Salida registrada',
         a['minutos_estancia'], a['cedula'], a['socio_nombre'], a['registrado_por'])
        for a in asistencias
    )
    return generar_excel('asistencias.xlsx', encabezados, filas)
