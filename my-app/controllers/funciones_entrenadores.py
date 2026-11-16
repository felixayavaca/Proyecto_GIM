from contextlib import contextmanager
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

import mysql.connector

from conexion.conexionBD import connectionBD


DIAS = ('Lunes', 'Martes', 'Miercoles', 'Jueves', 'Viernes', 'Sabado')
RANGOS_IMC = {
    'bajo': (None, Decimal('18.5')),
    'normal': (Decimal('18.5'), 25),
    'sobrepeso': (25, 30),
    'obesidad': (30, None),
}


class ErrorEntrenadores(Exception):
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
        raise ErrorEntrenadores('El socio o instructor seleccionado ya no está disponible.') from exc
    except (ConnectionError, mysql.connector.Error) as exc:
        raise ErrorEntrenadores('No se pudo completar la operación de entrenamiento.') from exc


def _id(valor, opcional=False):
    if opcional and valor in (None, ''):
        return None
    try:
        numero = int(str(valor))
        if 1 <= numero <= 2147483647:
            return numero
    except ValueError:
        pass
    raise ValueError('Selecciona un registro válido.')


def listar_valoraciones(socio_id=None, *, fecha=None, instructor_id=None, clasificacion=None):
    socio_id = _id(socio_id, opcional=True)
    instructor_id = _id(instructor_id, opcional=True)
    try:
        fecha = date.fromisoformat(str(fecha)) if fecha else None
        if fecha and fecha.year < 1000:
            raise ValueError
    except ValueError as exc:
        raise ValueError('Indica una fecha de valoración válida.') from exc
    if clasificacion and clasificacion not in RANGOS_IMC:
        raise ValueError('Selecciona una clasificación de IMC válida.')
    minimo, maximo = RANGOS_IMC.get(clasificacion, (None, None))
    with _cursor() as cursor:
        cursor.execute(
            """SELECT v.*, s.cedula, CONCAT_WS(' ', s.nombre, s.apellido) AS socio_nombre,
                      CONCAT_WS(' ', i.nombre, i.apellido) AS instructor_nombre
               FROM valoraciones_fisicas v JOIN socios s ON s.id = v.socio_id
               JOIN instructores i ON i.id = v.instructor_id
               WHERE (%s IS NULL OR v.socio_id = %s) AND (%s IS NULL OR v.fecha = %s)
                 AND (%s IS NULL OR v.instructor_id = %s)
                 AND (%s IS NULL OR v.imc >= %s) AND (%s IS NULL OR v.imc < %s)
               ORDER BY v.fecha DESC, v.id DESC""",
            (socio_id, socio_id, fecha, fecha, instructor_id, instructor_id, minimo, minimo, maximo, maximo),
        )
        return cursor.fetchall()


def listar_rutinas(socio_id=None, dia_semana=None, *, grupo_muscular=None, instructor_id=None, activa=None):
    socio_id = _id(socio_id, opcional=True)
    instructor_id = _id(instructor_id, opcional=True)
    activa = '' if activa is None else str(activa)
    if activa not in ('', '0', '1'):
        raise ValueError('Selecciona un estado de rutina válido.')
    estado = int(activa) if activa else None
    grupo = '%' + (grupo_muscular or '').strip().replace('!', '!!').replace('%', '!%').replace('_', '!_') + '%'
    dia_semana = dia_semana or None
    if dia_semana is not None and dia_semana not in DIAS:
        raise ValueError('Selecciona un día válido.')
    with _cursor() as cursor:
        cursor.execute(
            """SELECT r.*, s.cedula, CONCAT_WS(' ', s.nombre, s.apellido) AS socio_nombre,
                      CONCAT_WS(' ', i.nombre, i.apellido) AS instructor_nombre
               FROM rutinas_ejercicios r JOIN socios s ON s.id = r.socio_id
               JOIN instructores i ON i.id = r.instructor_id
               WHERE (%s IS NULL OR r.socio_id = %s) AND (%s IS NULL OR r.dia_semana = %s)
                 AND r.grupo_muscular LIKE %s ESCAPE '!'
                 AND (%s IS NULL OR r.instructor_id = %s) AND (%s IS NULL OR r.activa = %s)
               ORDER BY s.apellido, s.nombre, s.id, r.dia_semana, r.id""",
            (socio_id, socio_id, dia_semana, dia_semana, grupo, instructor_id, instructor_id, estado, estado),
        )
        return cursor.fetchall()


def listar_socios_entrenamiento():
    with _cursor() as cursor:
        cursor.execute('SELECT id, cedula, nombre, apellido FROM socios ORDER BY apellido, nombre, id', ())
        return cursor.fetchall()


def listar_instructores_entrenamiento(usuario_id=None):
    with _cursor() as cursor:
        cursor.execute(
            """SELECT id, nombre, apellido, activo FROM instructores
               WHERE (%s IS NULL OR usuario_id = %s)
               ORDER BY apellido, nombre, id""",
            (usuario_id, usuario_id),
        )
        return cursor.fetchall()


def _medida(valor, minimo, maximo, nombre):
    try:
        medida = Decimal(str(valor))
        if medida.is_finite() and minimo <= medida <= maximo and medida == medida.quantize(Decimal('0.01')):
            return medida
    except InvalidOperation:
        pass
    raise ValueError(f'Indica un valor válido para {nombre}, con hasta dos decimales.')


def _texto(valor, limite, nombre, requerido=False):
    texto = (valor or '').strip()
    if (requerido and not texto) or len(texto) > limite:
        raise ValueError(f'Completa {nombre} con hasta {limite} caracteres.')
    return texto or None


def crear_valoracion(socio_id, instructor_id, fecha, peso_kg, estatura_cm, porcentaje_grasa, observaciones):
    socio_id, instructor_id = _id(socio_id), _id(instructor_id)
    try:
        fecha = date.fromisoformat(str(fecha))
        if fecha.year < 1000:
            raise ValueError
    except ValueError as exc:
        raise ValueError('Indica una fecha de valoración válida.') from exc
    peso = _medida(peso_kg, Decimal('0.01'), Decimal('999.99'), 'el peso')
    estatura = _medida(estatura_cm, Decimal('0.01'), Decimal('999.99'), 'la estatura')
    grasa = None if porcentaje_grasa in (None, '') else _medida(porcentaje_grasa, 0, 100, 'el porcentaje de grasa')
    imc = (peso / ((estatura / 100) ** 2)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    if not Decimal('0.01') <= imc <= Decimal('999.99'):
        raise ValueError('El peso y la estatura generan un IMC fuera del rango permitido.')
    observaciones = _texto(observaciones, 10000, 'las observaciones')
    with _cursor(escritura=True) as cursor:
        cursor.execute(
            """INSERT INTO valoraciones_fisicas
               (socio_id, instructor_id, fecha, peso_kg, estatura_cm, imc, porcentaje_grasa, observaciones)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (socio_id, instructor_id, fecha, peso, estatura, imc, grasa, observaciones),
        )
        return cursor.lastrowid


def crear_rutina(socio_id, instructor_id, dia_semana, grupo_muscular, ejercicios_detalle):
    socio_id, instructor_id = _id(socio_id), _id(instructor_id)
    if dia_semana not in DIAS:
        raise ValueError('Selecciona un día válido.')
    grupo = _texto(grupo_muscular, 60, 'el grupo muscular', requerido=True)
    detalle = _texto(ejercicios_detalle, 10000, 'los ejercicios', requerido=True)
    with _cursor(escritura=True) as cursor:
        cursor.execute(
            """INSERT INTO rutinas_ejercicios (socio_id, instructor_id, dia_semana, grupo_muscular, ejercicios_detalle, activa)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (socio_id, instructor_id, dia_semana, grupo, detalle, 1),
        )
        return cursor.lastrowid


def cambiar_estado_rutina(rutina_id, activa):
    if str(activa) not in ('0', '1'):
        raise ValueError('Selecciona un estado válido.')
    with _cursor(escritura=True) as cursor:
        cursor.execute('SELECT id FROM rutinas_ejercicios WHERE id = %s FOR UPDATE', (_id(rutina_id),))
        if cursor.fetchone() is None:
            raise ValueError('La rutina no existe.')
        cursor.execute('UPDATE rutinas_ejercicios SET activa = %s WHERE id = %s', (int(activa), rutina_id))
