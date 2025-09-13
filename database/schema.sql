CREATE DATABASE IF NOT EXISTS soporte_ia CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE soporte_ia;

CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    tipo ENUM('usuario', 'admin') DEFAULT 'usuario',
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tickets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT,
    nombre VARCHAR(100),
    telefono VARCHAR(30),
    domicilio VARCHAR(200),
    titulo VARCHAR(200),
    descripcion TEXT NOT NULL,
    categoria ENUM('hardware', 'software', 'redes', 'otros') NOT NULL,
    tipo ENUM('preventivo', 'correctivo') NOT NULL,
    prioridad ENUM('baja', 'media', 'alta', 'critica') DEFAULT 'media',
    estado ENUM('abierto', 'en_proceso', 'resuelto', 'cerrado') DEFAULT 'abierto',
    asignado_admin BOOLEAN DEFAULT FALSE,
    solucion_ia TEXT,
    notas_admin TEXT,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

INSERT IGNORE INTO usuarios (nombre, email, tipo) VALUES 
('Administrador', 'admin@soporte.com', 'admin');

ALTER TABLE usuarios
ADD COLUMN username VARCHAR(50) UNIQUE AFTER id,
ADD COLUMN password_hash VARCHAR(255) NOT NULL AFTER email,
CHANGE COLUMN tipo role ENUM('usuario', 'admin') DEFAULT 'usuario';