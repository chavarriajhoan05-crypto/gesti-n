-- Base de datos para gestión de mantenimiento institucional
CREATE DATABASE IF NOT EXISTS gestion_mantenimiento CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE gestion_mantenimiento;

-- Tabla de aulas
CREATE TABLE IF NOT EXISTS aulas (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(100) NOT NULL UNIQUE,
  descripcion TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de categorías de daños
CREATE TABLE IF NOT EXISTS categorias_danos (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(100) NOT NULL UNIQUE,
  descripcion TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de estados de reportes
CREATE TABLE IF NOT EXISTS estados_reporte (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(50) NOT NULL UNIQUE
);

-- Tabla principal de reportes de daños
CREATE TABLE IF NOT EXISTS reportes_danos (
  id INT AUTO_INCREMENT PRIMARY KEY,
  titulo VARCHAR(200) NOT NULL,
  descripcion TEXT NOT NULL,
  aula_id INT NOT NULL,
  categoria_id INT NOT NULL,
  prioridad VARCHAR(50) NOT NULL,
  responsable VARCHAR(100) DEFAULT NULL,
  costo_estimado DECIMAL(10, 2) DEFAULT NULL,
  estado_id INT NOT NULL DEFAULT 1,
  fecha_reporte TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  fecha_actualizacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  fecha_resolucion DATETIME DEFAULT NULL,
  observaciones TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (aula_id) REFERENCES aulas(id),
  FOREIGN KEY (categoria_id) REFERENCES categorias_danos(id),
  FOREIGN KEY (estado_id) REFERENCES estados_reporte(id),
  INDEX idx_aula (aula_id),
  INDEX idx_categoria (categoria_id),
  INDEX idx_estado (estado_id),
  INDEX idx_prioridad (prioridad)
);

-- Tabla de seguimiento/historial de cambios
CREATE TABLE IF NOT EXISTS seguimiento_reportes (
  id INT AUTO_INCREMENT PRIMARY KEY,
  reporte_id INT NOT NULL,
  estado_anterior_id INT DEFAULT NULL,
  estado_nuevo_id INT NOT NULL,
  descripcion_cambio TEXT,
  responsable_cambio VARCHAR(100),
  fecha_cambio TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (reporte_id) REFERENCES reportes_danos(id) ON DELETE CASCADE,
  FOREIGN KEY (estado_anterior_id) REFERENCES estados_reporte(id),
  FOREIGN KEY (estado_nuevo_id) REFERENCES estados_reporte(id),
  INDEX idx_reporte (reporte_id)
);

-- Insertar datos iniciales
INSERT IGNORE INTO aulas (nombre, descripcion) VALUES 
('Infraestructura', 'Daños en estructura, techos, pisos'),
('Eléctrica', 'Problemas eléctricos e iluminación'),
('Plomería', 'Daños en tuberías y sistemas de agua'),
('Climatización', 'Aire acondicionado y calefacción'),
('Equipamiento', 'Mobiliario y equipos'),
('Seguridad', 'Sistemas de seguridad'),
('Jardines', 'Área externa y paisajismo'),
('Otra', 'Otras aulas y espacios escolares');

INSERT IGNORE INTO categorias_danos (nombre, descripcion) VALUES 
('Electricidad', 'Daños en instalaciones eléctricas'),
('Fontanería', 'Fugas, roturas y problemas hidráulicos'),
('Carpintería', 'Averías en puertas, ventanas y mobiliario de madera'),
('Pintura', 'Pintura descascarada o grafitis'),
('Cristalería', 'Vidrios rotos y ventanas dañadas'),
('Otros', 'Categorías diversas de mantenimiento');

INSERT IGNORE INTO estados_reporte (nombre) VALUES 
('Pendiente'),
('En Progreso'),
('Resuelto'),
('Cancelado');
