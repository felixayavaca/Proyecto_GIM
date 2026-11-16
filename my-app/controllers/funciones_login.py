import mysql.connector
from werkzeug.security import check_password_hash, generate_password_hash
from conexion.conexionBD import connectionBD

_HASH_FICTICIO = generate_password_hash('usuario-inexistente')


def validar_usuario(email, password):
    try:
        with connectionBD() as connection:
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute('''SELECT u.id, u.nombre, u.email, u.clave_hash, u.rol_id,
                    r.nombre AS rol_nombre FROM usuarios u JOIN roles r ON r.id = u.rol_id
                    WHERE u.email = %s AND u.activo = %s LIMIT 1''', (email, 1))
                usuario = cursor.fetchone()
                try:
                    valido = check_password_hash(usuario['clave_hash'] if usuario else _HASH_FICTICIO, password)
                except (ValueError, TypeError):
                    valido = False
                if not usuario or not valido:
                    return None
                cursor.execute('''SELECT DISTINCT p.clave FROM permisos p
                    JOIN rol_permisos rp ON rp.permiso_id = p.id
                    WHERE rp.rol_id = %s ORDER BY p.clave''', (usuario['rol_id'],))
                usuario.pop('clave_hash')
                usuario['permisos'] = [fila['clave'] for fila in cursor.fetchall()]
                return usuario
    except (ConnectionError, mysql.connector.Error) as exc:
        raise ConnectionError('No se pudo validar el usuario.') from exc
