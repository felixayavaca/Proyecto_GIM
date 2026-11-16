from contextlib import contextmanager
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import mysql.connector
from conexion.conexionBD import connectionBD

ECUADOR = ZoneInfo('America/Guayaquil')


class ErrorAsistencias(Exception):
    pass


@contextmanager
def _cursor(escritura=False):
    try:
        with connectionBD() as connection:
            try:
                with connection.cursor(dictionary=True) as cursor:
                    yield cursor
                if escritura:
                    connection.commit()
            except Exception:
                if escritura:
                    connection.rollback()
                raise
    except mysql.connector.IntegrityError as exc:
        raise ErrorAsistencias('El socio o usuario ya no está disponible.') from exc
    except (ConnectionError, mysql.connector.Error) as exc:
        raise ErrorAsistencias('No se pudo completar la operación de asistencias. Inténtalo más tarde.') from exc


def _id(valor):
    try:
        numero = int(str(valor))
        if not 1 <= numero <= 2147483647:
            raise ValueError
        return numero
    except (TypeError, ValueError) as exc:
        raise ErrorAsistencias('Selecciona un registro válido.') from exc


def listar_asistencias(q=None, fecha_inicio=None, fecha_fin=None, solo_en_gimnasio=False, *,
                       solo_activos=False, fecha_entrada=None, solo_finalizadas=False,
                       cedula=None, socio=None, registrado_por=None, hora_entrada=None, hora_salida=None):
    try:
        inicio = date.fromisoformat(str(fecha_inicio)) if fecha_inicio else None
        fin = date.fromisoformat(str(fecha_fin)) if fecha_fin else None
        entrada = date.fromisoformat(str(fecha_entrada)) if fecha_entrada else None
        if (inicio and inicio.year < 1000) or (fin and fin.year < 1000) or (inicio and fin and inicio > fin):
            raise ValueError
        if entrada and entrada.year < 1000:
            raise ValueError
    except ValueError as exc:
        raise ValueError('Indica un rango de fechas válido.') from exc
    try:
        horas = tuple(time.fromisoformat(valor) if valor else None for valor in (hora_entrada, hora_salida))
        if any(hora and (hora.tzinfo is not None or hora.microsecond) for hora in horas):
            raise ValueError
    except ValueError as exc:
        raise ValueError('Indica una hora válida en formato HH:MM:SS.') from exc
    hora_entrada, hora_salida = (hora.isoformat() if hora is not None else None for hora in horas)
    desde = datetime.combine(inicio, time.min) if inicio else None
    hasta = datetime.combine(fin, time(23, 59, 59)) if fin else None
    entrada_desde = datetime.combine(entrada, time.min) if entrada else None
    entrada_hasta = datetime.combine(entrada, time(23, 59, 59)) if entrada else None
    try:
        autor = _id(registrado_por) if registrado_por not in (None, '') else None
    except ErrorAsistencias as exc:
        raise ValueError('Selecciona un usuario válido.') from exc

    def patron(texto):
        return '%' + (texto or '').strip().replace('!', '!!').replace('%', '!%').replace('_', '!_') + '%'

    general = patron(q)
    with _cursor() as cursor:
        cursor.execute('''SELECT a.id, a.fecha_entrada, a.fecha_salida, a.registrado_por AS usuario_id, s.cedula,
            CONCAT_WS(' ', s.nombre, s.apellido) AS socio_nombre, u.nombre AS registrado_por,
            TIMESTAMPDIFF(MINUTE, a.fecha_entrada, COALESCE(a.fecha_salida, NOW())) AS minutos_estancia
            FROM asistencias a JOIN socios s ON s.id = a.socio_id
            LEFT JOIN usuarios u ON u.id = a.registrado_por
            WHERE (CONCAT_WS(' ', s.nombre, s.apellido) LIKE %s ESCAPE '!' OR s.cedula LIKE %s ESCAPE '!')
              AND (%s IS NULL OR a.fecha_entrada >= %s)
              AND (%s IS NULL OR a.fecha_entrada <= %s)
              AND (NOT %s OR a.fecha_salida IS NULL)
              AND (NOT %s OR a.fecha_salida IS NOT NULL)
              AND (NOT %s OR s.activo = %s)
              AND (%s IS NULL OR a.fecha_entrada BETWEEN %s AND %s)
              AND s.cedula LIKE %s ESCAPE '!'
              AND CONCAT_WS(' ', s.nombre, s.apellido) LIKE %s ESCAPE '!'
              AND (%s IS NULL OR a.registrado_por = %s)
              AND (%s IS NULL OR TIME(a.fecha_entrada) = %s)
              AND (%s IS NULL OR TIME(a.fecha_salida) = %s)
            ORDER BY a.fecha_entrada DESC, a.id DESC''',
            (general, general, desde, desde, hasta, hasta, solo_en_gimnasio, solo_finalizadas,
             solo_activos, 1, entrada_desde, entrada_desde, entrada_hasta, patron(cedula), patron(socio), autor, autor,
             hora_entrada, hora_entrada, hora_salida, hora_salida))
        return cursor.fetchall()


def listar_usuarios_asistencias():
    with _cursor() as cursor:
        cursor.execute('SELECT id, nombre FROM usuarios ORDER BY nombre, id', ())
        return cursor.fetchall()


def listar_socios_para_entrada():
    with _cursor() as cursor:
        cursor.execute('''SELECT id, cedula, nombre, apellido FROM socios
                          WHERE activo = %s ORDER BY apellido, nombre, id''', (1,))
        return cursor.fetchall()


def _hora_ecuador():
    return datetime.now(ECUADOR).replace(tzinfo=None, microsecond=0)


def registrar_entrada(socio_id, usuario_id):
    socio_id, usuario_id = _id(socio_id), _id(usuario_id)
    with _cursor(escritura=True) as cursor:
        cursor.execute('SELECT activo FROM socios WHERE id = %s FOR UPDATE', (socio_id,))
        socio = cursor.fetchone()
        if socio is None:
            return False, 'El socio seleccionado no existe.'
        cursor.execute('''SELECT id FROM asistencias WHERE socio_id = %s
                          AND fecha_salida IS NULL LIMIT %s''', (socio_id, 1))
        if cursor.fetchone():
            return False, 'El socio ya tiene una entrada abierta sin marcar salida.'
        if not socio['activo']:
            return False, 'Solo puedes registrar la entrada de un socio activo.'
        cursor.execute('''SELECT id FROM membresias WHERE socio_id = %s
            AND estado = %s AND fecha_fin >= CURDATE() LIMIT %s''', (socio_id, 'activa', 1))
        vigente = cursor.fetchone() is not None
        cursor.execute('''INSERT INTO asistencias (socio_id, fecha_entrada, registrado_por)
                          VALUES (%s, %s, %s)''', (socio_id, _hora_ecuador(), usuario_id))
    mensaje = 'Entrada registrada.' if vigente else 'Entrada registrada (ADVERTENCIA: socio sin membresía activa).'
    return True, mensaje


def registrar_salida(asistencia_id):
    asistencia_id = _id(asistencia_id)
    with _cursor(escritura=True) as cursor:
        cursor.execute('SELECT fecha_entrada, fecha_salida FROM asistencias WHERE id = %s FOR UPDATE', (asistencia_id,))
        asistencia = cursor.fetchone()
        if asistencia is None or asistencia['fecha_salida'] is not None:
            return False, 'La asistencia no existe o ya tiene una salida registrada.'
        hora = _hora_ecuador()
        if hora < asistencia['fecha_entrada']:
            return False, 'La hora de salida no puede ser anterior a la entrada.'
        cursor.execute('UPDATE asistencias SET fecha_salida = %s WHERE id = %s AND fecha_salida IS NULL',
                       (hora, asistencia_id))
    return True, 'Salida registrada.'


def eliminar_asistencia(asistencia_id):
    asistencia_id = _id(asistencia_id)
    with _cursor(escritura=True) as cursor:
        cursor.execute('DELETE FROM asistencias WHERE id = %s', (asistencia_id,))
        if cursor.rowcount == 0:
            raise ErrorAsistencias('La asistencia no existe.')
    return True
