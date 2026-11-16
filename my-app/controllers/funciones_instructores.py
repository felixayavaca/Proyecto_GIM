import re
from contextlib import contextmanager
from datetime import date

import mysql.connector

from conexion.conexionBD import connectionBD


class ErrorInstructores(Exception):
    pass


@contextmanager
def _cursor(escritura=False):
    try:
        with connectionBD() as conexion:
            try:
                with conexion.cursor(dictionary=True, buffered=True) as cursor:
                    yield cursor
                if escritura:
                    conexion.commit()
            except Exception:
                if escritura:
                    conexion.rollback()
                raise
    except mysql.connector.IntegrityError as exc:
        if exc.errno == 1062:
            mensaje = ('Ese usuario ya está vinculado a otro instructor.'
                       if 'usuario_id' in exc.msg else 'Ya existe un instructor con esa cédula.')
            raise ErrorInstructores(mensaje) from exc
        raise ErrorInstructores('No se pudo guardar el instructor por sus registros asociados.') from exc
    except (ConnectionError, mysql.connector.Error) as exc:
        raise ErrorInstructores('No se pudo completar la operación de instructores.') from exc


def listar_instructores(q=None, estado=None):
    q = (q or '').strip()
    estado = '' if estado is None else str(estado)
    if estado not in ('', '0', '1'):
        raise ValueError('Selecciona un estado válido.')
    patron = '%' + q.replace('!', '!!').replace('%', '!%').replace('_', '!_') + '%'
    with _cursor() as cursor:
        cursor.execute(
            """SELECT i.id, i.usuario_id, i.cedula, i.nombre, i.apellido, i.telefono,
                      i.especialidad, i.fecha_contratacion, i.activo, u.email AS usuario_email,
                      COALESCE(asignados.total, 0) AS socios_asignados
               FROM instructores i
               LEFT JOIN usuarios u ON u.id = i.usuario_id
               LEFT JOIN (
                   SELECT s.instructor_id, COUNT(s.id) AS total FROM socios s
                   GROUP BY s.instructor_id
               ) asignados ON asignados.instructor_id = i.id
               WHERE (%s = '' OR CONCAT_WS(' ', i.nombre, i.apellido) LIKE %s ESCAPE '!'
                      OR i.cedula LIKE %s ESCAPE '!' OR i.especialidad LIKE %s ESCAPE '!')
                 AND (%s IS NULL OR i.activo = %s)
               ORDER BY i.apellido, i.nombre, i.id""",
            (q, patron, patron, patron, int(estado) if estado else None, int(estado) if estado else None),
        )
        return cursor.fetchall()


def listar_usuarios_entrenadores():
    with _cursor() as cursor:
        cursor.execute(
            """SELECT u.id, u.nombre, u.email FROM usuarios u JOIN roles r ON r.id = u.rol_id
               LEFT JOIN instructores i ON i.usuario_id = u.id
               WHERE r.nombre = %s AND i.id IS NULL ORDER BY u.nombre, u.id""",
            ('Entrenador',),
        )
        return cursor.fetchall()


def _estado(activo):
    if str(activo) not in ('0', '1'):
        raise ErrorInstructores('Selecciona un estado válido.')
    return int(activo)


def _validar(datos):
    cedula = (datos.get('cedula') or '').strip()
    telefono = (datos.get('telefono') or '').strip()
    if not re.fullmatch(r'[0-9]{10}', cedula):
        raise ErrorInstructores('La cédula debe tener 10 dígitos.')
    if telefono and not re.fullmatch(r'09[0-9]{8}', telefono):
        raise ErrorInstructores('El teléfono debe tener 10 dígitos y comenzar con 09.')
    nombre = (datos.get('nombre') or '').strip()
    apellido = (datos.get('apellido') or '').strip()
    especialidad = (datos.get('especialidad') or '').strip()
    if not (1 <= len(nombre) <= 60 and 1 <= len(apellido) <= 60 and 1 <= len(especialidad) <= 80):
        raise ErrorInstructores('Completa el nombre, apellido y especialidad con sus longitudes permitidas.')
    try:
        contratacion = date.fromisoformat(str(datos.get('fecha_contratacion')))
        if contratacion.year < 1000:
            raise ValueError
    except ValueError as exc:
        raise ErrorInstructores('Indica una fecha de contratación válida.') from exc
    try:
        usuario_id = int(datos['usuario_id']) if datos.get('usuario_id') else None
        if usuario_id is not None and not 1 <= usuario_id <= 2147483647:
            raise ValueError
    except (TypeError, ValueError) as exc:
        raise ErrorInstructores('Selecciona un usuario válido.') from exc
    return usuario_id, cedula, nombre, apellido, telefono or None, especialidad, contratacion, _estado(datos.get('activo', 1))


def _verificar_usuario(cursor, usuario_id):
    if usuario_id is not None:
        cursor.execute(
            """SELECT u.id FROM usuarios u JOIN roles r ON r.id = u.rol_id
               WHERE u.id = %s AND r.nombre = %s FOR SHARE""",
            (usuario_id, 'Entrenador'),
        )
        if not cursor.fetchone():
            raise ErrorInstructores('La cuenta seleccionada debe pertenecer a un Entrenador.')


def _buscar_para_editar(cursor, instructor_id):
    cursor.execute('SELECT usuario_id FROM instructores WHERE id = %s FOR UPDATE', (instructor_id,))
    instructor = cursor.fetchone()
    if instructor is None:
        raise ErrorInstructores('El instructor no existe.')
    return instructor


def crear_instructor(datos):
    valores = _validar(datos)
    with _cursor(escritura=True) as cursor:
        _verificar_usuario(cursor, valores[0])
        cursor.execute(
            """INSERT INTO instructores
               (usuario_id, cedula, nombre, apellido, telefono, especialidad, fecha_contratacion, activo)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            valores,
        )
        return cursor.lastrowid


def actualizar_instructor(instructor_id, datos):
    valores = _validar(datos)
    with _cursor(escritura=True) as cursor:
        instructor = _buscar_para_editar(cursor, instructor_id)
        if instructor['usuario_id'] != valores[0]:
            _verificar_usuario(cursor, valores[0])
        cursor.execute(
            """UPDATE instructores SET usuario_id = %s, cedula = %s, nombre = %s, apellido = %s,
               telefono = %s, especialidad = %s, fecha_contratacion = %s, activo = %s WHERE id = %s""",
            valores + (instructor_id,),
        )


def cambiar_estado_instructor(instructor_id, activo):
    activo = _estado(activo)
    with _cursor(escritura=True) as cursor:
        _buscar_para_editar(cursor, instructor_id)
        cursor.execute('UPDATE instructores SET activo = %s WHERE id = %s', (activo, instructor_id))
