from flask import Blueprint, abort, current_app, flash, render_template, request

from controllers.exportar_excel import generar_excel
from controllers.funciones_home import CATEGORIAS, listar_socios_dashboard, obtener_metricas_dashboard
from routers.router_login import login_requerido, requiere_permiso


home_bp = Blueprint('home', __name__)
INDICADORES = (
    ('socios_activos', 'Socios activos', 'Cuentas habilitadas hoy', ''),
    ('membresias_vigentes', 'Membresías vigentes', 'Membresías activas en planes habilitados y dentro de sus fechas', ''),
    ('ingresos_periodo', 'Ingresos', 'Periodo', 'USD'),
    ('asistencias_hoy', 'Asistencias de hoy', 'Hoy', ''),
    ('promedio_estancia', 'Tiempo promedio de estancia', 'Visitas cerradas del periodo', 'min'),
)


def _metricas():
    return obtener_metricas_dashboard(request.args.get('fecha_inicio'), request.args.get('fecha_fin'),
                                      request.args.get('categoria'), request.args.get('socio_id'))


@home_bp.get('/dashboard')
@requiere_permiso('reportes.ver')
def dashboard():
    filtros = {campo: request.args.get(campo, '') for campo in ('fecha_inicio', 'fecha_fin', 'categoria', 'socio_id')}
    socios = []
    try:
        socios = listar_socios_dashboard()
        resumen = _metricas()
    except ValueError as exc:
        flash(str(exc), 'warning')
        return render_template('home/dashboard.html', resumen=None, filtros=filtros, categorias=CATEGORIAS, socios=socios), 400
    except ConnectionError:
        current_app.logger.exception('No se pudo consultar el dashboard en MySQL.')
        flash('No se pudo cargar el resumen. Inténtalo más tarde.', 'danger')
        return render_template('home/dashboard.html', resumen=None, filtros=filtros, categorias=CATEGORIAS, socios=socios), 503
    filtros = {campo: resumen[campo] for campo in filtros}
    graficos = {nombre: resumen[nombre] for nombre in ('horarios', 'generos', 'mensual')}
    graficos['planes'] = [dict(plan, ingresos=float(plan['ingresos'])) for plan in resumen['planes'][:10]]
    graficos['metodos'] = [dict(fila, ingresos=float(fila['ingresos'])) for fila in resumen['metodos']]
    return render_template('home/dashboard.html', resumen=resumen, filtros=filtros, categorias=CATEGORIAS,
                           indicadores=INDICADORES, graficos=graficos, socios=socios)


@home_bp.get('/dashboard/exportar')
@requiere_permiso('reportes.exportar')
def exportar():
    try:
        datos = _metricas()
    except ValueError as exc:
        abort(400, description=str(exc))
    except ConnectionError:
        abort(503, description='No se pudo cargar el resumen.')

    def filas():
        yield ('Periodo', 'Desde / hasta', datos['fecha_inicio'], datos['fecha_fin'])
        yield ('Periodo', 'Categoría', datos['categoria'] or 'Todas')
        if socio := datos['socio']:
            yield ('Socio', socio['nombre'], socio['cedula'])
            membresia = socio['membresia']
            if membresia:
                yield ('Socio', 'Membresía actual', membresia['estado_actual'], membresia['plan'], membresia['fecha_fin'])
            else:
                yield ('Socio', 'Membresía actual', 'Sin membresía')
            yield ('Socio', 'Días asistidos', len(datos['asistencia_diaria']))
            for fila in datos['asistencia_diaria']:
                yield ('Días asistidos', fila['fecha'], fila['visitas'])
        for clave, titulo, alcance, unidad in INDICADORES:
            yield ('Indicadores', titulo, datos['kpis'][clave], unidad, alcance)
        for fila in datos['horarios']:
            yield ('Horarios', fila['hora'], fila['visitas'])
        for fila in datos['generos']:
            yield ('Visitas por género', fila['genero'], fila['visitas'])
        yield ('Ventas por plan', 'Plan', 'Categoría', 'Ventas', 'Ingresos (USD)')
        for fila in datos['planes']:
            yield ('Ventas por plan', fila['nombre'], fila['categoria'], fila['ventas'], fila['ingresos'])
        yield ('Tendencia mensual', 'Mes', 'Altas', 'Membresías vencidas o canceladas')
        for fila in datos['mensual']:
            yield ('Tendencia mensual', fila['mes'], fila['altas'], fila['perdidas'])
        yield ('Pagos por método', 'Método', 'Pagos', 'Ingresos (USD)')
        for fila in datos['metodos']:
            yield ('Pagos por método', fila['metodo_pago'], fila['pagos'], fila['ingresos'])
        yield ('Carga por instructor', 'Instructor', 'Socios asignados')
        for fila in datos['instructores']:
            yield ('Carga por instructor', fila['instructor'], fila['socios'])

    return generar_excel('resumen_gerencial.xlsx',
                         ('Sección', 'Concepto', 'Dato 1', 'Dato 2', 'Dato 3', 'Dato 4'), filas())
