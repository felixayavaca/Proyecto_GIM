from io import BytesIO

from flask import Blueprint, abort, flash, redirect, render_template, request, send_file, session, url_for
from openpyxl import Workbook
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

from controllers.exportar_excel import nombre_descarga_excel
from controllers.funciones_entrenadores import (
    DIAS, ErrorEntrenadores, cambiar_estado_rutina, crear_rutina, crear_valoracion,
    listar_instructores_entrenamiento, listar_rutinas, listar_socios_entrenamiento, listar_valoraciones,
)
from routers.router_login import login_requerido, requiere_permiso, validar_csrf


entrenadores_bp = Blueprint('entrenadores', __name__)
RUTINAS = 'rutinas.gestionar'
VALORACIONES = 'valoraciones.gestionar'
FILTROS_RUTINAS = ('rutina_socio_id', 'dia_semana', 'grupo_muscular', 'instructor_id', 'activa')
FILTROS_VALORACIONES = ('valoracion_socio_id', 'valoracion_fecha', 'valoracion_instructor_id', 'valoracion_clasificacion')


def _filtros():
    filtros = {campo: request.args[campo] for campo in (*FILTROS_RUTINAS, *FILTROS_VALORACIONES)
               if request.args.get(campo)}
    if socio_id := request.args.get('socio_id'):
        filtros.setdefault('rutina_socio_id', socio_id)
        filtros.setdefault('valoracion_socio_id', socio_id)
    return filtros


def _datos(filtros):
    try:
        rutinas = listar_rutinas(**{
            campo.removeprefix('rutina_'): filtros.get(campo) for campo in FILTROS_RUTINAS
        })
        valoraciones = listar_valoraciones(**{
            campo.removeprefix('valoracion_'): filtros.get(campo) for campo in FILTROS_VALORACIONES
        })
        return rutinas, valoraciones
    except ValueError as exc:
        abort(400, description=str(exc))


@entrenadores_bp.get('/entrenadores')
@login_requerido
def panel():
    usuario = session['usuario']
    permisos = set(usuario['permisos'])
    if not permisos.intersection((RUTINAS, VALORACIONES, 'socios.ver')):
        abort(403)
    filtros = _filtros()
    entrenador = usuario.get('rol_nombre') == 'Entrenador'
    puede_crear = permisos.intersection((RUTINAS, VALORACIONES))
    try:
        rutinas, valoraciones = _datos(filtros)
        socios = listar_socios_entrenamiento()
        instructores_filtro = listar_instructores_entrenamiento()
        instructores = (listar_instructores_entrenamiento(usuario['id']) if entrenador else instructores_filtro) if puede_crear else []
    except ErrorEntrenadores as exc:
        flash(str(exc), 'danger')
        return render_template('entrenadores/panel_entrenador.html', disponible=False), 503
    return render_template(
        'entrenadores/panel_entrenador.html', disponible=True, rutinas=rutinas, valoraciones=valoraciones,
        socios=socios, instructores=instructores, entrenador=entrenador, dias=DIAS, filtros=filtros,
        opciones_socios=[(s['id'], f"{s['cedula']} · {s['nombre']} {s['apellido']}") for s in socios],
        opciones_instructores=[(i['id'], f"{i['nombre']} {i['apellido']}") for i in instructores_filtro],
        opciones_dias=[(dia, dia) for dia in DIAS],
        filtros_rutinas={campo: filtros[campo] for campo in FILTROS_RUTINAS if campo in filtros},
        filtros_valoraciones={campo: filtros[campo] for campo in FILTROS_VALORACIONES if campo in filtros},
        mostrar_valoraciones=request.args.get('tab') == 'valoraciones',
    )


def _instructor():
    usuario = session['usuario']
    if usuario.get('rol_nombre') != 'Entrenador':
        return request.form.get('instructor_id')
    vinculados = listar_instructores_entrenamiento(usuario['id'])
    if not vinculados:
        raise ValueError('Tu cuenta de Entrenador necesita un instructor vinculado.')
    return vinculados[0]['id']


def _guardar(operacion, mensaje, tab=None):
    validar_csrf()
    try:
        operacion()
        flash(mensaje, 'success')
    except (ErrorEntrenadores, ValueError) as exc:
        flash(str(exc), 'danger')
    return redirect(url_for('entrenadores.panel', **_filtros(), tab=tab))


@entrenadores_bp.post('/entrenadores/valoracion/crear')
@requiere_permiso(VALORACIONES)
def nueva_valoracion():
    def guardar():
        campos = ('fecha', 'peso_kg', 'estatura_cm', 'porcentaje_grasa', 'observaciones')
        crear_valoracion(request.form.get('socio_id'), _instructor(), *(request.form.get(campo) for campo in campos),
                         grasa_modo=request.form.get('grasa_modo', 'manual'))

    return _guardar(guardar, 'Valoración registrada.', tab='valoraciones')


@entrenadores_bp.post('/entrenadores/rutina/crear')
@requiere_permiso(RUTINAS)
def nueva_rutina():
    def guardar():
        campos = ('dia_semana', 'grupo_muscular', 'ejercicios_detalle')
        crear_rutina(request.form.get('socio_id'), _instructor(), *(request.form.get(campo) for campo in campos))

    return _guardar(guardar, 'Rutina registrada.')


@entrenadores_bp.post('/entrenadores/rutina/estado/<int:rutina_id>')
@requiere_permiso(RUTINAS)
def estado_rutina(rutina_id):
    return _guardar(lambda: cambiar_estado_rutina(rutina_id, request.form.get('activa')),
                    'Estado de la rutina actualizado.')


def _agregar_hoja(libro, nombre, columnas, registros):
    hoja = libro.create_sheet(nombre)
    negrita = Font(bold=True)
    for posicion, (campo, titulo) in enumerate(columnas, start=1):
        hoja.cell(1, posicion, titulo).font = negrita
        ancho = len(titulo)
        for fila, registro in enumerate(registros, start=2):
            valor = registro[campo]
            if isinstance(valor, str):
                valor = ILLEGAL_CHARACTERS_RE.sub('', valor)
            celda = hoja.cell(fila, posicion, valor)
            if isinstance(valor, str):
                celda.data_type = 's'
            elif campo == 'fecha':
                celda.number_format = 'yyyy-mm-dd'
            if valor is not None:
                ancho = max(ancho, *(len(linea) for linea in str(valor).split('\n')))
        hoja.column_dimensions[get_column_letter(posicion)].width = min(65, ancho + 3)
    hoja.freeze_panes = 'A2'
    hoja.auto_filter.ref = hoja.dimensions


@entrenadores_bp.get('/entrenadores/exportar')
@requiere_permiso('reportes.exportar')
def exportar():
    try:
        rutinas, valoraciones = _datos(_filtros())
    except ErrorEntrenadores as exc:
        abort(503, description=str(exc))
    libro = Workbook()
    libro.remove(libro.active)
    comunes = (('cedula', 'Cédula'), ('socio_nombre', 'Socio'), ('instructor_nombre', 'Instructor'))
    _agregar_hoja(libro, 'Valoraciones', comunes + (
        ('fecha', 'Fecha'), ('peso_kg', 'Peso (kg)'), ('estatura_cm', 'Estatura (cm)'),
        ('imc', 'IMC'), ('porcentaje_grasa', 'Grasa (%)'), ('observaciones', 'Observaciones'),
    ), valoraciones)
    for rutina in rutinas:
        rutina['estado'] = 'Activa' if rutina['activa'] else 'Inactiva'
    _agregar_hoja(libro, 'Rutinas', comunes + (
        ('dia_semana', 'Día'), ('grupo_muscular', 'Grupo muscular'),
        ('ejercicios_detalle', 'Ejercicios'), ('estado', 'Estado'),
    ), rutinas)
    contenido = BytesIO()
    libro.save(contenido)
    contenido.seek(0)
    return send_file(contenido, as_attachment=True, download_name=nombre_descarga_excel('rutinas_valoraciones'),
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
