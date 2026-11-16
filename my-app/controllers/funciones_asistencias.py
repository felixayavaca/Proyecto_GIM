from contextlib import contextmanager

import mysql.connector
from conexion.conexionBD import connectionBD


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


def listar_asistencias():
    with _cursor() as cursor:
        cursor.execute('''SELECT a.id, a.fecha_hora, s.cedula,
            CONCAT(s.nombre, ' ', s.apellido) AS socio_nombre,
            u.nombre AS registrado_por
            FROM asistencias a JOIN socios s ON s.id = a.socio_id
            LEFT JOIN usuarios u ON u.id = a.registrado_por
            ORDER BY a.fecha_hora DESC, a.id DESC LIMIT %s''', (100,))
        return cursor.fetchall()


def registrar_asistencia(socio_id, usuario_id):
    socio_id, usuario_id = _id(socio_id), _id(usuario_id)
    with _cursor(escritura=True) as cursor:
        cursor.execute('SELECT id FROM socios WHERE id = %s FOR SHARE', (socio_id,))
        if not cursor.fetchone():
            raise ErrorAsistencias('El socio seleccionado no existe.')
        cursor.execute('''SELECT id FROM membresias WHERE socio_id = %s
            AND estado = %s AND fecha_fin >= CURDATE() LIMIT %s''', (socio_id, 'activa', 1))
        vigente = cursor.fetchone() is not None
        cursor.execute('INSERT INTO asistencias (socio_id, registrado_por) VALUES (%s, %s)', (socio_id, usuario_id))
    mensaje = 'Asistencia registrada' if vigente else 'Asistencia registrada (ADVERTENCIA: socio sin membresía activa)'
    return True, mensaje


def eliminar_asistencia(asistencia_id):
    asistencia_id = _id(asistencia_id)
    with _cursor(escritura=True) as cursor:
        cursor.execute('DELETE FROM asistencias WHERE id = %s', (asistencia_id,))
        if cursor.rowcount == 0:
            raise ErrorAsistencias('La asistencia no existe.')
    return True
