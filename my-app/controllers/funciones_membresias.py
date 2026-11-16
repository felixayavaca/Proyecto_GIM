from contextlib import contextmanager
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

import mysql.connector
from conexion.conexionBD import connectionBD


class ErrorMembresias(Exception):
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
        mensaje = 'Ya existe un plan con ese nombre.' if exc.errno == 1062 else 'El socio o plan no existe, o hay registros relacionados.'
        raise ErrorMembresias(mensaje) from exc
    except (ConnectionError, mysql.connector.Error) as exc:
        raise ErrorMembresias('No se pudo completar la operación. Inténtalo más tarde.') from exc


def _id(valor):
    try:
        numero = int(str(valor))
        if numero <= 0 or numero > 2147483647:
            raise ValueError
        return numero
    except (ValueError, TypeError) as exc:
        raise ErrorMembresias('Selecciona un registro válido.') from exc


def listar_membresias():
    with _cursor() as cursor:
        cursor.execute('''SELECT m.id, CONCAT(s.nombre, ' ', s.apellido) AS socio_nombre,
            s.cedula, p.nombre AS plan_nombre, m.fecha_inicio, m.fecha_fin,
            m.precio_pagado, m.estado, DATEDIFF(m.fecha_fin, CURDATE()) AS dias_restantes
            FROM membresias m JOIN socios s ON s.id = m.socio_id
            JOIN planes p ON p.id = m.plan_id ORDER BY m.id DESC''', ())
        return cursor.fetchall()


def listar_planes():
    with _cursor() as cursor:
        cursor.execute('SELECT id, nombre, precio, duracion_dias FROM planes ORDER BY nombre', ())
        return cursor.fetchall()


def crear_plan(nombre, precio, duracion_dias):
    nombre = str(nombre or '').strip()
    if not nombre or len(nombre) > 50:
        raise ErrorMembresias('El nombre del plan es obligatorio y admite hasta 50 caracteres.')
    try:
        precio = Decimal(str(precio))
        duracion = int(str(duracion_dias))
        if not precio.is_finite() or precio < 0 or precio > Decimal('999999.99'):
            raise ValueError
        if precio != precio.quantize(Decimal('0.01')) or not 1 <= duracion <= 2147483647:
            raise ValueError
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ErrorMembresias('Indica un precio no negativo con hasta dos decimales y una duración entera positiva.') from exc
    with _cursor(escritura=True) as cursor:
        cursor.execute('INSERT INTO planes (nombre, precio, duracion_dias) VALUES (%s, %s, %s)', (nombre, precio, duracion))
        return cursor.lastrowid


def crear_membresia(socio_id, plan_id, fecha_inicio):
    socio_id, plan_id = _id(socio_id), _id(plan_id)
    try:
        inicio = date.fromisoformat(str(fecha_inicio))
        if inicio.year < 1000:
            raise ValueError
    except (ValueError, TypeError) as exc:
        raise ErrorMembresias('Indica una fecha de inicio válida.') from exc
    with _cursor(escritura=True) as cursor:
        cursor.execute('SELECT precio, duracion_dias FROM planes WHERE id = %s FOR SHARE', (plan_id,))
        plan = cursor.fetchone()
        if not plan:
            raise ErrorMembresias('El plan seleccionado no existe.')
        cursor.execute('SELECT id FROM socios WHERE id = %s FOR SHARE', (socio_id,))
        if not cursor.fetchone():
            raise ErrorMembresias('El socio seleccionado no existe.')
        try:
            fin = inicio + timedelta(days=plan['duracion_dias'])
        except (OverflowError, ValueError) as exc:
            raise ErrorMembresias('La duración del plan excede el rango de fechas permitido.') from exc
        cursor.execute('''INSERT INTO membresias
            (socio_id, plan_id, fecha_inicio, fecha_fin, precio_pagado, estado)
            VALUES (%s, %s, %s, %s, %s, %s)''',
            (socio_id, plan_id, inicio, fin, plan['precio'], 'activa'))
        return cursor.lastrowid


def _modificar(membresia_id, sql, parametros):
    membresia_id = _id(membresia_id)
    with _cursor(escritura=True) as cursor:
        cursor.execute('SELECT id FROM membresias WHERE id = %s FOR UPDATE', (membresia_id,))
        if not cursor.fetchone():
            raise ErrorMembresias('La membresía no existe.')
        cursor.execute(sql, parametros + (membresia_id,))
    return membresia_id


def cambiar_estado_membresia(membresia_id, nuevo_estado):
    if nuevo_estado not in ('activa', 'vencida', 'cancelada'):
        raise ErrorMembresias('El estado seleccionado no es válido.')
    return _modificar(membresia_id, 'UPDATE membresias SET estado = %s WHERE id = %s', (nuevo_estado,))


def eliminar_membresia(membresia_id):
    return _modificar(membresia_id, 'DELETE FROM membresias WHERE id = %s', ())
