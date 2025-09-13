# backend/app.py
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import mysql.connector
import os

# ---------- Flask básico ----------
app = Flask(
    __name__,
    static_folder=os.path.abspath('../frontend'),
    template_folder=os.path.abspath('../frontend')
)
CORS(app)  # permite llamadas desde el front en el mismo host/puerto u otros

# ---------- Config DB ----------
db_config = {
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', '3307')),
    'database': os.getenv('DB_NAME', 'soporte_ia')
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

def ensure_schema(conn):
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INT AUTO_INCREMENT PRIMARY KEY,
            usuario_id INT DEFAULT 0,
            nombre VARCHAR(100),
            telefono VARCHAR(50),
            domicilio VARCHAR(255),
            titulo VARCHAR(200) NOT NULL,
            descripcion TEXT NOT NULL,
            categoria VARCHAR(50) NOT NULL,
            tipo VARCHAR(50) DEFAULT 'correctivo',
            estado VARCHAR(50) DEFAULT 'abierto',
            prioridad VARCHAR(50) DEFAULT 'media',
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cur.close()

# ---------- Vistas ----------
@app.route('/')
def index():
    return render_template('index.html')     # ../frontend/index.html

@app.route('/admin')
def admin():
    return render_template('admin.html')     # ../frontend/admin.html

# ---------- API: crear ticket (SIN login) ----------
@app.route('/api/crear-ticket', methods=['POST'])
def crear_ticket():
    """
    Acepta JSON o FormData.
    Obligatorios: titulo, descripcion, categoria
    Opcionales: nombre, telefono, domicilio, tipo, estado, prioridad
    """
    try:
        data = request.get_json(silent=True) or request.form.to_dict()
        if not data:
            return jsonify({'success': False, 'error': 'Cuerpo vacío'}), 400

        for f in ['titulo', 'descripcion', 'categoria']:
            if not data.get(f):
                return jsonify({'success': False, 'error': f'Falta el campo {f}'}), 400

        conn = get_db_connection()
        ensure_schema(conn)
        cur = conn.cursor()

        usuario_id = 0  # invitado (sin login)
        nombre     = data.get('nombre')
        telefono   = data.get('telefono')
        domicilio  = data.get('domicilio')
        titulo     = data['titulo']
        descripcion= data['descripcion']
        categoria  = data['categoria']
        tipo       = data.get('tipo', 'correctivo')
        estado     = data.get('estado', 'abierto')
        prioridad  = data.get('prioridad', 'media')

        cur.execute("""
            INSERT INTO tickets (usuario_id, nombre, telefono, domicilio, titulo, descripcion, categoria, tipo, estado, prioridad)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (usuario_id, nombre, telefono, domicilio, titulo, descripcion, categoria, tipo, estado, prioridad))
        conn.commit()
        ticket_id = cur.lastrowid
        cur.close()
        conn.close()

        return jsonify({'success': True, 'ticket_id': ticket_id}), 201
    except Exception as e:
        print("Error /api/crear-ticket:", e)
        return jsonify({'success': False, 'error': str(e)}), 500

# ---------- API: listar tickets (para admin.html) ----------
@app.route('/api/tickets', methods=['GET'])
def obtener_tickets():
    try:
        conn = get_db_connection()
        ensure_schema(conn)
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id, titulo, categoria, estado, prioridad, fecha, nombre, telefono, domicilio FROM tickets ORDER BY id DESC LIMIT 100")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify({'success': True, 'tickets': rows})
    except Exception as e:
        print("Error /api/tickets:", e)
        return jsonify({'success': False, 'error': str(e)}), 500

# ---------- Utilidad DB ----------
@app.route('/test_db')
def test_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT DATABASE();")
        db_name = cur.fetchone()[0]
        cur.close()
        conn.close()
        return f"Conexión exitosa a la base de datos: {db_name}"
    except mysql.connector.Error as err:
        return f"Error de conexión: {err}"

if __name__ == '__main__':
    app.run(debug=True, port=5000)

