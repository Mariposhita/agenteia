# reset_admin.py (ejecútalo:  python reset_admin.py)
from werkzeug.security import generate_password_hash
from models import Database, TicketModel

db = Database()
m = TicketModel(db)
h = generate_password_hash("admin123", method="pbkdf2:sha256")
m.force_admin_password("admin", h, "Administrador", "admin@soporte.com")
print("Admin listo: admin / admin123")
