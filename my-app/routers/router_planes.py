from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from controllers.exportar_excel import generar_excel
from controllers.funciones_planes import (
    CATEGORIAS, ErrorPlanes, actualizar_plan, cambiar_estado_plan, crear_plan, listar_planes,
)
from routers.router_login import requiere_permiso, validar_csrf

planes_bp = Blueprint('planes', __name__)


def _filtros():
    return {campo: request.args[campo] for campo in ('q', 'estado', 'categoria', 'referido', 'precio_max', 'duracion')
            if request.args.get(campo)}


@planes_bp.get('/planes')
@requiere_permiso('planes.ver')
def lista():
    filtros = _filtros()
    try:
        planes = listar_planes(**filtros)
    except ValueError as exc:
        abort(400, description=str(exc))
    except ErrorPlanes as exc:
        flash(str(exc), 'danger')
        return render_template('planes/lista_planes.html', disponible=False), 503
    return render_template('planes/lista_planes.html', disponible=True, planes=planes,
                           filtros=filtros, categorias=CATEGORIAS)


def _guardar(operacion, mensaje, *args):
    validar_csrf()
    try:
        operacion(*args)
        flash(mensaje, 'success')
    except (ValueError, ErrorPlanes) as exc:
        flash(str(exc), 'danger')
    return redirect(url_for('planes.lista', **_filtros()))


@planes_bp.post('/planes/crear')
@requiere_permiso('planes.gestionar')
def crear():
    return _guardar(crear_plan, 'Plan creado.', request.form)


@planes_bp.post('/planes/editar/<int:plan_id>')
@requiere_permiso('planes.gestionar')
def editar(plan_id):
    return _guardar(actualizar_plan, 'Plan actualizado.', plan_id, request.form)


@planes_bp.post('/planes/estado/<int:plan_id>')
@requiere_permiso('planes.gestionar')
def estado(plan_id):
    return _guardar(cambiar_estado_plan, 'Estado del plan actualizado.', plan_id, request.form.get('activo'))


@planes_bp.get('/planes/exportar')
@requiere_permiso('reportes.exportar')
@requiere_permiso('planes.ver')
def exportar():
    try:
        planes = listar_planes(**_filtros())
    except ValueError as exc:
        abort(400, description=str(exc))
    except ErrorPlanes as exc:
        abort(503, description=str(exc))
    encabezados = ('ID', 'Nombre', 'Categoría', 'Plan referido', 'Precio', 'Duración (días)', 'Estado', 'Total de ventas')
    filas = ((p['id'], p['nombre'], p['categoria'], 'Sí' if p['es_plan_referido'] else 'No',
              p['precio'], p['duracion_dias'], 'Activo' if p['activo'] else 'Inactivo', p['total_ventas']) for p in planes)
    return generar_excel('planes.xlsx', encabezados, filas)
