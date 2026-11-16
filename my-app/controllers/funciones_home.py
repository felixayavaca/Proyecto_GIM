import calendar
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import mysql.connector

from conexion.conexionBD import connectionBD


CATEGORIAS = ('Basico', 'Pro', 'Premium', 'Platinum')
METODOS = ('Efectivo', 'Transferencia', 'Tarjeta')
GENEROS = ('M', 'F', 'Otro')


def listar_socios_dashboard():
    try:
        with connectionBD() as conexion:
            with conexion.cursor(dictionary=True) as cursor:
                cursor.execute(
                    "SELECT id, cedula, CONCAT_WS(' ', nombre, apellido) AS nombre "
                    'FROM socios ORDER BY apellido, nombre, id', (),
                )
                return cursor.fetchall()
    except (ConnectionError, mysql.connector.Error) as exc:
        raise ConnectionError('No se pudo cargar la lista de socios.') from exc


def _periodo(fecha_inicio, fecha_fin):
    hoy = datetime.now(ZoneInfo('America/Guayaquil')).date()
    try:
        fin = date.fromisoformat(str(fecha_fin)) if fecha_fin else hoy
        if fecha_inicio:
            inicio = date.fromisoformat(str(fecha_inicio))
        else:
            anio, mes = divmod(fin.year * 12 + fin.month - 7, 12)
            inicio = date(anio, mes + 1, min(fin.day, calendar.monthrange(anio, mes + 1)[1]))
        if inicio.year < 1000 or inicio > fin:
            raise ValueError
    except ValueError as exc:
        raise ValueError('Indica un rango de fechas válido.') from exc
    return hoy, inicio, fin


_VISITAS = """
    FROM asistencias a JOIN socios s ON s.id = a.socio_id
    WHERE a.fecha_entrada BETWEEN %s AND %s
      AND (%s IS NULL OR a.socio_id = %s)
      AND (%s IS NULL OR EXISTS (
          SELECT 1 FROM membresias m JOIN planes p ON p.id = m.plan_id
          WHERE m.socio_id = s.id AND p.categoria = %s AND m.estado <> %s
            AND DATE(a.fecha_entrada) BETWEEN m.fecha_inicio AND m.fecha_fin
      ))
"""

_FILTRO_PAGOS = """
    WHERE m.fecha_pago BETWEEN %s AND %s AND (%s IS NULL OR p.categoria = %s)
      AND (%s IS NULL OR m.socio_id = %s)
"""
_PAGOS = ' FROM membresias m JOIN planes p ON p.id = m.plan_id ' + _FILTRO_PAGOS

def _meses(inicio, fin):
    for indice in range(inicio.year * 12 + inicio.month - 1, fin.year * 12 + fin.month):
        anio, mes = divmod(indice, 12)
        yield f'{anio:04d}-{mes + 1:02d}'


def obtener_metricas_dashboard(fecha_inicio=None, fecha_fin=None, categoria_plan=None, socio_id=None):
    categoria = categoria_plan or None
    if categoria is not None and categoria not in CATEGORIAS:
        raise ValueError('Selecciona una categoría de plan válida.')
    try:
        socio_id = int(str(socio_id)) if socio_id not in (None, '') else None
        if socio_id is not None and not 1 <= socio_id <= 2147483647:
            raise ValueError
    except ValueError as exc:
        raise ValueError('Selecciona un socio válido.') from exc
    hoy, inicio, fin = _periodo(fecha_inicio, fecha_fin)
    rango = (datetime.combine(inicio, time.min), datetime.combine(fin, time(23, 59, 59)))
    fechas_hoy = (datetime.combine(hoy, time.min), datetime.combine(hoy, time(23, 59, 59)))
    socio_params = (socio_id, socio_id)
    visita_filtros = (*socio_params, categoria, categoria, 'cancelada')
    visita_params = (*rango, *visita_filtros)
    pago_params = (*rango, categoria, categoria, *socio_params)

    try:
        with connectionBD() as conexion:
            with conexion.cursor(dictionary=True) as cursor:
                def consultar(sql, parametros, uno=False):
                    cursor.execute(sql, parametros)
                    return cursor.fetchone() if uno else cursor.fetchall()

                socio = None
                asistencia_diaria = []
                if socio_id is not None:
                    socio = consultar(
                        "SELECT id, cedula, CONCAT_WS(' ', nombre, apellido) AS nombre FROM socios WHERE id = %s",
                        (socio_id,), uno=True,
                    )
                    if socio is None:
                        raise ValueError('El socio seleccionado no existe.')
                    socio['membresia'] = consultar(
                        """SELECT p.nombre AS plan, m.fecha_inicio, m.fecha_fin,
                                  CASE WHEN m.estado = %s THEN 'Cancelada'
                                       WHEN m.estado = %s OR m.fecha_fin < %s THEN 'Vencida'
                                       WHEN p.activo = %s THEN 'Plan inactivo'
                                       WHEN m.fecha_inicio > %s THEN 'Programada'
                                       ELSE 'Vigente' END AS estado_actual
                           FROM membresias m JOIN planes p ON p.id = m.plan_id
                           WHERE m.socio_id = %s AND (%s IS NULL OR p.categoria = %s)
                           ORDER BY (m.estado = %s AND p.activo = %s
                                     AND %s BETWEEN m.fecha_inicio AND m.fecha_fin) DESC,
                                    m.fecha_inicio DESC, m.id DESC LIMIT %s""",
                        ('cancelada', 'vencida', hoy, 0, hoy, socio_id, categoria, categoria, 'activa', 1, hoy, 1),
                        uno=True,
                    )
                    asistencia_diaria = consultar(
                        'SELECT DATE(a.fecha_entrada) AS fecha, COUNT(*) AS visitas ' + _VISITAS
                        + ' GROUP BY fecha ORDER BY fecha DESC', visita_params,
                    )

                kpis = consultar(
                    """SELECT
                        (SELECT COUNT(*) FROM socios s WHERE s.activo = %s
                         AND (%s IS NULL OR s.id = %s)) AS socios_activos,
                        (SELECT COUNT(*) FROM membresias m JOIN planes p ON p.id = m.plan_id
                         WHERE m.estado = %s AND p.activo = %s AND %s BETWEEN m.fecha_inicio AND m.fecha_fin
                           AND (%s IS NULL OR m.socio_id = %s)
                           AND (%s IS NULL OR p.categoria = %s)) AS membresias_vigentes,
                        (SELECT COALESCE(SUM(m.precio_pagado), 0) """ + _PAGOS + """) AS ingresos_periodo,
                        (SELECT COUNT(*) """ + _VISITAS + """) AS asistencias_hoy,
                        (SELECT COALESCE(ROUND(AVG(TIMESTAMPDIFF(MINUTE, a.fecha_entrada, a.fecha_salida)), 1), 0)
                         """ + _VISITAS + """ AND a.fecha_salida IS NOT NULL) AS promedio_estancia""",
                    (1, *socio_params, 'activa', 1, hoy, *socio_params, categoria, categoria,
                     *pago_params, *fechas_hoy, *visita_filtros, *visita_params),
                    uno=True,
                )
                horas = consultar('SELECT HOUR(a.fecha_entrada) AS hora, COUNT(*) AS visitas ' + _VISITAS +
                                  ' GROUP BY hora ORDER BY hora', visita_params)
                generos = consultar('SELECT s.genero, COUNT(*) AS visitas ' + _VISITAS +
                                    ' GROUP BY s.genero', visita_params)
                planes = consultar(
                    'SELECT p.nombre, p.categoria, COUNT(*) AS ventas, COALESCE(SUM(m.precio_pagado), 0) AS ingresos '
                    + _PAGOS + ' GROUP BY p.id, p.nombre, p.categoria ORDER BY ventas DESC, ingresos DESC, p.nombre',
                    pago_params,
                )
                altas = consultar(
                    """SELECT DATE_FORMAT(s.fecha_registro, '%Y-%m') AS mes, COUNT(*) AS cantidad
                       FROM socios s WHERE s.fecha_registro BETWEEN %s AND %s
                       AND (%s IS NULL OR s.id = %s)
                       AND (%s IS NULL OR EXISTS (
                           SELECT 1 FROM membresias m JOIN planes p ON p.id = m.plan_id
                           WHERE m.socio_id = s.id AND p.categoria = %s AND m.fecha_pago BETWEEN %s AND %s
                       )) GROUP BY mes""",
                    (inicio, fin, *socio_params, categoria, categoria, *rango),
                )
                perdidas = consultar(
                    """SELECT DATE_FORMAT(m.fecha_fin, '%Y-%m') AS mes, COUNT(*) AS cantidad
                       FROM membresias m JOIN planes p ON p.id = m.plan_id
                       WHERE m.estado IN (%s, %s) AND m.fecha_fin BETWEEN %s AND %s
                       AND (%s IS NULL OR m.socio_id = %s)
                       AND (%s IS NULL OR p.categoria = %s) GROUP BY mes""",
                    ('vencida', 'cancelada', inicio, fin, *socio_params, categoria, categoria),
                )
                metodos = consultar(
                    'SELECT m.metodo_pago, COUNT(*) AS pagos, COALESCE(SUM(m.precio_pagado), 0) AS ingresos '
                    + _PAGOS + ' GROUP BY m.metodo_pago', pago_params,
                )
                instructores = consultar(
                    """SELECT CONCAT_WS(' ', i.nombre, i.apellido) AS instructor, COUNT(s.id) AS socios
                       FROM instructores i
                       LEFT JOIN socios s ON s.instructor_id = i.id AND s.activo = %s
                       WHERE i.activo = %s
                       GROUP BY i.id, i.nombre, i.apellido
                       ORDER BY socios DESC, i.nombre ASC""",
                    (1, 1),
                )
    except (ConnectionError, mysql.connector.Error) as exc:
        raise ConnectionError('No se pudo cargar el dashboard.') from exc

    visitas_hora = {fila['hora']: fila['visitas'] for fila in horas}
    visitas_genero = {fila['genero']: fila['visitas'] for fila in generos}
    altas_mes = {fila['mes']: fila['cantidad'] for fila in altas}
    perdidas_mes = {fila['mes']: fila['cantidad'] for fila in perdidas}
    pagos_metodo = {fila['metodo_pago']: fila for fila in metodos}
    return {
        'fecha_inicio': inicio.isoformat(), 'fecha_fin': fin.isoformat(), 'categoria': categoria or '',
        'socio_id': str(socio_id) if socio_id is not None else '', 'socio': socio,
        'asistencia_diaria': asistencia_diaria,
        'kpis': kpis,
        'horarios': [{'hora': f'{hora:02d}:00', 'visitas': visitas_hora.get(hora, 0)} for hora in range(24)],
        'generos': [{'genero': genero, 'visitas': visitas_genero.get(genero, 0)} for genero in GENEROS],
        'planes': planes,
        'mensual': [
            {'mes': mes, 'altas': altas_mes.get(mes, 0), 'perdidas': perdidas_mes.get(mes, 0)}
            for mes in _meses(inicio, fin)
        ],
        'metodos': [
            pagos_metodo.get(metodo, {'metodo_pago': metodo, 'pagos': 0, 'ingresos': 0}) for metodo in METODOS
        ],
        'instructores': instructores,
    }
