import mysql.connector
from conexion.conexionBD import connectionBD


def obtener_resumen():
    try:
        with connectionBD() as connection:
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute('''SELECT
                    (SELECT COUNT(DISTINCT socio_id) FROM membresias
                     WHERE estado = %s AND CURDATE() BETWEEN fecha_inicio AND fecha_fin) AS socios_activos,
                    (SELECT COUNT(*) FROM membresias
                     WHERE estado = %s AND CURDATE() BETWEEN fecha_inicio AND fecha_fin) AS membresias_vigentes,
                    (SELECT COUNT(*) FROM asistencias WHERE fecha_hora >= CURDATE()
                     AND fecha_hora < CURDATE() + INTERVAL %s DAY) AS asistencias_hoy''',
                    ('activa', 'activa', 1))
                return cursor.fetchone()
    except (ConnectionError, mysql.connector.Error) as exc:
        raise ConnectionError('No se pudo cargar el resumen.') from exc
