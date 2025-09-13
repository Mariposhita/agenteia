# backend/models.py
import os
from typing import Optional, Any, Dict
import mysql.connector
from mysql.connector import errorcode

class Database:
    def __init__(self):
        # Lee .env (valores por defecto compatibles con XAMPP en 3307)
        self.host = os.getenv("DB_HOST", "127.0.0.1")
        self.user = os.getenv("DB_USER", "appuser")
        self.password = os.getenv("DB_PASSWORD", "app123")
        self.port = int(os.getenv("DB_PORT", "3307"))
        self.database = os.getenv("DB_NAME", "soporte_ia")
        self.cnx = None
        print("== DB cfg ==", self.host, self.user, self.port, self.database)  # debug

    def server_connect(self):
        """Conecta al servidor (sin BD) para poder crear la base si hace falta."""
        return mysql.connector.connect(
            host=self.host,
            user=self.user,
            password=self.password,
            port=self.port,
            connection_timeout=5,
        )

    def connect(self):
        """Conexión normal a la BD."""
        if self.cnx and self.cnx.is_connected():
            return self.cnx
        self.cnx = mysql.connector.connect(
            host=self.host,
            user=self.user,
            password=self.password,
            port=self.port,
            database=self.database,
            connection_timeout=5,
        )
        return self.cnx

    def cursor(self):
        self.connect()
        return self.cnx.cursor(dictionary=True)

    def commit(self):
        if self.cnx and self.cnx.is_connected():
            self.cnx.commit()

    def close(self):
        if self.cnx and self.cnx.is_connected():
            self.cnx.close()

    def init_schema(self):
        """Crea base y tablas si no existen. Si no hay permiso para CREATE, ignora el error."""
        # 1) Crear base de datos si tenemos permiso
        try:
            srv = self.server_connect()
            cur = srv.cursor()
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{self.database}` "
                "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
            )
            cur.close()
            srv.close()
        except mysql.connector.Error as e:
            if e.errno not in (errorcode.ER_DBACCESS_DENIED_ERROR, errorcode.ER_ACCESS_DENIED_ERROR):
                raise

        # 2) Crear tablas
        cnx = self.connect()
        cur = cnx.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE,
            password_hash VARCHAR(512),
            nombre VARCHAR(100) NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            role ENUM('usuario','admin') DEFAULT 'usuario',
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB;
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INT AUTO_INCREMENT PRIMARY KEY,
            usuario_id INT NULL,
            nombre VARCHAR(100),
            telefono VARCHAR(30),
            domicilio VARCHAR(200),
            titulo VARCHAR(200),
            descripcion TEXT NOT NULL,
            categoria ENUM('hardware','software','redes','otros') NOT NULL,
            tipo ENUM('preventivo','correctivo') NOT NULL,
            prioridad ENUM('baja','media','alta','critica') DEFAULT 'media',
            estado ENUM('abierto','en_proceso','resuelto','cerrado') DEFAULT 'abierto',
            asignado_admin BOOLEAN DEFAULT FALSE,
            solucion_ia TEXT,
            notas_admin TEXT,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            CONSTRAINT fk_tickets_usuario
              FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
              ON DELETE SET NULL ON UPDATE CASCADE
        ) ENGINE=InnoDB;
        """)

        cnx.commit()
        cur.close()


class TicketModel:
    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()

    # ---------- USUARIOS ----------
    def existe_admin(self) -> bool:
        cur = self.db.cursor()
        cur.execute("SELECT COUNT(*) AS c FROM usuarios WHERE role='admin'")
        row = cur.fetchone() or {}
        cur.close()
        return (row.get('c') or 0) > 0

    def crear_usuario(self, username, password_hash, nombre, email, role='usuario') -> int:
        cur = self.db.cursor()
        cur.execute("""
            INSERT INTO usuarios (username, password_hash, nombre, email, role)
            VALUES (%s,%s,%s,%s,%s)
        """, (username, password_hash, nombre, email, role))
        self.db.commit()
        uid = cur.lastrowid
        cur.close()
        return uid

    def upsert_admin(self, username, password_hash, nombre, email) -> int:
        """Inserta o actualiza el admin sin violar UNIQUE (username/email)."""
        cur = self.db.cursor()
        cur.execute("""
            INSERT INTO usuarios (username, password_hash, nombre, email, role)
            VALUES (%s,%s,%s,%s,'admin')
            ON DUPLICATE KEY UPDATE
              password_hash=VALUES(password_hash),
              nombre=VALUES(nombre),
              role='admin'
        """, (username, password_hash, nombre, email))
        self.db.commit()
        uid = cur.lastrowid
        cur.close()
        return uid

    def force_admin_password(self, username: str, password_hash: str, nombre: str, email: str) -> int:
        """
        Garantiza que exista un admin con 'username' y contraseña 'password_hash'.
        - Si existe por username: actualiza password/nombre/role (NO cambia email para no chocar con UNIQUE).
        - Si no existe por username pero sí por email: actualiza ese registro (password/nombre/role).
        - Si no existe ninguno: intenta insertar con el email dado; si el email ya está tomado, inserta con un alias.
        """
        cur = self.db.cursor()

        # 1) ¿Existe por username?
        cur.execute("SELECT id, email FROM usuarios WHERE username=%s LIMIT 1", (username,))
        row = cur.fetchone()
        if row:
            cur.execute(
                "UPDATE usuarios SET password_hash=%s, nombre=%s, role='admin' WHERE id=%s",
                (password_hash, nombre, row["id"])
            )
            self.db.commit()
            uid = row["id"]
            cur.close()
            return uid

        # 2) ¿Existe por email?
        cur.execute("SELECT id FROM usuarios WHERE email=%s LIMIT 1", (email,))
        row = cur.fetchone()
        if row:
            cur.execute(
                "UPDATE usuarios SET password_hash=%s, nombre=%s, role='admin' WHERE id=%s",
                (password_hash, nombre, row["id"])
            )
            self.db.commit()
            uid = row["id"]
            cur.close()
            return uid

        # 3) No existe: intenta insertar con el email pedido
        try:
            cur.execute(
                "INSERT INTO usuarios (username, password_hash, nombre, email, role) VALUES (%s,%s,%s,%s,'admin')",
                (username, password_hash, nombre, email)
            )
            self.db.commit()
            uid = cur.lastrowid
            cur.close()
            return uid
        except mysql.connector.Error as e:
            # Si falló por duplicado de email, inserta con un alias y sigue
            if e.errno == errorcode.ER_DUP_ENTRY:
                alias = f"admin+{username}@local"
                cur.execute(
                    "INSERT INTO usuarios (username, password_hash, nombre, email, role) VALUES (%s,%s,%s,%s,'admin')",
                    (username, password_hash, nombre, alias)
                )
                self.db.commit()
                uid = cur.lastrowid
                cur.close()
                return uid
            cur.close()
            raise

    def obtener_usuario_por_username(self, username) -> Optional[Dict[str, Any]]:
        cur = self.db.cursor()
        cur.execute("SELECT * FROM usuarios WHERE username=%s", (username,))
        row = cur.fetchone()
        cur.close()
        return row

    def obtener_usuario_por_username_o_email(self, v: str) -> Optional[Dict[str, Any]]:
        cur = self.db.cursor()
        cur.execute("SELECT * FROM usuarios WHERE username=%s OR email=%s LIMIT 1", (v, v))
        row = cur.fetchone()
        cur.close()
        return row

    # ---------- STATS (para cuadro comparativo) ----------
    def stats_resumen(self) -> Dict[str, Any]:
        cur = self.db.cursor()

        cur.execute("SELECT COUNT(*) AS total FROM tickets")
        total = (cur.fetchone() or {}).get("total", 0)

        cur.execute("SELECT estado, COUNT(*) c FROM tickets GROUP BY estado")
        estados_rows = cur.fetchall() or []
        estados = {r["estado"]: r["c"] for r in estados_rows}

        cur.execute("SELECT tipo, COUNT(*) c FROM tickets GROUP BY tipo")
        tipos_rows = cur.fetchall() or []
        tipos = {r["tipo"]: r["c"] for r in tipos_rows}

        cur.execute("SELECT categoria, COUNT(*) c FROM tickets GROUP BY categoria")
        cat_rows = cur.fetchall() or []
        categorias = {r["categoria"]: r["c"] for r in cat_rows}

        cur.close()
        return {
            "total": total,
            "estados": estados,       # abierto, en_proceso, resuelto, cerrado
            "tipos": tipos,           # preventivo, correctivo
            "categorias": categorias  # hardware, software, redes, otros
        }

    # ---------- TICKETS ----------
    def crear_ticket(self, usuario_id, titulo, descripcion, categoria, tipo,
                     nombre=None, telefono=None, domicilio=None,
                     prioridad='media', estado='abierto') -> int:
        cur = self.db.cursor()
        cur.execute("""
            INSERT INTO tickets
            (usuario_id, nombre, telefono, domicilio, titulo, descripcion,
             categoria, tipo, prioridad, estado)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (usuario_id, nombre, telefono, domicilio,
              titulo, descripcion, categoria, tipo, prioridad, estado))
        self.db.commit()
        tid = cur.lastrowid
        cur.close()
        return tid

    def actualizar_ticket(self, ticket_id, **updates):
        permitidos = {
            'estado', 'prioridad', 'notas_admin', 'asignado_admin', 'solucion_ia',
            'tipo', 'categoria', 'titulo', 'descripcion', 'nombre', 'telefono', 'domicilio'
        }
        sets, vals = [], []
        for k, v in updates.items():
            if k in permitidos:
                sets.append(f"{k}=%s")
                vals.append(v)
        if not sets:
            return
        vals.append(ticket_id)
        cur = self.db.cursor()
        cur.execute(f"UPDATE tickets SET {', '.join(sets)} WHERE id=%s", vals)
        self.db.commit()
        cur.close()

    def obtener_tickets(self, admin=False, usuario_id: Optional[int]=None):
        cur = self.db.cursor()
        base = """
          SELECT id, usuario_id, nombre, telefono, domicilio,
                 titulo, descripcion, categoria, tipo,
                 prioridad, estado, asignado_admin, solucion_ia,
                 notas_admin, fecha_creacion
          FROM tickets
        """
        if admin or not usuario_id:
            cur.execute(base + " ORDER BY fecha_creacion DESC")
        else:
            cur.execute(base + " WHERE usuario_id=%s ORDER BY fecha_creacion DESC", (usuario_id,))
        rows = cur.fetchall()
        cur.close()
        return rows
