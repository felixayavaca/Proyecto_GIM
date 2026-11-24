from collections import defaultdict

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for
from controllers.exportar_excel import generar_excel
from conexion.conexionBD import connectionBD
from controllers.funciones_planes import ErrorPlanes, listar_planes_activos
from controllers.funciones_socios import (
    GENEROS, METODOS_PAGO, ErrorSocios, actualizar_socio, cambiar_estado_socio,
    crear_socio, listar_opciones_socios, listar_pagos, listar_planes_filtro, listar_socios, registrar_pago,
)
from routers.router_login import requiere_permiso, validar_csrf

socios_bp = Blueprint('socios', __name__)


def _filtros():
    return {campo: request.args[campo] for campo in (
        'q', 'estado', 'genero', 'instructor_id', 'cedula', 'socio', 'contacto', 'referente',
        'plan_vigente', 'dias_restantes', 'antiguedad_min', 'fecha_ingreso',
    ) if request.args.get(campo)}


def _filtros_pagos():
    return {campo: request.args[campo] for campo in ('pago_socio', 'pago_plan', 'pago_metodo', 'pago_fecha')
            if request.args.get(campo)}


@socios_bp.get('/socios')
@requiere_permiso('socios.ver')
def lista():
    filtros = _filtros()
    filtros_pagos = _filtros_pagos()
    permisos = session['usuario']['permisos']
    rol = session['usuario'].get('rol_nombre')
    personal = rol in ('Entrenador', 'Nutricionista', 'Fisioterapeuta')
    gestionar = 'socios.gestionar' in permisos
    registrar = 'membresias.gestionar' in permisos
    ver_pagos = registrar or 'membresias.ver' in permisos
    try:
        if personal:
            with connectionBD() as conexion:
                with conexion.cursor(dictionary=True) as cursor:
                    cursor.execute(
                        'SELECT id FROM instructores WHERE usuario_id = %s LIMIT 1',
                        (session['usuario']['id'],),
                    )
                    instructor = cursor.fetchone()
            if instructor:
                filtros['instructor_id'] = str(instructor['id'])
            else:
                filtros['instructor_id'] = '0'
        socios = listar_socios(**filtros)
        referentes, instructores = listar_opciones_socios()
        pagos = listar_pagos(**filtros_pagos) if ver_pagos else []
        planes = listar_planes_activos() if registrar else []
        planes_filtro = listar_planes_filtro()
    except ValueError as exc:
        abort(400, description=str(exc))
    except (ErrorSocios, ErrorPlanes) as exc:
        flash(str(exc), 'danger')
        return render_template('socios/lista_socios.html', disponible=False), 503
    return render_template(
        'socios/lista_socios.html', disponible=True, socios=socios, filtros=filtros,
        filtros_pagos=filtros_pagos, filtros_combinados={**filtros, **filtros_pagos},
        opciones_generos=[(g, g) for g in GENEROS],
        opciones_metodos=[(m, m) for m in METODOS_PAGO],
        opciones_instructores=[(i['id'], f"{i['nombre']} {i['apellido']}") for i in instructores],
        opciones_planes=[(p['id'], p['nombre']) for p in planes_filtro],
        referentes=referentes, instructores=instructores, pagos=pagos, planes=planes,
        gestionar=gestionar, registrar=registrar, ver_pagos=ver_pagos,
        generos=GENEROS, metodos=METODOS_PAGO, mostrar_pagos=ver_pagos and request.args.get('tab') == 'pagos',
    )


def _guardar(operacion, mensaje, *args, tab=None):
    validar_csrf()
    try:
        operacion(*args)
        flash(mensaje, 'success')
    except (ValueError, ErrorSocios) as exc:
        flash(str(exc), 'danger')
    return redirect(url_for('socios.lista', **_filtros(), **_filtros_pagos(), tab=tab))


@socios_bp.post('/socios/crear')
@requiere_permiso('socios.gestionar')
def crear():
    return _guardar(crear_socio, 'Socio creado.', request.form)


@socios_bp.post('/socios/editar/<int:socio_id>')
@requiere_permiso('socios.gestionar')
def editar(socio_id):
    return _guardar(actualizar_socio, 'Socio actualizado.', socio_id, request.form)


@socios_bp.post('/socios/estado/<int:socio_id>')
@requiere_permiso('socios.gestionar')
def estado(socio_id):
    return _guardar(cambiar_estado_socio, 'Estado del socio actualizado.', socio_id, request.form.get('activo'))


@socios_bp.post('/socios/pagar/<int:socio_id>')
@requiere_permiso('membresias.gestionar')
def pagar(socio_id):
    return _guardar(registrar_pago, 'Membresía y pago registrados.', socio_id, request.form, tab='pagos')


@socios_bp.get('/socios/exportar')
@requiere_permiso('reportes.exportar')
def exportar():
    filtros = _filtros()
    filtros_pagos = _filtros_pagos()
    try:
        socios = listar_socios(**filtros)
        pagos = defaultdict(list)
        for pago in listar_pagos(**filtros_pagos):
            pagos[pago['socio_id']].append(pago)
    except ValueError as exc:
        abort(400, description=str(exc))
    except ErrorSocios as exc:
        abort(503, description=str(exc))

    encabezados = ('ID socio', 'Cédula', 'Nombre', 'Apellido', 'Género', 'Teléfono', 'Correo', 'Registro',
                   'Estado socio', 'Instructor', 'Referente', 'Plan vigente', 'Días restantes',
                   'Antigüedad actual (días)', 'ID pago', 'Plan pagado', 'Fecha de pago', 'Método',
                   'Duración (días)', 'Antigüedad al pagar (días)', 'Precio pagado', 'Estado membresía')
    campos_pago = ('id', 'plan_nombre', 'fecha_pago', 'metodo_pago', 'duracion_dias', 'antiguedad', 'precio_pagado', 'estado')

    def filas():
        for socio in socios:
            base = (socio['id'], socio['cedula'], socio['nombre'], socio['apellido'], socio['genero'],
                    socio['telefono'], socio['email'], socio['fecha_registro'],
                    'Activo' if socio['activo'] else 'Inactivo', socio['instructor_nombre'],
                    socio['referente_nombre'], socio['plan_actual'], socio['dias_restantes'], socio['antiguedad'])
            for pago in pagos.get(socio['id'], () if filtros_pagos else ({},)):
                yield base + tuple(pago.get(campo) for campo in campos_pago)

    return generar_excel('socios.xlsx', encabezados, filas())
