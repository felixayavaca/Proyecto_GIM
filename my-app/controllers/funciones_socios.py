import re
from datetime import date

import mysql.connector
from conexion.conexionBD import connectionBD


class ErrorSocios(Exception):
    pass


def _consultar(sql, parametros, uno=False):
    try:
        with connectionBD() as connection:
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(sql, parametros)
                return cursor.fetchone() if uno else cursor.fetchall()
    except (ConnectionError, mysql.connector.Error) as exc:
        raise ErrorSocios('No se pudo consultar los socios. Inténtalo más tarde.') from exc


def listar_socios():
    return _consultar('SELECT * FROM socios ORDER BY id DESC', ())


def obtener_socio(socio_id):
    return _consultar('SELECT * FROM socios WHERE id = %s', (socio_id,), uno=True)


def _validar(datos):
    valores = {}
    for campo, limite in [('cedula', 15), ('nombre', 60), ('apellido', 60), ('telefono', 20), ('email', 120)]:
        valor = str(datos.get(campo) or '').strip()
        if len(valor) > limite or (campo in ('cedula', 'nombre', 'apellido') and not valor):
            raise ErrorSocios(f'El campo {campo} es obligatorio o excede {limite} caracteres.')
        valores[campo] = valor or None
    if valores['email'] and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', valores['email']):
        raise ErrorSocios('El correo electrónico no es válido.')
    nacimiento = datos.get('fecha_nacimiento') or None
    if nacimiento:
        try:
            nacimiento = date.fromisoformat(str(nacimiento))
        except ValueError as exc:
            raise ErrorSocios('La fecha de nacimiento no es válida.') from exc
        if nacimiento > date.today():
            raise ErrorSocios('La fecha de nacimiento no puede ser futura.')
    return tuple(valores[c] for c in ('cedula', 'nombre', 'apellido', 'telefono', 'email')) + (nacimiento,)


def _escribir(sql, parametros, socio_id=None):
    try:
        with connectionBD() as connection:
            try:
                with connection.cursor() as cursor:
                    if socio_id is not None:
                        cursor.execute('SELECT id FROM socios WHERE id = %s FOR UPDATE', (socio_id,))
                        if cursor.fetchone() is None:
                            raise ErrorSocios('El socio no existe.')
                    cursor.execute(sql, parametros)
                    resultado = cursor.lastrowid if socio_id is None else socio_id
                connection.commit()
                return resultado
            except Exception:
                connection.rollback()
                raise
    except mysql.connector.IntegrityError as exc:
        if exc.errno == 1062:
            raise ErrorSocios('Ya existe un socio con esa cédula.') from exc
        raise ErrorSocios('No se pudo completar la operación por registros relacionados.') from exc
    except (ConnectionError, mysql.connector.Error) as exc:
        raise ErrorSocios('No se pudo guardar el cambio. Inténtalo más tarde.') from exc


def crear_socio(datos):
    return _escribir('''INSERT INTO socios
        (cedula, nombre, apellido, telefono, email, fecha_nacimiento)
        VALUES (%s, %s, %s, %s, %s, %s)''', _validar(datos))


def actualizar_socio(socio_id, datos):
    return _escribir('''UPDATE socios SET cedula = %s, nombre = %s, apellido = %s,
        telefono = %s, email = %s, fecha_nacimiento = %s WHERE id = %s''',
        _validar(datos) + (socio_id,), socio_id)


def eliminar_socio(socio_id):
    return _escribir('DELETE FROM socios WHERE id = %s', (socio_id,), socio_id)
