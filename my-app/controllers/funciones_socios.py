import re
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from contextlib import contextmanager

import mysql.connector
from conexion.conexionBD import connectionBD


GENEROS = ('M', 'F', 'Otro')
METODOS_PAGO = ('Efectivo', 'Transferencia', 'Tarjeta')


class ErrorSocios(Exception):
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
        mensaje = ('Ya existe un socio con esa cédula.' if exc.errno == 1062
                   else 'El referente, instructor, socio o plan seleccionado no existe.')
        raise ErrorSocios(mensaje) from exc
    except (ConnectionError, mysql.connector.Error) as exc:
        raise ErrorSocios('No se pudo completar la operación de socios.') from exc


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


def _patron(texto):
    return '%' + (texto or '').strip().replace('!', '!!').replace('%', '!%').replace('_', '!_') + '%'


def _filtros(q, estado, genero, instructor_id):
    if estado not in (None, '', 0, 1, '0', '1') or genero not in (None, '', *GENEROS):
        raise ValueError('Selecciona filtros válidos.')
    estado = None if estado in (None, '') else int(estado)
    genero = genero or None
    instructor_id = _id(instructor_id, opcional=True)
    patron = _patron(q)
    return patron, patron, patron, estado, estado, genero, genero, instructor_id, instructor_id


_FILTROS = """WHERE (CONCAT_WS(' ', s.nombre, s.apellido) LIKE %s ESCAPE '!'
                     OR s.cedula LIKE %s ESCAPE '!' OR COALESCE(s.email, '') LIKE %s ESCAPE '!')
                AND (%s IS NULL OR s.activo = %s)
                AND (%s IS NULL OR s.genero = %s)
                AND (%s IS NULL OR s.instructor_id = %s)"""


def listar_socios(q=None, estado=None, genero=None, instructor_id=None, *,
                 cedula=None, socio=None, contacto=None, referente=None, plan_vigente=None,
                 dias_restantes=None, antiguedad_min=None, fecha_ingreso=None):
    parametros = _filtros(q, estado, genero, instructor_id)
    if dias_restantes not in (None, '', 'por_vencer', 'vigentes', 'sin_vigencia'):
        raise ValueError('Selecciona un filtro válido de días restantes.')
    sin_plan = plan_vigente == 'sin_plan'
    plan_id = None if sin_plan else _id(plan_vigente, opcional=True)
    try:
        antiguedad = int(str(antiguedad_min)) if antiguedad_min not in (None, '') else None
        if antiguedad is not None and not 0 <= antiguedad <= 2147483647:
            raise ValueError
    except ValueError as exc:
        raise ValueError('Indica una antigüedad mínima válida.') from exc
    contacto = _patron(contacto)
    try:
        ingreso = date.fromisoformat(str(fecha_ingreso)) if fecha_ingreso else None
        if ingreso and ingreso.year < 1000:
            raise ValueError
    except ValueError as exc:
        raise ValueError('Indica una fecha de ingreso válida.') from exc
    with _cursor() as cursor:
        cursor.execute(
            """SELECT s.*, CONCAT_WS(' ', i.nombre, i.apellido) AS instructor_nombre,
                      CONCAT_WS(' ', r.nombre, r.apellido) AS referente_nombre,
                      p.nombre AS plan_actual, m.plan_id AS plan_actual_id, m.fecha_fin,
                      DATEDIFF(m.fecha_fin, CURDATE()) AS dias_restantes,
                      DATEDIFF(CURDATE(), s.fecha_registro) AS antiguedad
               FROM socios s
               LEFT JOIN instructores i ON i.id = s.instructor_id
               LEFT JOIN socios r ON r.id = s.referido_por_socio_id
               LEFT JOIN membresias m ON m.id = (
                   SELECT mx.id FROM membresias mx WHERE mx.socio_id = s.id AND mx.estado = %s
                   AND CURDATE() BETWEEN mx.fecha_inicio AND mx.fecha_fin
                   ORDER BY mx.fecha_inicio DESC, mx.id DESC LIMIT 1
               )
               LEFT JOIN planes p ON p.id = m.plan_id
            """ + _FILTROS + """
                AND s.cedula LIKE %s ESCAPE '!'
                AND CONCAT_WS(' ', s.nombre, s.apellido) LIKE %s ESCAPE '!'
                AND (COALESCE(s.telefono, '') LIKE %s ESCAPE '!' OR COALESCE(s.email, '') LIKE %s ESCAPE '!')
                AND CONCAT_WS(' ', r.nombre, r.apellido) LIKE %s ESCAPE '!'
                AND (%s IS NULL OR m.plan_id = %s)
                AND (NOT %s OR m.id IS NULL)
                AND CASE %s
                    WHEN 'por_vencer' THEN DATEDIFF(m.fecha_fin, CURDATE()) BETWEEN 0 AND 7
                    WHEN 'vigentes' THEN DATEDIFF(m.fecha_fin, CURDATE()) > 7
                    WHEN 'sin_vigencia' THEN m.id IS NULL
                    ELSE TRUE END
                AND (%s IS NULL OR DATEDIFF(CURDATE(), s.fecha_registro) >= %s)
                AND (%s IS NULL OR s.fecha_registro = %s)
                ORDER BY s.id DESC""",
            ('activa', *parametros, _patron(cedula), _patron(socio), contacto, contacto,
             _patron(referente), plan_id, plan_id, sin_plan, dias_restantes, antiguedad, antiguedad, ingreso, ingreso),
        )
        return cursor.fetchall()


def listar_pagos(q=None, estado=None, genero=None, instructor_id=None, *,
                 pago_socio=None, pago_plan=None, pago_metodo=None, pago_fecha=None):
    parametros = _filtros(q, estado, genero, instructor_id)
    plan = _id(pago_plan, opcional=True)
    if pago_metodo not in (None, '', *METODOS_PAGO):
        raise ValueError('Selecciona un método de pago válido.')
    metodo = pago_metodo or None
    try:
        fecha = date.fromisoformat(str(pago_fecha)) if pago_fecha else None
        if fecha and fecha.year < 1000:
            raise ValueError
    except ValueError as exc:
        raise ValueError('Indica una fecha de pago válida.') from exc
    with _cursor() as cursor:
        cursor.execute(
            """SELECT m.id, m.socio_id, m.plan_id, s.cedula, CONCAT_WS(' ', s.nombre, s.apellido) AS socio_nombre,
                      p.nombre AS plan_nombre, m.fecha_inicio, m.fecha_fin, m.estado, m.fecha_pago,
                      m.metodo_pago, m.precio_pagado,
                      DATEDIFF(m.fecha_fin, m.fecha_inicio) AS duracion_dias,
                      DATEDIFF(DATE(m.fecha_pago), s.fecha_registro) AS antiguedad
               FROM membresias m JOIN socios s ON s.id = m.socio_id JOIN planes p ON p.id = m.plan_id
            """ + _FILTROS + """
                AND CONCAT_WS(' ', s.nombre, s.apellido) LIKE %s ESCAPE '!'
                AND (%s IS NULL OR m.plan_id = %s)
                AND (%s IS NULL OR m.metodo_pago = %s)
                AND (%s IS NULL OR DATE(m.fecha_pago) = %s)
                ORDER BY m.fecha_pago DESC, m.id DESC""",
            (*parametros, _patron(pago_socio), plan, plan, metodo, metodo, fecha, fecha),
        )
        return cursor.fetchall()


def listar_planes_filtro():
    with _cursor() as cursor:
        cursor.execute('SELECT id, nombre FROM planes ORDER BY nombre, id', ())
        return cursor.fetchall()


def listar_opciones_socios():
    with _cursor() as cursor:
        cursor.execute('SELECT id, cedula, nombre, apellido FROM socios ORDER BY apellido, nombre')
        referentes = cursor.fetchall()
        cursor.execute('SELECT id, nombre, apellido, especialidad, activo FROM instructores ORDER BY apellido, nombre')
        return referentes, cursor.fetchall()


def obtener_socio(socio_id):
    with _cursor() as cursor:
        cursor.execute('SELECT * FROM socios WHERE id = %s', (socio_id,))
        return cursor.fetchone()


def validar_cedula_telefono(cedula, telefono):
    if not isinstance(cedula, str) or not re.fullmatch(r'\d{10}', cedula, flags=re.ASCII):
        raise ValueError('La cédula debe tener exactamente 10 dígitos numéricos.')
    provincia = int(cedula[:2])
    if provincia != 30 and not 1 <= provincia <= 24:
        raise ValueError('El código de provincia de la cédula debe estar entre 01 y 24, o ser 30.')
    suma = 0
    for posicion, digito in enumerate(cedula[:9]):
        producto = int(digito) * (2 if posicion % 2 == 0 else 1)
        suma += producto - 9 if producto > 9 else producto
    if int(cedula[-1]) != (-suma) % 10:
        raise ValueError('El dígito verificador de la cédula no es válido.')
    if not isinstance(telefono, str) or not re.fullmatch(r'09\d{8}', telefono, flags=re.ASCII):
        raise ValueError('El teléfono es obligatorio y debe tener 10 dígitos comenzando con 09.')


def _validar(datos, socio_id=None):
    cedula = datos.get('cedula')
    telefono = datos.get('telefono')
    validar_cedula_telefono(cedula, telefono)
    genero = datos.get('genero')
    if genero not in GENEROS:
        raise ValueError('Selecciona un género válido.')
    nombre, apellido, email = (datos.get(campo, '').strip() for campo in ('nombre', 'apellido', 'email'))
    for campo, valor in (('nombre', nombre), ('apellido', apellido)):
        if not re.fullmatch(r'[A-Za-zÁÉÍÓÚáéíóúÑñÜü\s]{2,60}', valor):
            raise ValueError(f'El {campo} debe tener entre 2 y 60 caracteres, solo letras y espacios.')
    if email and (len(email) > 120 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email)):
        raise ValueError('El correo electrónico no es válido.')
    nacimiento = datos.get('fecha_nacimiento') or None
    if nacimiento is not None:
        try:
            nacimiento = date.fromisoformat(str(nacimiento))
            if nacimiento.year < 1000 or nacimiento > date.today():
                raise ValueError
        except ValueError as exc:
            raise ValueError('Indica una fecha de nacimiento válida.') from exc
    referente = _id(datos.get('referido_por_socio_id'), opcional=True)
    instructor = _id(datos.get('instructor_id'), opcional=True)
    if referente is not None and referente == socio_id:
        raise ValueError('Un socio no puede ser su propio referente.')
    return cedula, nombre, apellido, genero, telefono, email or None, nacimiento, referente, instructor


def _bloquear_socio(cursor, socio_id):
    cursor.execute('SELECT activo FROM socios WHERE id = %s FOR UPDATE', (socio_id,))
    socio = cursor.fetchone()
    if socio is None:
        raise ValueError('El socio no existe.')
    return socio


def crear_socio(datos):
    valores = _validar(datos)
    with _cursor(escritura=True) as cursor:
        cursor.execute(
            """INSERT INTO socios (cedula, nombre, apellido, genero, telefono, email, fecha_nacimiento,
                                   referido_por_socio_id, instructor_id)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""", valores,
        )
        return cursor.lastrowid


def actualizar_socio(socio_id, datos):
    valores = _validar(datos, socio_id)
    with _cursor(escritura=True) as cursor:
        _bloquear_socio(cursor, socio_id)
        cursor.execute(
            """UPDATE socios SET cedula=%s, nombre=%s, apellido=%s, genero=%s, telefono=%s, email=%s,
                      fecha_nacimiento=%s, referido_por_socio_id=%s, instructor_id=%s WHERE id=%s""",
            (*valores, socio_id),
        )


def cambiar_estado_socio(socio_id, activo):
    if str(activo) not in ('0', '1'):
        raise ValueError('Selecciona un estado válido.')
    with _cursor(escritura=True) as cursor:
        _bloquear_socio(cursor, socio_id)
        cursor.execute('UPDATE socios SET activo = %s WHERE id = %s', (int(activo), socio_id))


def _precio(valor):
    try:
        precio = Decimal(str(valor))
        if precio.is_finite() and 0 <= precio <= Decimal('999999.99') and precio == precio.quantize(Decimal('0.01')):
            return precio
    except InvalidOperation:
        pass
    raise ValueError('Indica un precio válido con hasta dos decimales.')


def registrar_pago(socio_id, datos):
    plan_id = _id(datos.get('plan_id'))
    metodo = datos.get('metodo_pago')
    if metodo not in METODOS_PAGO:
        raise ValueError('Selecciona un método de pago válido.')
    precio = _precio(datos.get('precio_pagado'))
    try:
        inicio = date.fromisoformat(datos.get('fecha_inicio', ''))
        pago = datetime.fromisoformat(datos['fecha_pago']) if datos.get('fecha_pago') else None
        if inicio.year < 1000 or (pago and (pago.tzinfo is not None or pago.year < 1000)):
            raise ValueError
    except ValueError as exc:
        raise ValueError('Indica fechas válidas en la hora local del gimnasio.') from exc
    with _cursor(escritura=True) as cursor:
        if not _bloquear_socio(cursor, socio_id)['activo']:
            raise ValueError('Activa al socio antes de asignarle una membresía.')
        cursor.execute('SELECT duracion_dias FROM planes WHERE id = %s AND activo = %s FOR SHARE', (plan_id, 1))
        plan = cursor.fetchone()
        if plan is None:
            raise ValueError('Selecciona un plan activo.')
        try:
            fin = inicio + timedelta(days=plan['duracion_dias'])
        except (OverflowError, ValueError) as exc:
            raise ValueError('La duración del plan excede el rango de fechas.') from exc
        cursor.execute(
            """INSERT INTO membresias (socio_id, plan_id, fecha_inicio, fecha_fin, precio_pagado,
                                       metodo_pago, fecha_pago, estado)
               VALUES (%s, %s, %s, %s, %s, %s, COALESCE(%s, NOW()), IF(%s < CURDATE(), %s, %s))""",
            (socio_id, plan_id, inicio, fin, precio, metodo, pago, fin, 'vencida', 'activa'),
        )
        return cursor.lastrowid
