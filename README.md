# Icasoft I21 – Mesa de Ayuda con Flask + MySQL

Sistema simple de tickets de soporte:
- **Frontend**: `index.html` (formulario + chatbot)
- **Panel Admin**: `/admin` (filtros y edición en línea)

> **Acceso directo (solo DEV)**  
> Usuario: `admin`  
> Contraseña: `admin123`  
> *Cámbialos en producción.*

---

## 1. Requisitos

- **Python** 3.10+ (recomendado 3.11 o superior)
- **MySQL** funcionando  
  - Por defecto este proyecto usa: `127.0.0.1:3307` (típico XAMPP)  
  - Usuario: `appuser` / Password: `app123` / Base: `soporte_ia`
- Navegador moderno (Chrome/Edge/Firefox)

---

## 2. Instalación rápida

### Windows (PowerShell)
```powershell
# 1) Clona el repo
git clone https://github.com/TU_USUARIO/TU_REPO.git
cd TU_REPO

# 2) Crea entorno virtual e instala dependencias
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt

# 3) Variables de entorno (crea tu .env desde el ejemplo)
copy ..\.env.example .env
# => edita backend\.env si tu MySQL/puerto/usuario difieren

# 4) Inicia la app
python routers.py
# Abre http://127.0.0.1:5000
