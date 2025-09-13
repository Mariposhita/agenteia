# backend/routers.py
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

from flask import Flask, request, jsonify, render_template, session, redirect, url_for, flash
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from models import Database, TicketModel

from pathlib import Path
# Carga .env tanto de /backend como de la raíz del proyecto
here = Path(__file__).resolve().parent
load_dotenv(here / '.env')
load_dotenv(here.parent / '.env')


APP_ROOT = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.abspath(os.path.join(APP_ROOT, '../frontend'))

app = Flask(__name__, template_folder=TEMPLATES_DIR, static_folder=TEMPLATES_DIR)
app.secret_key = os.getenv("SECRET_KEY", "clave-secreta-por-defecto")
CORS(app)

# DB & modelos
db = Database()
db.init_schema()
ticket_model = TicketModel(db)

# ===== Admin por defecto =====
def ensure_admin():
    h = generate_password_hash("admin123", method="pbkdf2:sha256")
    ticket_model.force_admin_password(
        username="admin",
        password_hash=h,
        nombre="Administrador",
        email="admin@soporte.com",  # si ya está usado por otro, se respeta el email actual del admin
    )
    print("== Admin listo: admin / admin123")

ensure_admin()

# ===== Helpers =====
def login_required(f):
    from functools import wraps
    @wraps(f)
    def wrap(*a, **kw):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*a, **kw)
    return wrap

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def wrap(*a, **kw):
        if session.get('role') != 'admin':
            return "Acceso denegado", 403
        return f(*a, **kw)
    return wrap

# ===== Páginas =====
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/perfil')
def perfil():
    if 'user_id' in session:
        return redirect(url_for('admin'))
    return render_template('login.html')

# ⚠️ ÚNICA ruta de login (no tengas otra en el archivo)
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        user_input = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''
        if not user_input or not password:
            flash("Completa usuario y contraseña.", "error")
            return redirect(url_for('login', next=request.args.get('next')))

        user = ticket_model.obtener_usuario_por_username_o_email(user_input)
        print(f"DBG user_input: '{user_input}'")
        print("DBG user is None? ->", user is None)

        ok = False
        if user:
            try:
                ok = check_password_hash(user.get('password_hash') or '', password)
            except Exception as e:
                print("DBG check_password_hash error:", e)

        # Fallback DEV (ya pusiste ALLOW_DEV_PLAINTEXT=1 en .env)
        if not ok and os.getenv("ALLOW_DEV_PLAINTEXT") == "1" and user:
            ok = ((user.get('password_hash') or '') == password)
            print("DBG plaintext fallback used ->", ok)

        if not ok:
            flash("Usuario o contraseña incorrectos.", "error")
            return redirect(url_for('login', next=request.args.get('next')))

        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']
        return redirect(request.args.get('next') or url_for('admin'))

    return render_template('login.html')



@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin')
@login_required
@admin_required
def admin():
    # stats opcional si lo tienes implementado, si no, quítalo
    stats = {}
    if hasattr(ticket_model, 'stats_resumen'):
        stats = ticket_model.stats_resumen()
    tickets = ticket_model.obtener_tickets(admin=True)
    return render_template('admin.html', tickets=tickets, stats=stats)

# ===== API mínima =====
@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json(silent=True) or {}
    user_message = (data.get('message') or '').strip()
    if not user_message:
        return jsonify({"answer": "¿Podrías escribir tu consulta técnica?", "ticket_required": False}), 200
    m = user_message.lower()
    gatillos = ["lento","lenta","ticket","soporte","no enciende","pantalla azul","ssd","disco"]
    ticket_required = any(g in m for g in gatillos)
    pasos = (
        "Prueba esto:\n"
        "1) Reinicia y aplica actualizaciones.\n"
        "2) Desinstala programas que no uses.\n"
        "3) Limpia temporales (Win+R → cleanmgr).\n"
        "4) Revisa el Administrador de tareas.\n"
        "5) Escanea con antivirus."
    )
    if "lento" in m or "lenta" in m:
        answer = "Entiendo, tu equipo está lento. " + pasos + "\n\nSi sigue igual, deja **nombre, teléfono, domicilio y descripción** para crear ticket."
        ticket_required = True
    else:
        answer = "Gracias por tu consulta. " + pasos + "\n\nSi prefieres atención directa, comparte **nombre, teléfono, domicilio y descripción** para crear ticket."
    return jsonify({"answer": answer, "ticket_required": ticket_required}), 200

@app.route('/api/crear-ticket', methods=['POST'])
def api_crear_ticket():
    try:
        data = request.get_json(silent=True) or {}
        nombre = data.get('nombre')
        telefono = data.get('telefono')
        domicilio = data.get('domicilio')
        descripcion = data.get('descripcion') or data.get('problema')
        categoria = data.get('categoria', 'otros')
        titulo = data.get('titulo', 'Ticket de soporte')
        tipo = data.get('tipo', 'correctivo')

        if not all([nombre, telefono, domicilio, descripcion]):
            return jsonify({'success': False, 'message': 'Faltan campos obligatorios.'}), 400

        usuario_id = session.get('user_id')  # puede ser None
        tid = ticket_model.crear_ticket(
            usuario_id=usuario_id,
            titulo=titulo,
            descripcion=descripcion,
            categoria=categoria,
            tipo=tipo,
            nombre=nombre,
            telefono=telefono,
            domicilio=domicilio,
            prioridad='media',
            estado='abierto'
        )

        return jsonify({'success': True, 'ticket_id': tid,
                        'message': 'Ticket enviado correctamente.'}), 201
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/tickets')
@login_required
@admin_required
def api_tickets():
    tickets = ticket_model.obtener_tickets(admin=True)
    return jsonify({'success': True, 'tickets': tickets})

@app.route('/api/tickets/<int:ticket_id>', methods=['PATCH'])
@login_required
@admin_required
def api_update_ticket(ticket_id):
    data = request.get_json(silent=True) or {}

    # Solo permitimos cambiar estos campos desde la UI
    permitidos = {'estado', 'prioridad', 'tipo', 'categoria'}
    updates = {k: v for k, v in data.items() if k in permitidos and v}

    if not updates:
        return jsonify({'success': False, 'message': 'No hay campos válidos para actualizar.'}), 400

    try:
        ticket_model.actualizar_ticket(ticket_id, **updates)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ===== Diagnóstico =====
@app.route('/health/db')
def health_db():
    try:
        cnx = db.connect()
        cur = cnx.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        cur.close()
        return "DB OK", 200
    except Exception as e:
        return f"DB FAIL: {e}", 500

@app.route("/dbg_check")
def dbg_check():
    try:
        u = ticket_model.obtener_usuario_por_username_o_email("admin")
    except AttributeError:
        u = ticket_model.obtener_usuario_por_username("admin")
    if not u:
        return "user not found", 500
    ok = False
    try:
        ok = check_password_hash(u.get("password_hash") or "", "admin123")
    except Exception:
        ok = False
    prefix = (u.get("password_hash") or "")[:20]
    return f"prefix={prefix} ok={ok} role={u['role']}", 200

@app.route("/setup-admin")
def setup_admin():
    from werkzeug.security import generate_password_hash
    pwd = generate_password_hash("admin123", method="pbkdf2:sha256")
    try:
        ticket_model.upsert_admin("admin", pwd, "Administrador", "admin@soporte.com")
    except AttributeError:
        u = ticket_model.obtener_usuario_por_username("admin")
        if not u:
            ticket_model.crear_usuario("admin", pwd, "Administrador", "admin@soporte.com", role="admin")
    return "Admin listo: admin / admin123", 200

@app.route("/dev-login")
def dev_login():
    try:
        u = ticket_model.obtener_usuario_por_username_o_email("admin")
    except AttributeError:
        u = ticket_model.obtener_usuario_por_username("admin")
    if not u:
        return "No existe admin. Ejecuta /setup-admin primero.", 400
    session['user_id'] = u['id']
    session['username'] = u['username']
    session['role']     = u['role']
    return redirect(url_for('admin'))


if __name__ == '__main__':
    print("== DB cfg ==", db.host, db.user, db.port, db.database)
    print("== templates dir =>", TEMPLATES_DIR)
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=True, use_reloader=True)
