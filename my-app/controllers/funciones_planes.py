from contextlib import contextmanager

import mysql.connector
from conexion.conexionBD import connectionBD
from controllers.funciones_socios import _precio


CATEGORIAS = ('Basico', 'Pro', 'Premium', 'Platinum')


class ErrorPlanes(Exception):
    pass


@contextmanager
def _cursor(escritura=False):
    try:
        with connectionBD() as conexion:
            try:
                with conexion.cursor(dictionary=True) as cursor:
                    yield cursor
                if escritura:
                    conexion.commit()
            except Exception:
                if escritura:
                    conexion.rollback()
                raise
    except mysql.connector.IntegrityError as exc:
        if exc.errno == 1062:
            raise ErrorPlanes('Ya existe un plan con ese nombre.') from exc
        raise ErrorPlanes('No se pudo guardar el plan.') from exc
    except (ConnectionError, mysql.connector.Error) as exc:
        raise ErrorPlanes('No se pudo completar la operación de planes.') from exc


def listar_planes(q=None, estado=None, categoria=None, *, referido=None, precio_max=None, duracion=None):
    if estado not in (None, '', 0, 1, '0', '1') or categoria not in (None, '', *CATEGORIAS):
        raise ValueError('Selecciona filtros válidos.')
    estado = None if estado in (None, '') else int(estado)
    categoria = categoria or None
    referido = '' if referido is None else str(referido)
    if referido not in ('', '0', '1'):
        raise ValueError('Selecciona un tipo de plan válido.')
    referido = int(referido) if referido else None
    precio_max = _precio(precio_max) if precio_max not in (None, '') else None
    try:
        duracion = int(str(duracion)) if duracion not in (None, '') else None
        if duracion is not None and not 1 <= duracion <= 2147483647:
            raise ValueError
    except ValueError as exc:
        raise ValueError('Indica una duración válida en días.') from exc
    patron = '%' + (q or '').strip().replace('!', '!!').replace('%', '!%').replace('_', '!_') + '%'
    with _cursor() as cursor:
        cursor.execute(
            """SELECT p.*, COALESCE(v.total, 0) AS total_ventas
               FROM planes p LEFT JOIN (
                   SELECT plan_id, COUNT(*) AS total FROM membresias GROUP BY plan_id
               ) v ON v.plan_id = p.id
               WHERE p.nombre LIKE %s ESCAPE '!'
                 AND (%s IS NULL OR p.activo = %s) AND (%s IS NULL OR p.categoria = %s)
                 AND (%s IS NULL OR p.es_plan_referido = %s)
                 AND (%s IS NULL OR p.precio <= %s) AND (%s IS NULL OR p.duracion_dias = %s)
               ORDER BY p.nombre, p.id""",
            (patron, estado, estado, categoria, categoria, referido, referido,
             precio_max, precio_max, duracion, duracion),
        )
        return cursor.fetchall()


def listar_planes_activos():
    with _cursor() as cursor:
        cursor.execute('SELECT id, nombre, precio, es_plan_referido FROM planes WHERE activo = %s ORDER BY nombre', (1,))
        return cursor.fetchall()


def _validar(datos):
    nombre = datos.get('nombre', '').strip()
    categoria = datos.get('categoria')
    referido = datos.get('es_plan_referido', '0')
    if not 1 <= len(nombre) <= 50 or categoria not in CATEGORIAS or str(referido) not in ('0', '1'):
        raise ValueError('Indica un nombre de hasta 50 caracteres, una categoría y un tipo de plan válidos.')
    try:
        dias = int(str(datos.get('duracion_dias')))
        if not 1 <= dias <= 2147483647:
            raise ValueError
    except ValueError as exc:
        raise ValueError('La duración debe ser un número entero positivo de días.') from exc
    return nombre, categoria, int(referido), _precio(datos.get('precio')), dias


def crear_plan(datos):
    valores = _validar(datos)
    with _cursor(escritura=True) as cursor:
        cursor.execute(
            'INSERT INTO planes (nombre, categoria, es_plan_referido, precio, duracion_dias) VALUES (%s, %s, %s, %s, %s)',
            valores,
        )
        return cursor.lastrowid


def _actualizar(plan_id, sql, parametros):
    with _cursor(escritura=True) as cursor:
        cursor.execute('SELECT id FROM planes WHERE id = %s FOR UPDATE', (plan_id,))
        if cursor.fetchone() is None:
            raise ValueError('El plan no existe.')
        cursor.execute(sql, (*parametros, plan_id))


def actualizar_plan(plan_id, datos):
    _actualizar(
        plan_id, 'UPDATE planes SET nombre=%s, categoria=%s, es_plan_referido=%s, precio=%s, duracion_dias=%s WHERE id=%s',
        _validar(datos),
    )


def cambiar_estado_plan(plan_id, activo):
    if str(activo) not in ('0', '1'):
        raise ValueError('Selecciona un estado válido.')
    _actualizar(plan_id, 'UPDATE planes SET activo = %s WHERE id = %s', (int(activo),))
