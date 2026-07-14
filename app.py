from flask import Flask, render_template, request, jsonify, redirect, url_for
import mysql.connector
from mysql.connector import Error
from datetime import datetime
import os
import base64
import hashlib

try:
    from cryptography.fernet import Fernet, InvalidToken
except ImportError:
    Fernet = None
    InvalidToken = Exception

# Intentar cargar variables desde .env si python-dotenv está disponible
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print('Aviso: python-dotenv no está instalado. Se usarán variables de entorno del sistema o valores por defecto.')

app = Flask(__name__)

# Configuración de la base de datos usando variables de entorno si existen
db_config = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'gestion_mantenimiento')
}


def get_encryption_key():
    """Obtiene una clave de cifrado segura a partir de variables de entorno."""
    raw_key = os.getenv('ENCRYPTION_KEY')
    if raw_key:
        try:
            key = raw_key.encode() if isinstance(raw_key, str) else raw_key
            base64.urlsafe_b64decode(key)
            return key
        except Exception:
            pass

    secret = os.getenv('SECRET_KEY', 'clave_segura_por_defecto_2026')
    return base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())


def get_cipher():
    if Fernet is None:
        raise RuntimeError('La librería cryptography no está instalada.')
    return Fernet(get_encryption_key())


def encrypt_text(value):
    if value is None:
        return None
    try:
        cipher = get_cipher()
        return cipher.encrypt(value.encode()).decode()
    except Exception as e:
        print(f"Error al encriptar: {e}")
        return value


def decrypt_text(value):
    if value is None:
        return None
    try:
        cipher = get_cipher()
        return cipher.decrypt(value.encode()).decode()
    except InvalidToken:
        return value
    except Exception as e:
        print(f"Error al desencriptar: {e}")
        return value


def get_db_connection():
    """Obtiene una conexión a la base de datos"""
    try:
        connection = mysql.connector.connect(**db_config)
        if connection.is_connected():
            return connection
    except Exception as e:
        print(f"Error al conectar a MySQL: {e}")
        return None

# ======================== RUTAS PRINCIPALES ========================

@app.route('/')
def index():
    """Página principal con estadísticas"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Obtener estadísticas
        cursor.execute("""
            SELECT 
                COUNT(*) as total_reportes,
                SUM(CASE WHEN estado_id = 1 THEN 1 ELSE 0 END) as pendientes,
                SUM(CASE WHEN estado_id = 2 THEN 1 ELSE 0 END) as en_progreso,
                SUM(CASE WHEN estado_id = 3 THEN 1 ELSE 0 END) as resueltos
            FROM reportes_danos
        """)
        estadisticas = cursor.fetchone()
        
        # Obtener reportes recientes
        cursor.execute("""
            SELECT r.*, d.nombre as aula, c.nombre as categoria, e.nombre as estado
            FROM reportes_danos r
            JOIN aulas d ON r.aula_id = d.id
            JOIN categorias_danos c ON r.categoria_id = c.id
            JOIN estados_reporte e ON r.estado_id = e.id
            ORDER BY r.fecha_reporte DESC
            LIMIT 10
        """)
        reportes_recientes = cursor.fetchall()
        for reporte in reportes_recientes:
            if 'descripcion' in reporte:
                reporte['descripcion'] = decrypt_text(reporte['descripcion'])
            if 'observaciones' in reporte:
                reporte['observaciones'] = decrypt_text(reporte['observaciones'])
        
        cursor.close()
        connection.close()
        
        return render_template('index.html', 
                             estadisticas=estadisticas,
                             reportes_recientes=reportes_recientes)
    except Exception as e:
        print(f"Error: {e}")
        return render_template('index.html', 
                             estadisticas={'total_reportes': 0, 'pendientes': 0, 'en_progreso': 0, 'resueltos': 0},
                             reportes_recientes=[])

@app.route('/reportes')
def listar_reportes():
    """Lista todos los reportes con filtros"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Filtros
        estado_id = request.args.get('estado', None)
        aula_id = request.args.get('aula', None)
        prioridad = request.args.get('prioridad', None)
        
        # Construcción de query
        query = """
            SELECT r.*, d.nombre as aula, c.nombre as categoria, e.nombre as estado
            FROM reportes_danos r
            JOIN aulas d ON r.aula_id = d.id
            JOIN categorias_danos c ON r.categoria_id = c.id
            JOIN estados_reporte e ON r.estado_id = e.id
            WHERE 1=1
        """
        params = []
        
        if estado_id:
            query += " AND r.estado_id = %s"
            params.append(estado_id)
        if aula_id:
            query += " AND r.aula_id = %s"
            params.append(aula_id)
        if prioridad:
            query += " AND r.prioridad = %s"
            params.append(prioridad)
        
        query += " ORDER BY r.fecha_reporte DESC"
        cursor.execute(query, params)
        reportes = cursor.fetchall()
        for reporte in reportes:
            if 'descripcion' in reporte:
                reporte['descripcion'] = decrypt_text(reporte['descripcion'])
            if 'observaciones' in reporte:
                reporte['observaciones'] = decrypt_text(reporte['observaciones'])
        
        # Obtener aulas y estados para filtros
        cursor.execute("SELECT id, nombre FROM aulas")
        aulas = cursor.fetchall()
        
        cursor.execute("SELECT id, nombre FROM estados_reporte")
        estados = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return render_template('reportes.html', 
                             reportes=reportes,
                             aulas=aulas,
                             estados=estados)
    except Exception as e:
        print(f"Error: {e}")
        return render_template('reportes.html', 
                             reportes=[],
                             aulas=[],
                             estados=[])

@app.route('/reportes/crear', methods=['GET', 'POST'])
def crear_reporte():
    """Crear un nuevo reporte"""
    if request.method == 'GET':
        try:
            connection = get_db_connection()
            if connection is None:
                raise ConnectionError('No se pudo conectar a la base de datos MySQL. Verifica que MySQL esté ejecutándose.')
            cursor = connection.cursor(dictionary=True)
            
            cursor.execute("SELECT id, nombre FROM aulas")
            aulas = cursor.fetchall()
            
            cursor.execute("SELECT id, nombre FROM categorias_danos")
            categorias = cursor.fetchall()
            
            cursor.close()
            connection.close()
            
            return render_template('crear_reporte.html',
                                 aulas=aulas,
                                 categorias=categorias)
        except Exception as e:
            print(f"Error: {e}")
            return render_template('error.html', mensaje=str(e))
    
    elif request.method == 'POST':
        try:
            connection = get_db_connection()
            if connection is None:
                raise ConnectionError('No se pudo conectar a la base de datos MySQL. Verifica que MySQL esté ejecutándose.')
            cursor = connection.cursor()
            
            titulo = request.form['titulo']
            descripcion = request.form['descripcion']
            aula_id = request.form['aula_id']
            categoria_id = request.form['categoria_id']
            prioridad = request.form['prioridad']
            responsable = request.form['responsable']
            costo_estimado = request.form.get('costo_estimado', None)
            descripcion_enc = encrypt_text(descripcion)
            
            cursor.execute("""
                INSERT INTO reportes_danos 
                (titulo, descripcion, aula_id, categoria_id, prioridad, responsable, costo_estimado)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (titulo, descripcion_enc, aula_id, categoria_id, prioridad, responsable, costo_estimado))
            
            connection.commit()
            reporte_id = cursor.lastrowid
            
            # Registrar en seguimiento
            cursor.execute("""
                INSERT INTO seguimiento_reportes 
                (reporte_id, estado_nuevo_id, descripcion_cambio, responsable_cambio)
                VALUES (%s, 1, 'Reporte creado', %s)
            """, (reporte_id, responsable))
            
            connection.commit()
            cursor.close()
            connection.close()
            
            return redirect(url_for('ver_reporte', id=reporte_id))
        except Exception as e:
            print(f"Error: {e}")
            return redirect(url_for('crear_reporte'))

@app.route('/reportes/<int:id>')
def ver_reporte(id):
    """Ver detalles de un reporte"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Obtener reporte
        cursor.execute("""
            SELECT r.*, d.nombre as aula, c.nombre as categoria, e.nombre as estado
            FROM reportes_danos r
            JOIN aulas d ON r.aula_id = d.id
            JOIN categorias_danos c ON r.categoria_id = c.id
            JOIN estados_reporte e ON r.estado_id = e.id
            WHERE r.id = %s
        """, (id,))
        reporte = cursor.fetchone()
        
        if not reporte:
            return redirect(url_for('listar_reportes'))

        reporte['descripcion'] = decrypt_text(reporte['descripcion'])
        reporte['observaciones'] = decrypt_text(reporte.get('observaciones'))
        
        # Obtener seguimiento
        cursor.execute("""
            SELECT s.*, e1.nombre as estado_anterior, e2.nombre as estado_nuevo
            FROM seguimiento_reportes s
            LEFT JOIN estados_reporte e1 ON s.estado_anterior_id = e1.id
            LEFT JOIN estados_reporte e2 ON s.estado_nuevo_id = e2.id
            WHERE s.reporte_id = %s
            ORDER BY s.fecha_cambio DESC
        """, (id,))
        seguimiento = cursor.fetchall()
        
        # Obtener estados disponibles
        cursor.execute("SELECT id, nombre FROM estados_reporte")
        estados = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return render_template('ver_reporte.html',
                             reporte=reporte,
                             seguimiento=seguimiento,
                             estados=estados)
    except Exception as e:
        print(f"Error: {e}")
        return redirect(url_for('listar_reportes'))

@app.route('/reportes/<int:id>/editar', methods=['GET', 'POST'])
def editar_reporte(id):
    """Editar un reporte"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        if request.method == 'GET':
            cursor.execute("""
                SELECT r.*, d.nombre as aula, c.nombre as categoria
                FROM reportes_danos r
                JOIN aulas d ON r.aula_id = d.id
                JOIN categorias_danos c ON r.categoria_id = c.id
                WHERE r.id = %s
            """, (id,))
            reporte = cursor.fetchone()
            if reporte:
                reporte['descripcion'] = decrypt_text(reporte['descripcion'])
                reporte['observaciones'] = decrypt_text(reporte.get('observaciones'))
            
            cursor.execute("SELECT id, nombre FROM aulas")
            aulas = cursor.fetchall()
            
            cursor.execute("SELECT id, nombre FROM categorias_danos")
            categorias = cursor.fetchall()
            
            cursor.execute("SELECT id, nombre FROM estados_reporte")
            estados = cursor.fetchall()
            
            cursor.close()
            connection.close()
            
            if not reporte:
                return redirect(url_for('listar_reportes'))
            
            return render_template('editar_reporte.html',
                                 reporte=reporte,
                                 aulas=aulas,
                                 categorias=categorias,
                                 estados=estados)
        
        elif request.method == 'POST':
            titulo = request.form['titulo']
            descripcion = request.form['descripcion']
            aula_id = request.form['aula_id']
            categoria_id = request.form['categoria_id']
            estado_id = request.form['estado_id']
            prioridad = request.form['prioridad']
            responsable = request.form['responsable']
            observaciones = request.form.get('observaciones', '')
            costo_estimado = request.form.get('costo_estimado', None)
            descripcion_enc = encrypt_text(descripcion)
            observaciones_enc = encrypt_text(observaciones)
            
            # Obtener estado anterior
            cursor.execute("SELECT estado_id FROM reportes_danos WHERE id = %s", (id,))
            reporte_actual = cursor.fetchone()
            estado_anterior_id = reporte_actual['estado_id']
            
            # Actualizar reporte
            cursor.execute("""
                UPDATE reportes_danos 
                SET titulo = %s, descripcion = %s, aula_id = %s, 
                    categoria_id = %s, estado_id = %s, prioridad = %s, 
                    responsable = %s, observaciones = %s, costo_estimado = %s
                WHERE id = %s
            """, (titulo, descripcion_enc, aula_id, categoria_id, estado_id, 
                  prioridad, responsable, observaciones_enc, costo_estimado, id))
            
            # Registrar cambio si el estado cambió
            if estado_anterior_id != int(estado_id):
                cursor.execute("""
                    INSERT INTO seguimiento_reportes 
                    (reporte_id, estado_anterior_id, estado_nuevo_id, descripcion_cambio, responsable_cambio)
                    VALUES (%s, %s, %s, 'Estado actualizado', %s)
                """, (id, estado_anterior_id, estado_id, responsable))
            
            connection.commit()
            cursor.close()
            connection.close()
            
            return redirect(url_for('ver_reporte', id=id))
    except Exception as e:
        print(f"Error: {e}")
        return redirect(url_for('listar_reportes'))

@app.route('/reportes/<int:id>/eliminar', methods=['POST'])
def eliminar_reporte(id):
    """Eliminar un reporte"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Primero eliminar seguimientos (por la FK)
        cursor.execute("DELETE FROM seguimiento_reportes WHERE reporte_id = %s", (id,))
        
        # Luego eliminar el reporte
        cursor.execute("DELETE FROM reportes_danos WHERE id = %s", (id,))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        return redirect(url_for('listar_reportes'))
    except Exception as e:
        print(f"Error: {e}")
        return redirect(url_for('ver_reporte', id=id))

@app.route('/reportes/<int:id>/cambiar-estado', methods=['POST'])
def cambiar_estado(id):
    """Cambiar estado de un reporte"""
    is_api = False
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        data = request.get_json(silent=True)
        if data:
            estado_id = data.get('estado_id')
            observaciones = data.get('observaciones', '')
            responsable = data.get('responsable', 'Sistema')
            is_api = True
        else:
            estado_id = request.form.get('estado_id')
            observaciones = request.form.get('observaciones', '')
            responsable = request.form.get('responsable', 'Sistema')
            is_api = False
        
        if not estado_id:
            raise ValueError('Debe seleccionar un nuevo estado para el reporte.')
        
        # Obtener estado anterior
        cursor.execute("SELECT estado_id FROM reportes_danos WHERE id = %s", (id,))
        reporte = cursor.fetchone()
        if not reporte:
            raise ValueError('Reporte no encontrado.')
        estado_anterior_id = reporte['estado_id']
        
        # Determinar si el nuevo estado es Resuelto y registrar fecha de resolución
        cursor.execute("SELECT nombre FROM estados_reporte WHERE id = %s", (estado_id,))
        estado_destino = cursor.fetchone()
        if estado_destino and estado_destino['nombre'].strip().lower() == 'resuelto':
            cursor.execute("""
                UPDATE reportes_danos 
                SET estado_id = %s, fecha_resolucion = NOW()
                WHERE id = %s
            """, (estado_id, id))
        else:
            cursor.execute("""
                UPDATE reportes_danos 
                SET estado_id = %s
                WHERE id = %s
            """, (estado_id, id))
        
        # Registrar cambio
        cursor.execute("""
            INSERT INTO seguimiento_reportes 
            (reporte_id, estado_anterior_id, estado_nuevo_id, descripcion_cambio, responsable_cambio)
            VALUES (%s, %s, %s, %s, %s)
        """, (id, estado_anterior_id, estado_id, observaciones, responsable))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        if is_api:
            return jsonify({'success': True, 'message': 'Estado actualizado correctamente'})
        return redirect(url_for('ver_reporte', id=id))
    except Exception as e:
        print(f"Error: {e}")
        if is_api:
            return jsonify({'success': False, 'message': f'Error: {e}'}), 500
        return redirect(url_for('ver_reporte', id=id))

# ======================== RUTAS DE ESTADÍSTICAS Y REPORTES ========================

@app.route('/estadisticas')
def estadisticas():
    """Página de estadísticas y análisis"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Reportes por estado
        cursor.execute("""
            SELECT e.nombre, COUNT(*) as cantidad
            FROM reportes_danos r
            JOIN estados_reporte e ON r.estado_id = e.id
            GROUP BY e.nombre
        """)
        reportes_por_estado = cursor.fetchall()
        
# Reportes por aula
        cursor.execute("""
            SELECT d.nombre, COUNT(*) as cantidad
            FROM reportes_danos r
            JOIN aulas d ON r.aula_id = d.id
            GROUP BY d.nombre
            ORDER BY cantidad DESC
        """)
        reportes_por_aula = cursor.fetchall()
        
        # Reportes por prioridad
        cursor.execute("""
            SELECT prioridad, COUNT(*) as cantidad
            FROM reportes_danos
            GROUP BY prioridad
        """)
        reportes_por_prioridad = cursor.fetchall()
        
        # Reportes por categoría
        cursor.execute("""
            SELECT c.nombre, COUNT(*) as cantidad
            FROM reportes_danos r
            JOIN categorias_danos c ON r.categoria_id = c.id
            GROUP BY c.nombre
            ORDER BY cantidad DESC
        """)
        reportes_por_categoria = cursor.fetchall()
        
        # Costo total estimado
        cursor.execute("""
            SELECT SUM(costo_estimado) as costo_total, 
                   AVG(costo_estimado) as costo_promedio
            FROM reportes_danos
            WHERE costo_estimado IS NOT NULL
        """)
        costos = cursor.fetchone()
        
        cursor.close()
        connection.close()
        
        return render_template('estadisticas.html',
                             reportes_por_estado=reportes_por_estado,
                             reportes_por_departamento=reportes_por_aula,
                             reportes_por_prioridad=reportes_por_prioridad,
                             reportes_por_categoria=reportes_por_categoria,
                             costos=costos)
    except Exception as e:
        print(f"Error: {e}")
        return render_template('estadisticas.html',
                             reportes_por_estado=[],
                             reportes_por_departamento=[],
                             reportes_por_prioridad=[],
                             reportes_por_categoria=[],
                             costos={})

if __name__ == '__main__':
    app.run(debug=True, host='localhost', port=5000)
