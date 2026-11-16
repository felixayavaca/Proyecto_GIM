-- =====================================================
-- GIM: SISTEMA DE GESTIÓN PARA UN GIMNASIO
-- MySQL 8.0 | UTF-8 | Zona horaria America/Guayaquil (-05:00)
--
-- ADVERTENCIA: el script crea tablas y carga datos de ejemplo.
-- No elimina la base existente. Revisar antes de ejecutarlo
-- en una base que ya contenga información.
--
-- Para eliminar la base manualmente, descomentar:
-- DROP DATABASE IF EXISTS GIM;
-- =====================================================

SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;
SET time_zone = '-05:00';

CREATE DATABASE IF NOT EXISTS GIM
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;
USE GIM;

-- =====================================================
-- 1. DDL: TABLAS, CLAVES, RESTRICCIONES E ÍNDICES
-- Orden de creación: primero las tablas referenciadas.
-- =====================================================

CREATE TABLE roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(30) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE permisos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    clave VARCHAR(50) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE rol_permisos (
    rol_id INT NOT NULL,
    permiso_id INT NOT NULL,
    PRIMARY KEY (rol_id, permiso_id),
    CONSTRAINT fk_rol_permisos_rol
        FOREIGN KEY (rol_id) REFERENCES roles(id) ON DELETE CASCADE,
    CONSTRAINT fk_rol_permisos_permiso
        FOREIGN KEY (permiso_id) REFERENCES permisos(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    clave_hash VARCHAR(255) NOT NULL,
    rol_id INT NOT NULL,
    activo TINYINT(1) NOT NULL DEFAULT 1,
    CONSTRAINT fk_usuarios_rol
        FOREIGN KEY (rol_id) REFERENCES roles(id),
    CONSTRAINT chk_usuarios_activo CHECK (activo IN (0, 1)),
    INDEX idx_usuarios_rol (rol_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE instructores (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NULL UNIQUE,
    cedula VARCHAR(15) NOT NULL UNIQUE,
    nombre VARCHAR(60) NOT NULL,
    apellido VARCHAR(60) NOT NULL,
    telefono VARCHAR(20),
    especialidad VARCHAR(80) NOT NULL,
    fecha_contratacion DATE NOT NULL,
    activo TINYINT(1) NOT NULL DEFAULT 1,
    CONSTRAINT fk_instructores_usuario
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL,
    CONSTRAINT chk_instructores_activo CHECK (activo IN (0, 1)),
    INDEX idx_instructores_especialidad (especialidad)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE socios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cedula VARCHAR(15) NOT NULL UNIQUE,
    nombre VARCHAR(60) NOT NULL,
    apellido VARCHAR(60) NOT NULL,
    genero ENUM('M', 'F', 'Otro') NOT NULL,
    telefono VARCHAR(20),
    email VARCHAR(120),
    fecha_nacimiento DATE,
    fecha_registro DATE NOT NULL DEFAULT (CURRENT_DATE),
    referido_por_socio_id INT NULL,
    instructor_id INT NULL,
    activo TINYINT(1) NOT NULL DEFAULT 1,
    CONSTRAINT fk_socios_referido
        FOREIGN KEY (referido_por_socio_id) REFERENCES socios(id) ON DELETE SET NULL,
    CONSTRAINT fk_socios_instructor
        FOREIGN KEY (instructor_id) REFERENCES instructores(id) ON DELETE SET NULL,
    CONSTRAINT chk_socios_activo CHECK (activo IN (0, 1)),
    INDEX idx_socios_instructor (instructor_id),
    INDEX idx_socios_referido (referido_por_socio_id),
    INDEX idx_socios_genero (genero)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE planes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE,
    categoria ENUM('Basico', 'Pro', 'Premium', 'Platinum') NOT NULL,
    es_plan_referido TINYINT(1) NOT NULL DEFAULT 0,
    precio DECIMAL(8,2) NOT NULL,
    duracion_dias INT NOT NULL,
    activo TINYINT(1) NOT NULL DEFAULT 1,
    CONSTRAINT chk_planes_referido CHECK (es_plan_referido IN (0, 1)),
    CONSTRAINT chk_planes_precio CHECK (precio >= 0),
    CONSTRAINT chk_planes_duracion CHECK (duracion_dias > 0),
    CONSTRAINT chk_planes_activo CHECK (activo IN (0, 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE membresias (
    id INT AUTO_INCREMENT PRIMARY KEY,
    socio_id INT NOT NULL,
    plan_id INT NOT NULL,
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE NOT NULL,
    precio_pagado DECIMAL(8,2) NOT NULL,
    metodo_pago ENUM('Efectivo', 'Transferencia', 'Tarjeta') NOT NULL,
    fecha_pago DATETIME NOT NULL,
    estado ENUM('activa', 'vencida', 'cancelada') NOT NULL,
    CONSTRAINT fk_membresias_socio
        FOREIGN KEY (socio_id) REFERENCES socios(id) ON DELETE CASCADE,
    CONSTRAINT fk_membresias_plan
        FOREIGN KEY (plan_id) REFERENCES planes(id),
    CONSTRAINT chk_membresias_fechas CHECK (fecha_fin >= fecha_inicio),
    CONSTRAINT chk_membresias_precio CHECK (precio_pagado >= 0),
    INDEX idx_membresias_fechas (fecha_inicio, fecha_fin),
    INDEX idx_membresias_estado (estado),
    INDEX idx_membresias_plan (plan_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE asistencias (
    id INT AUTO_INCREMENT PRIMARY KEY,
    socio_id INT NOT NULL,
    fecha_entrada DATETIME NOT NULL,
    fecha_salida DATETIME NULL,
    registrado_por INT NULL,
    CONSTRAINT fk_asistencias_socio
        FOREIGN KEY (socio_id) REFERENCES socios(id) ON DELETE CASCADE,
    CONSTRAINT fk_asistencias_usuario
        FOREIGN KEY (registrado_por) REFERENCES usuarios(id) ON DELETE SET NULL,
    CONSTRAINT chk_asistencias_horas
        CHECK (fecha_salida IS NULL OR fecha_salida >= fecha_entrada),
    INDEX idx_asistencias_entrada (fecha_entrada),
    INDEX idx_asistencias_socio_fecha (socio_id, fecha_entrada)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE valoraciones_fisicas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    socio_id INT NOT NULL,
    instructor_id INT NOT NULL,
    fecha DATE NOT NULL,
    peso_kg DECIMAL(5,2) NOT NULL,
    estatura_cm DECIMAL(5,2) NOT NULL,
    imc DECIMAL(5,2) NOT NULL,
    porcentaje_grasa DECIMAL(5,2),
    observaciones TEXT,
    CONSTRAINT fk_valoraciones_socio
        FOREIGN KEY (socio_id) REFERENCES socios(id) ON DELETE CASCADE,
    CONSTRAINT fk_valoraciones_instructor
        FOREIGN KEY (instructor_id) REFERENCES instructores(id),
    CONSTRAINT chk_valoraciones_peso CHECK (peso_kg > 0),
    CONSTRAINT chk_valoraciones_estatura CHECK (estatura_cm > 0),
    CONSTRAINT chk_valoraciones_imc CHECK (imc > 0),
    CONSTRAINT chk_valoraciones_grasa
        CHECK (porcentaje_grasa IS NULL OR porcentaje_grasa BETWEEN 0 AND 100),
    INDEX idx_valoraciones_socio_fecha (socio_id, fecha)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE rutinas_ejercicios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    socio_id INT NOT NULL,
    instructor_id INT NOT NULL,
    dia_semana ENUM(
        'Lunes', 'Martes', 'Miercoles', 'Jueves', 'Viernes', 'Sabado'
    ) NOT NULL,
    grupo_muscular VARCHAR(60) NOT NULL,
    ejercicios_detalle TEXT NOT NULL,
    activa TINYINT(1) NOT NULL DEFAULT 1,
    CONSTRAINT fk_rutinas_socio
        FOREIGN KEY (socio_id) REFERENCES socios(id) ON DELETE CASCADE,
    CONSTRAINT fk_rutinas_instructor
        FOREIGN KEY (instructor_id) REFERENCES instructores(id),
    CONSTRAINT chk_rutinas_activa CHECK (activa IN (0, 1)),
    INDEX idx_rutinas_socio_activa (socio_id, activa),
    INDEX idx_rutinas_instructor (instructor_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- 2. DML: DATOS INICIALES
-- =====================================================

-- =====================================================
-- 2A. SEGURIDAD DEL NIVEL APLICACIÓN (RBAC)
-- =====================================================

INSERT INTO roles (nombre) VALUES
    ('Admin'),
    ('Recepcionista'),
    ('Entrenador'),
    ('Supervisor'),
    ('Nutricionista'),
    ('Fisioterapeuta'),
    ('Coordinador'),
    ('Auditor'),
    ('Soporte'),
    ('Gerente');

INSERT INTO permisos (clave) VALUES
    ('usuarios.gestionar'),
    ('planes.ver'),
    ('planes.gestionar'),
    ('socios.ver'),
    ('socios.gestionar'),
    ('instructores.gestionar'),
    ('membresias.ver'),
    ('membresias.gestionar'),
    ('asistencias.registrar'),
    ('asistencias.ver'),
    ('rutinas.gestionar'),
    ('valoraciones.gestionar'),
    ('reportes.ver'),
    ('reportes.exportar');

-- Admin recibe todos los permisos existentes.
INSERT INTO rol_permisos (rol_id, permiso_id)
SELECT r.id, p.id
FROM roles r
CROSS JOIN permisos p
WHERE r.nombre = 'Admin';

-- Recepcionista: socios, planes, membresías y asistencias operativas.
INSERT INTO rol_permisos (rol_id, permiso_id)
SELECT r.id, p.id
FROM roles r
JOIN permisos p
    ON p.clave IN (
        'planes.ver',
        'socios.ver',
        'socios.gestionar',
        'membresias.ver',
        'membresias.gestionar',
        'asistencias.registrar',
        'asistencias.ver'
    )
WHERE r.nombre = 'Recepcionista';

-- Entrenador: consulta de socios y asistencias, y gestión de sus áreas.
INSERT INTO rol_permisos (rol_id, permiso_id)
SELECT r.id, p.id
FROM roles r
JOIN permisos p
    ON p.clave IN (
        'socios.ver',
        'asistencias.ver',
        'asistencias.registrar',
        'rutinas.gestionar',
        'valoraciones.gestionar'
    )
WHERE r.nombre = 'Entrenador';

-- Supervisor, coordinador y gerente: permisos de consulta y reportes.
INSERT INTO rol_permisos (rol_id, permiso_id)
SELECT r.id, p.id
FROM roles r
JOIN permisos p
    ON p.clave IN (
        'planes.ver',
        'socios.ver',
        'membresias.ver',
        'asistencias.ver',
        'reportes.ver',
        'reportes.exportar'
    )
WHERE r.nombre IN ('Supervisor', 'Coordinador', 'Gerente');

-- Nutricionista y fisioterapeuta: consulta de socios y gestión de valoraciones.
INSERT INTO rol_permisos (rol_id, permiso_id)
SELECT r.id, p.id
FROM roles r
JOIN permisos p
    ON p.clave IN ('socios.ver', 'valoraciones.gestionar')
WHERE r.nombre IN ('Nutricionista', 'Fisioterapeuta');

-- Auditor: consulta de datos y exportación de reportes.
INSERT INTO rol_permisos (rol_id, permiso_id)
SELECT r.id, p.id
FROM roles r
JOIN permisos p
    ON p.clave IN (
        'planes.ver',
        'socios.ver',
        'membresias.ver',
        'asistencias.ver',
        'reportes.ver',
        'reportes.exportar'
    )
WHERE r.nombre = 'Auditor';

-- Soporte: consulta básica de socios y planes.
INSERT INTO rol_permisos (rol_id, permiso_id)
SELECT r.id, p.id
FROM roles r
JOIN permisos p
    ON p.clave IN ('planes.ver', 'socios.ver')
WHERE r.nombre = 'Soporte';

-- Hash de prueba solicitado para Admin123!.
-- En producción, almacenar hashes generados con el algoritmo
-- y los parámetros gestionados por la aplicación.
SET @hash_demo =
'scrypt:32768:8:1$ldXdYArQPlEDxMCv$f7a24ce7f6f19d266e44216d9d23ff10d8539649ee84b4dbe4bc3d1d9d37007eb24c01277a8840d15f0dcea515b9d9b142a8ab0dc5b7f9f3ad82dae53cacb633';

INSERT INTO usuarios (nombre, email, clave_hash, rol_id, activo) VALUES
    ('Administrador', 'admin@gym.com', @hash_demo,
        (SELECT id FROM roles WHERE nombre = 'Admin'), 1),
    ('Rosa Recepción', 'recep@gym.com', @hash_demo,
        (SELECT id FROM roles WHERE nombre = 'Recepcionista'), 1),
    ('Carlos Entrenador', 'entre@gym.com', @hash_demo,
        (SELECT id FROM roles WHERE nombre = 'Entrenador'), 1),
    ('Elena Supervisora', 'elena.super@gym.com', @hash_demo,
        (SELECT id FROM roles WHERE nombre = 'Supervisor'), 1),
    ('Marco Nutricionista', 'marco.nutri@gym.com', @hash_demo,
        (SELECT id FROM roles WHERE nombre = 'Nutricionista'), 1),
    ('Paola Fisioterapeuta', 'paola.fisio@gym.com', @hash_demo,
        (SELECT id FROM roles WHERE nombre = 'Fisioterapeuta'), 1),
    ('Jorge Coordinador', 'jorge.coord@gym.com', @hash_demo,
        (SELECT id FROM roles WHERE nombre = 'Coordinador'), 1),
    ('Lucía Auditora', 'lucia.audit@gym.com', @hash_demo,
        (SELECT id FROM roles WHERE nombre = 'Auditor'), 1),
    ('Andrés Soporte', 'andres.soporte@gym.com', @hash_demo,
        (SELECT id FROM roles WHERE nombre = 'Soporte'), 1),
    ('Marta Gerente', 'marta.gerente@gym.com', @hash_demo,
        (SELECT id FROM roles WHERE nombre = 'Gerente'), 1);

-- =====================================================
-- 2B. INSTRUCTORES
-- usuarios ya está cargada para resolver usuario_id.
-- =====================================================

INSERT INTO instructores
    (usuario_id, cedula, nombre, apellido, telefono, especialidad,
     fecha_contratacion, activo)
VALUES
    (3, '0901000001', 'Carlos', 'Entrenador', '0993000001', 'Fuerza',
        DATE_SUB(CURDATE(), INTERVAL 900 DAY), 1),
    (NULL, '0901000002', 'Daniela', 'Mera', '0993000002', 'Entrenamiento funcional',
        DATE_SUB(CURDATE(), INTERVAL 800 DAY), 1),
    (NULL, '0901000003', 'Esteban', 'Lara', '0993000003', 'Cardio',
        DATE_SUB(CURDATE(), INTERVAL 700 DAY), 1),
    (NULL, '0901000004', 'Gabriela', 'Solís', '0993000004', 'Yoga',
        DATE_SUB(CURDATE(), INTERVAL 600 DAY), 1),
    (NULL, '0901000005', 'Héctor', 'Paz', '0993000005', 'Rehabilitación',
        DATE_SUB(CURDATE(), INTERVAL 500 DAY), 1),
    (NULL, '0901000006', 'Inés', 'Cárdenas', '0993000006', 'Nutrición deportiva',
        DATE_SUB(CURDATE(), INTERVAL 400 DAY), 1),
    (NULL, '0901000007', 'Javier', 'Cruz', '0993000007', 'Culturismo',
        DATE_SUB(CURDATE(), INTERVAL 300 DAY), 1),
    (NULL, '0901000008', 'Karina', 'Vélez', '0993000008', 'Pilates',
        DATE_SUB(CURDATE(), INTERVAL 200 DAY), 1),
    (NULL, '0901000009', 'Leonardo', 'Ríos', '0993000009', 'Boxeo',
        DATE_SUB(CURDATE(), INTERVAL 100 DAY), 1),
    (NULL, '0901000010', 'Mónica', 'Vera', '0993000010', 'Movilidad',
        DATE_SUB(CURDATE(), INTERVAL 50 DAY), 1);

-- =====================================================
-- 2C. SOCIOS
-- Los primeros socios no tienen referido; los restantes
-- apuntan a socios insertados previamente.
-- =====================================================

INSERT INTO socios
    (cedula, nombre, apellido, genero, telefono, email, fecha_nacimiento,
     fecha_registro, referido_por_socio_id, instructor_id, activo)
VALUES
    ('0102030401', 'Ana', 'Torres', 'F', '0991111111', 'ana@mail.com',
        '1995-03-12', DATE_SUB(CURDATE(), INTERVAL 200 DAY), NULL, 1, 1),
    ('0102030402', 'Luis', 'Pérez', 'M', '0992222222', 'luis@mail.com',
        '1988-07-25', DATE_SUB(CURDATE(), INTERVAL 120 DAY), NULL, 2, 1),
    ('0102030403', 'María', 'Cevallos', 'F', '0993333333', 'maria@mail.com',
        '2000-11-02', DATE_SUB(CURDATE(), INTERVAL 60 DAY), NULL, 3, 1),
    ('0102030404', 'Pedro', 'Salinas', 'M', '0994444444', 'pedro@mail.com',
        '1992-01-30', DATE_SUB(CURDATE(), INTERVAL 45 DAY), NULL, 4, 1),
    ('0102030405', 'Sofía', 'Mora', 'F', '0995555555', 'sofia@mail.com',
        '1998-09-14', DATE_SUB(CURDATE(), INTERVAL 10 DAY), NULL, 5, 1),
    ('0102030406', 'Diego', 'Vera', 'M', '0996666666', 'diego@mail.com',
        '1985-05-20', DATE_SUB(CURDATE(), INTERVAL 5 DAY), NULL, 6, 1),
    ('0102030407', 'Valeria', 'León', 'F', '0997777771', 'valeria.leon@mail.com',
        '1997-04-18', DATE_SUB(CURDATE(), INTERVAL 30 DAY), 1, 7, 1),
    ('0102030408', 'Andrés', 'Vega', 'M', '0997777772', 'andres.vega@mail.com',
        '1990-08-09', DATE_SUB(CURDATE(), INTERVAL 25 DAY), 2, 8, 1),
    ('0102030409', 'Camila', 'Ríos', 'F', '0997777773', 'camila.rios@mail.com',
        '2001-02-21', DATE_SUB(CURDATE(), INTERVAL 20 DAY), 3, 9, 1),
    ('0102030410', 'Mateo', 'Paredes', 'Otro', '0997777774', 'mateo.paredes@mail.com',
        '1987-12-05', DATE_SUB(CURDATE(), INTERVAL 15 DAY), 4, 10, 1);

-- =====================================================
-- 2D. PLANES
-- =====================================================

INSERT INTO planes
    (nombre, categoria, es_plan_referido, precio, duracion_dias, activo)
VALUES
    ('Mensual Básico', 'Basico', 0, 30.00, 30, 1),
    ('Trimestral Pro', 'Pro', 0, 80.00, 90, 1),
    ('Anual Premium', 'Premium', 0, 280.00, 365, 1),
    ('Semanal Básico', 'Basico', 0, 12.00, 7, 1),
    ('Quincenal Pro', 'Pro', 0, 18.00, 15, 1),
    ('Semestral Premium', 'Premium', 0, 160.00, 180, 1),
    ('Estudiante Básico', 'Basico', 1, 24.00, 30, 1),
    ('Fin de Semana Pro', 'Pro', 0, 15.00, 30, 1),
    ('Mañanas Premium', 'Premium', 0, 22.00, 30, 1),
    ('VIP Platinum', 'Platinum', 0, 350.00, 365, 1);

-- =====================================================
-- 2E. MEMBRESÍAS
-- Socios y planes ya existen.
-- =====================================================

INSERT INTO membresias
    (socio_id, plan_id, fecha_inicio, fecha_fin, precio_pagado,
     metodo_pago, fecha_pago, estado)
VALUES
    (1, 3, DATE_SUB(CURDATE(), INTERVAL 200 DAY),
        DATE_ADD(DATE_SUB(CURDATE(), INTERVAL 200 DAY), INTERVAL 365 DAY),
        280.00, 'Tarjeta', DATE_SUB(NOW(), INTERVAL 200 DAY), 'activa'),
    (2, 1, DATE_SUB(CURDATE(), INTERVAL 40 DAY),
        DATE_ADD(DATE_SUB(CURDATE(), INTERVAL 40 DAY), INTERVAL 30 DAY),
        30.00, 'Efectivo', DATE_SUB(NOW(), INTERVAL 40 DAY), 'vencida'),
    (2, 1, DATE_SUB(CURDATE(), INTERVAL 5 DAY),
        DATE_ADD(DATE_SUB(CURDATE(), INTERVAL 5 DAY), INTERVAL 30 DAY),
        30.00, 'Transferencia', DATE_SUB(NOW(), INTERVAL 5 DAY), 'activa'),
    (3, 2, DATE_SUB(CURDATE(), INTERVAL 60 DAY),
        DATE_ADD(DATE_SUB(CURDATE(), INTERVAL 60 DAY), INTERVAL 90 DAY),
        80.00, 'Tarjeta', DATE_SUB(NOW(), INTERVAL 60 DAY), 'activa'),
    (4, 1, DATE_SUB(CURDATE(), INTERVAL 28 DAY),
        DATE_ADD(DATE_SUB(CURDATE(), INTERVAL 28 DAY), INTERVAL 30 DAY),
        30.00, 'Efectivo', DATE_SUB(NOW(), INTERVAL 28 DAY), 'activa'),
    (5, 1, DATE_SUB(CURDATE(), INTERVAL 10 DAY),
        DATE_ADD(DATE_SUB(CURDATE(), INTERVAL 10 DAY), INTERVAL 30 DAY),
        30.00, 'Transferencia', DATE_SUB(NOW(), INTERVAL 10 DAY), 'activa'),
    (6, 2, DATE_SUB(CURDATE(), INTERVAL 100 DAY),
        DATE_ADD(DATE_SUB(CURDATE(), INTERVAL 100 DAY), INTERVAL 90 DAY),
        80.00, 'Tarjeta', DATE_SUB(NOW(), INTERVAL 100 DAY), 'vencida'),
    (7, 4, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 7 DAY),
        12.00, 'Efectivo', NOW(), 'activa'),
    (8, 5, DATE_SUB(CURDATE(), INTERVAL 20 DAY),
        DATE_ADD(DATE_SUB(CURDATE(), INTERVAL 20 DAY), INTERVAL 15 DAY),
        18.00, 'Transferencia', DATE_SUB(NOW(), INTERVAL 20 DAY), 'vencida'),
    (9, 6, DATE_SUB(CURDATE(), INTERVAL 2 DAY),
        DATE_ADD(DATE_SUB(CURDATE(), INTERVAL 2 DAY), INTERVAL 180 DAY),
        160.00, 'Tarjeta', DATE_SUB(NOW(), INTERVAL 2 DAY), 'activa');

-- =====================================================
-- 2F. ASISTENCIAS
-- =====================================================

INSERT INTO asistencias
    (socio_id, fecha_entrada, fecha_salida, registrado_por)
VALUES
    (1, DATE_SUB(NOW(), INTERVAL 1 DAY), DATE_SUB(NOW(), INTERVAL 1 DAY) + INTERVAL 70 MINUTE, 2),
    (1, DATE_SUB(NOW(), INTERVAL 3 DAY), DATE_SUB(NOW(), INTERVAL 3 DAY) + INTERVAL 65 MINUTE, 3),
    (1, DATE_SUB(NOW(), INTERVAL 5 DAY), DATE_SUB(NOW(), INTERVAL 5 DAY) + INTERVAL 80 MINUTE, 2),
    (2, DATE_SUB(NOW(), INTERVAL 2 DAY), DATE_SUB(NOW(), INTERVAL 2 DAY) + INTERVAL 55 MINUTE, 2),
    (2, DATE_SUB(NOW(), INTERVAL 4 DAY), DATE_SUB(NOW(), INTERVAL 4 DAY) + INTERVAL 60 MINUTE, 3),
    (3, DATE_SUB(NOW(), INTERVAL 1 DAY), DATE_SUB(NOW(), INTERVAL 1 DAY) + INTERVAL 75 MINUTE, 2),
    (3, DATE_SUB(NOW(), INTERVAL 6 DAY), DATE_SUB(NOW(), INTERVAL 6 DAY) + INTERVAL 90 MINUTE, 3),
    (4, DATE_SUB(NOW(), INTERVAL 2 DAY), DATE_SUB(NOW(), INTERVAL 2 DAY) + INTERVAL 50 MINUTE, 2),
    (5, DATE_SUB(NOW(), INTERVAL 1 DAY), DATE_SUB(NOW(), INTERVAL 1 DAY) + INTERVAL 85 MINUTE, 2),
    (6, DATE_SUB(NOW(), INTERVAL 3 DAY), DATE_SUB(NOW(), INTERVAL 3 DAY) + INTERVAL 60 MINUTE, 3),
    (7, DATE_SUB(NOW(), INTERVAL 1 DAY), DATE_SUB(NOW(), INTERVAL 1 DAY) + INTERVAL 45 MINUTE, 2),
    (8, DATE_SUB(NOW(), INTERVAL 2 DAY), DATE_SUB(NOW(), INTERVAL 2 DAY) + INTERVAL 70 MINUTE, 3),
    (9, DATE_SUB(NOW(), INTERVAL 3 DAY), DATE_SUB(NOW(), INTERVAL 3 DAY) + INTERVAL 95 MINUTE, 2),
    (10, DATE_SUB(NOW(), INTERVAL 4 DAY), DATE_SUB(NOW(), INTERVAL 4 DAY) + INTERVAL 55 MINUTE, 2);

-- =====================================================
-- 2G. VALORACIONES FÍSICAS
-- =====================================================

INSERT INTO valoraciones_fisicas
    (socio_id, instructor_id, fecha, peso_kg, estatura_cm, imc,
     porcentaje_grasa, observaciones)
VALUES
    (1, 1, DATE_SUB(CURDATE(), INTERVAL 30 DAY), 62.50, 165.00, 22.96, 24.50, 'Evaluación inicial; buena movilidad.'),
    (2, 2, DATE_SUB(CURDATE(), INTERVAL 28 DAY), 78.00, 178.00, 24.62, 19.20, 'Objetivo: mejorar resistencia.'),
    (3, 3, DATE_SUB(CURDATE(), INTERVAL 25 DAY), 58.00, 162.00, 22.10, 23.10, 'Plan de fuerza progresiva.'),
    (4, 4, DATE_SUB(CURDATE(), INTERVAL 22 DAY), 82.00, 180.00, 25.31, 21.00, 'Seguimiento de composición corporal.'),
    (5, 5, DATE_SUB(CURDATE(), INTERVAL 20 DAY), 55.00, 160.00, 21.48, 22.00, 'Sin restricciones reportadas.'),
    (6, 6, DATE_SUB(CURDATE(), INTERVAL 18 DAY), 88.00, 182.00, 26.57, 24.80, 'Enfoque en acondicionamiento general.'),
    (7, 7, DATE_SUB(CURDATE(), INTERVAL 15 DAY), 64.00, 168.00, 22.68, 25.10, 'Evaluación de fuerza y movilidad.'),
    (8, 8, DATE_SUB(CURDATE(), INTERVAL 12 DAY), 74.00, 175.00, 24.16, 20.50, 'Progresión adecuada.'),
    (9, 9, DATE_SUB(CURDATE(), INTERVAL 10 DAY), 60.00, 164.00, 22.31, 23.70, 'Objetivo: mejorar resistencia cardiovascular.'),
    (10, 10, DATE_SUB(CURDATE(), INTERVAL 7 DAY), 70.00, 172.00, 23.66, 20.00, 'Evaluación inicial satisfactoria.');

-- =====================================================
-- 2H. RUTINAS DE EJERCICIOS
-- =====================================================

INSERT INTO rutinas_ejercicios
    (socio_id, instructor_id, dia_semana, grupo_muscular,
     ejercicios_detalle, activa)
VALUES
    (1, 1, 'Lunes', 'Piernas', 'Sentadilla 3x10; prensa 3x12; extensión 3x12.', 1),
    (2, 2, 'Martes', 'Pecho', 'Press banca 4x8; press inclinado 3x10; aperturas 3x12.', 1),
    (3, 3, 'Miercoles', 'Espalda', 'Jalón al pecho 3x10; remo 3x10; face pull 3x12.', 1),
    (4, 4, 'Jueves', 'Hombros', 'Press militar 3x8; elevación lateral 3x12.', 1),
    (5, 5, 'Viernes', 'Cuerpo completo', 'Peso muerto ligero; sentadilla goblet; plancha.', 1),
    (6, 6, 'Sabado', 'Cardio', 'Bicicleta 20 min; caminata inclinada 20 min.', 1),
    (7, 7, 'Lunes', 'Brazos', 'Curl bíceps 3x12; extensión tríceps 3x12.', 1),
    (8, 8, 'Martes', 'Core', 'Plancha 3x45 s; dead bug 3x10; pallof press 3x12.', 1),
    (9, 9, 'Jueves', 'Piernas', 'Peso muerto rumano 3x10; zancadas 3x10 por lado.', 1),
    (10, 10, 'Viernes', 'Movilidad', 'Movilidad de cadera, hombro y columna; 30 min.', 1);

-- =====================================================
-- 3. SEGURIDAD DEL NIVEL MOTOR MYSQL (DCL)
-- Estas cuentas y roles controlan conexiones y operaciones
-- directas en MySQL. Complementan, pero no sustituyen, los
-- roles de aplicación almacenados en roles/permisos.
--
-- Cambiar las contraseñas antes de usar en un servidor
-- compartido. Se asume que las conexiones usan localhost.
-- =====================================================

CREATE ROLE IF NOT EXISTS 'gim_admin_role';
CREATE ROLE IF NOT EXISTS 'gim_recepcionista_role';
CREATE ROLE IF NOT EXISTS 'gim_entrenador_role';

GRANT ALL PRIVILEGES ON GIM.* TO 'gim_admin_role';

GRANT SELECT, INSERT, UPDATE, DELETE ON GIM.socios
    TO 'gim_recepcionista_role';
GRANT SELECT, INSERT, UPDATE, DELETE ON GIM.membresias
    TO 'gim_recepcionista_role';
GRANT SELECT, INSERT ON GIM.asistencias
    TO 'gim_recepcionista_role';
GRANT SELECT ON GIM.planes
    TO 'gim_recepcionista_role';

GRANT SELECT ON GIM.socios
    TO 'gim_entrenador_role';
GRANT SELECT, INSERT ON GIM.asistencias
    TO 'gim_entrenador_role';
GRANT SELECT, INSERT, UPDATE ON GIM.rutinas_ejercicios
    TO 'gim_entrenador_role';
GRANT SELECT, INSERT, UPDATE ON GIM.valoraciones_fisicas
    TO 'gim_entrenador_role';

CREATE USER IF NOT EXISTS 'Admin'@'localhost'
    IDENTIFIED BY 'Cambiar_Admin_2026!';
CREATE USER IF NOT EXISTS 'Recepcionista'@'localhost'
    IDENTIFIED BY 'Cambiar_Recepcion_2026!';
CREATE USER IF NOT EXISTS 'Entrenador'@'localhost'
    IDENTIFIED BY 'Cambiar_Entrenador_2026!';

GRANT 'gim_admin_role' TO 'Admin'@'localhost';
GRANT 'gim_recepcionista_role' TO 'Recepcionista'@'localhost';
GRANT 'gim_entrenador_role' TO 'Entrenador'@'localhost';

SET DEFAULT ROLE 'gim_admin_role' TO 'Admin'@'localhost';
SET DEFAULT ROLE 'gim_recepcionista_role' TO 'Recepcionista'@'localhost';
SET DEFAULT ROLE 'gim_entrenador_role' TO 'Entrenador'@'localhost';

-- MySQL aplica CREATE USER y GRANT inmediatamente.
-- FLUSH PRIVILEGES se incluye como paso explícito solicitado.
FLUSH PRIVILEGES;

-- =====================================================
-- 4. CONSULTAS AVANZADAS
-- Ejecutar cada consulta por separado según la necesidad.
-- =====================================================

-- C1. Horas pico de visita según la hora de entrada.
SELECT
    HOUR(fecha_entrada) AS hora_del_dia,
    COUNT(*) AS total_visitas,
    COUNT(DISTINCT socio_id) AS socios_atendidos
FROM asistencias
GROUP BY HOUR(fecha_entrada)
HAVING COUNT(*) >= 1
ORDER BY total_visitas DESC, hora_del_dia;

-- C2. Asistencias por género y día de la semana.
SELECT
    s.genero,
    DAYNAME(a.fecha_entrada) AS dia_semana,
    COUNT(a.id) AS total_asistencias,
    COUNT(DISTINCT s.id) AS socios_distintos
FROM asistencias a
JOIN socios s ON s.id = a.socio_id
GROUP BY s.genero, DAYOFWEEK(a.fecha_entrada), DAYNAME(a.fecha_entrada)
ORDER BY total_asistencias DESC, s.genero;

-- C3. Tiempo promedio de estancia por socio e instructor.
SELECT
    s.id AS socio_id,
    CONCAT(s.nombre, ' ', s.apellido) AS socio,
    CONCAT(i.nombre, ' ', i.apellido) AS instructor,
    COUNT(a.id) AS visitas_con_salida,
    ROUND(AVG(TIMESTAMPDIFF(MINUTE, a.fecha_entrada, a.fecha_salida)), 1)
        AS minutos_promedio_estancia
FROM socios s
JOIN instructores i ON i.id = s.instructor_id
JOIN asistencias a ON a.socio_id = s.id
WHERE a.fecha_salida IS NOT NULL
GROUP BY s.id, s.nombre, s.apellido, i.nombre, i.apellido
HAVING COUNT(a.id) > 0
ORDER BY minutos_promedio_estancia DESC;

-- C4. Ventas e ingresos por plan, con clasificación por ingreso.
SELECT
    p.id AS plan_id,
    p.nombre AS plan,
    p.categoria,
    COUNT(m.id) AS membresias_vendidas,
    SUM(m.precio_pagado) AS ingresos_totales,
    ROUND(AVG(m.precio_pagado), 2) AS pago_promedio,
    CASE
        WHEN SUM(m.precio_pagado) >= 300 THEN 'Ingreso alto'
        WHEN SUM(m.precio_pagado) >= 100 THEN 'Ingreso medio'
        ELSE 'Ingreso inicial'
    END AS categoria_ingresos
FROM planes p
LEFT JOIN membresias m ON m.plan_id = p.id
GROUP BY p.id, p.nombre, p.categoria
ORDER BY ingresos_totales DESC;

-- C5. Cantidad de socios activos por instructor y especialidad.
SELECT
    i.id AS instructor_id,
    CONCAT(i.nombre, ' ', i.apellido) AS instructor,
    i.especialidad,
    COUNT(s.id) AS socios_asignados,
    SUM(CASE WHEN s.activo = 1 THEN 1 ELSE 0 END) AS socios_activos
FROM instructores i
LEFT JOIN socios s ON s.instructor_id = i.id
GROUP BY i.id, i.nombre, i.apellido, i.especialidad
HAVING COUNT(s.id) >= 1
ORDER BY socios_activos DESC, instructor;

-- C6. Nuevas membresías y membresías vencidas por mes.
WITH meses AS (
    SELECT DATE_FORMAT(fecha_inicio, '%Y-%m') AS mes
    FROM membresias
    UNION
    SELECT DATE_FORMAT(fecha_fin, '%Y-%m') AS mes
    FROM membresias
),
nuevas AS (
    SELECT
        DATE_FORMAT(fecha_inicio, '%Y-%m') AS mes,
        COUNT(*) AS cantidad_nuevas
    FROM membresias
    GROUP BY DATE_FORMAT(fecha_inicio, '%Y-%m')
),
vencidas AS (
    SELECT
        DATE_FORMAT(fecha_fin, '%Y-%m') AS mes,
        COUNT(*) AS cantidad_vencidas
    FROM membresias
    WHERE estado = 'vencida'
    GROUP BY DATE_FORMAT(fecha_fin, '%Y-%m')
)
SELECT
    m.mes,
    COALESCE(n.cantidad_nuevas, 0) AS membresias_nuevas,
    COALESCE(v.cantidad_vencidas, 0) AS membresias_vencidas
FROM meses m
LEFT JOIN nuevas n ON n.mes = m.mes
LEFT JOIN vencidas v ON v.mes = m.mes
ORDER BY m.mes;

-- C7. Socios referidos y conversión a membresía de referido.
SELECT
    referente.id AS referente_id,
    CONCAT(referente.nombre, ' ', referente.apellido) AS referente,
    COUNT(referido.id) AS personas_referidas,
    SUM(CASE WHEN p.es_plan_referido = 1 THEN 1 ELSE 0 END)
        AS membresias_con_plan_referido
FROM socios referente
LEFT JOIN socios referido
    ON referido.referido_por_socio_id = referente.id
LEFT JOIN membresias m
    ON m.socio_id = referido.id
LEFT JOIN planes p
    ON p.id = m.plan_id
GROUP BY referente.id, referente.nombre, referente.apellido
HAVING COUNT(referido.id) > 0
ORDER BY personas_referidas DESC, referente;

-- C8. Evolución del IMC por socio comparando cada valoración
-- con la valoración inmediatamente anterior.
WITH historial AS (
    SELECT
        s.id AS socio_id,
        CONCAT(s.nombre, ' ', s.apellido) AS socio,
        v.fecha,
        v.imc,
        LAG(v.imc) OVER (PARTITION BY s.id ORDER BY v.fecha, v.id) AS imc_anterior
    FROM valoraciones_fisicas v
    JOIN socios s ON s.id = v.socio_id
)
SELECT
    socio_id,
    socio,
    fecha,
    imc,
    imc_anterior,
    CASE
        WHEN imc_anterior IS NULL THEN 'Primera valoración'
        WHEN imc < imc_anterior THEN 'IMC disminuyó'
        WHEN imc > imc_anterior THEN 'IMC aumentó'
        ELSE 'IMC sin cambio'
    END AS cambio_imc
FROM historial
ORDER BY socio, fecha;

-- C9. Socios con rutinas activas y cantidad de grupos musculares.
SELECT
    s.id AS socio_id,
    CONCAT(s.nombre, ' ', s.apellido) AS socio,
    CONCAT(i.nombre, ' ', i.apellido) AS instructor,
    COUNT(r.id) AS rutinas_activas,
    COUNT(DISTINCT r.grupo_muscular) AS grupos_musculares,
    GROUP_CONCAT(
        DISTINCT r.dia_semana
        ORDER BY r.dia_semana
        SEPARATOR ', '
    ) AS dias_programados
FROM socios s
JOIN instructores i ON i.id = s.instructor_id
LEFT JOIN rutinas_ejercicios r
    ON r.socio_id = s.id
   AND r.activa = 1
GROUP BY s.id, s.nombre, s.apellido, i.nombre, i.apellido
HAVING COUNT(r.id) > 0
ORDER BY rutinas_activas DESC, socio;

-- C10. Resumen de actividad, membresía vigente y gasto acumulado
-- por socio usando agregación, JOIN y subconsulta.
SELECT
    s.id AS socio_id,
    CONCAT(s.nombre, ' ', s.apellido) AS socio,
    s.genero,
    COUNT(DISTINCT a.id) AS asistencias_totales,
    COUNT(DISTINCT CASE WHEN m.estado = 'activa'
        AND CURDATE() BETWEEN m.fecha_inicio AND m.fecha_fin
        THEN m.id END) AS membresias_vigentes,
    COALESCE(SUM(DISTINCT m.precio_pagado), 0) AS gasto_membresias,
    CASE
        WHEN EXISTS (
            SELECT 1
            FROM membresias mx
            WHERE mx.socio_id = s.id
              AND mx.estado = 'activa'
              AND CURDATE() BETWEEN mx.fecha_inicio AND mx.fecha_fin
        ) THEN 'Membresía vigente'
        ELSE 'Revisar renovación'
    END AS estado_comercial
FROM socios s
LEFT JOIN asistencias a ON a.socio_id = s.id
LEFT JOIN membresias m ON m.socio_id = s.id
GROUP BY s.id, s.nombre, s.apellido, s.genero
ORDER BY asistencias_totales DESC, socio;