"""
Diagnóstico de conexiones de Torqly.
Ejecutar con el servidor corriendo:  python scripts/check_connections.py
O sin servidor (modo interno):       python scripts/check_connections.py --internal
"""
from __future__ import annotations

import argparse
import sys
import os

# Asegura que el directorio raíz esté en el path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

# ── colores ────────────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def ok(msg):    print(f"  {GREEN}[OK]{RESET} {msg}")
def fail(msg):  print(f"  {RED}[FAIL]{RESET} {msg}")
def warn(msg):  print(f"  {YELLOW}[WARN]{RESET} {msg}")
def title(msg): print(f"\n{BOLD}{msg}{RESET}")

PASSED = []
FAILED = []


def check(label: str, result: bool, detail: str = ""):
    if result:
        ok(label)
        PASSED.append(label)
    else:
        fail(f"{label}{' — ' + detail if detail else ''}")
        FAILED.append(label)


# ── 1. BASE DE DATOS ──────────────────────────────────────────────────────────
def check_database():
    title("1. Base de datos")
    try:
        from app.database import SessionLocal
        from app.models import User
        from sqlalchemy import text

        with SessionLocal() as session:
            result = session.execute(text("SELECT 1")).scalar()
            check("Conexión a la DB", result == 1)

            user_count = session.execute(text("SELECT COUNT(*) FROM users")).scalar()
            check(f"Tabla 'users' accesible ({user_count} usuarios)", True)

            # Verificar columnas de migración 0006
            cols_raw = session.execute(text("SELECT name FROM pragma_table_info('users')")).fetchall()
            cols = {r[0] for r in cols_raw}
            for col in ("google_sub", "privacy_policy_version", "privacy_policy_accepted_at"):
                check(f"Columna users.{col} existe", col in cols)

    except Exception as exc:
        check("Conexión a la DB", False, str(exc))


# ── 2. AUTENTICACIÓN ──────────────────────────────────────────────────────────
def check_auth_internal():
    title("2. Autenticación (login interno)")
    try:
        from app.database import SessionLocal
        from app.services.users import authenticate_user
        from app.config import settings

        with SessionLocal() as session:
            user = authenticate_user(
                session,
                phone=settings.default_admin_phone,
                password=settings.default_admin_password,
            )
            check(
                f"Login con admin ({settings.default_admin_phone})",
                user is not None,
                "Verifica DEFAULT_ADMIN_PHONE y DEFAULT_ADMIN_PASSWORD en .env" if not user else "",
            )
    except Exception as exc:
        check("Login interno", False, str(exc))


# ── 3. GOOGLE OAUTH ───────────────────────────────────────────────────────────
def check_google():
    title("3. Google OAuth")
    try:
        from app.services.google_oauth import is_configured, get_auth_url, _redirect_uri
        from app.config import settings

        configured = is_configured()
        check("GOOGLE_CLIENT_ID y CLIENT_SECRET configurados", configured)

        if configured:
            check("google_login_enabled = True", settings.google_login_enabled)

            redirect = _redirect_uri()
            check(f"Redirect URI: {redirect}", True)

            try:
                auth_url, state, code_verifier = get_auth_url()
                check("get_auth_url() genera URL de autorización", bool(auth_url))
                check("state generado", bool(state))
                check(
                    f"code_verifier (PKCE): {'presente' if code_verifier else 'ausente (sin PKCE)'}",
                    True,
                )
                if "accounts.google.com" in auth_url:
                    ok("URL apunta a accounts.google.com")
                else:
                    warn(f"URL inesperada: {auth_url[:80]}")
            except Exception as exc:
                check("Generación de URL de autorización", False, str(exc))

    except Exception as exc:
        check("Módulo Google OAuth", False, str(exc))


# ── 4. INTEGRACIONES ──────────────────────────────────────────────────────────
def check_integrations():
    title("4. Estado de integraciones")
    try:
        from app.config import settings

        items = [
            ("Google Calendar", settings.google_calendar_enabled),
            ("Google Sheets",   settings.google_sheets_enabled),
            ("WhatsApp Cloud",  settings.whatsapp_enabled),
            ("ClickUp",         settings.clickup_enabled),
        ]
        for name, enabled in items:
            if enabled:
                ok(f"{name}: configurado")
            else:
                warn(f"{name}: sin credenciales (opcional)")

        warnings = settings.integration_warnings()
        if warnings:
            for w in warnings:
                warn(w)
        else:
            ok("Sin advertencias de integración")

    except Exception as exc:
        check("Configuración de integraciones", False, str(exc))


# ── 5. RUTAS HTTP (contra servidor en vivo) ───────────────────────────────────
def check_http(base_url: str):
    title(f"5. Rutas HTTP ({base_url})")
    try:
        import httpx

        with httpx.Client(base_url=base_url, follow_redirects=False, timeout=10) as client:

            # /health
            try:
                r = client.get("/health")
                check("/health responde 200", r.status_code == 200, f"status={r.status_code}")
                if r.status_code == 200:
                    data = r.json()
                    check("status=ok en /health", data.get("status") == "ok")
            except Exception as exc:
                check("/health accesible", False, str(exc))

            # /login
            try:
                r = client.get("/login")
                check("/login responde 200", r.status_code == 200, f"status={r.status_code}")
            except Exception as exc:
                check("/login accesible", False, str(exc))

            # /auth/google sin credenciales → debe redirigir
            try:
                r = client.get("/auth/google")
                check(
                    "/auth/google redirige a Google",
                    r.status_code in (302, 303),
                    f"status={r.status_code}",
                )
            except Exception as exc:
                check("/auth/google accesible", False, str(exc))

            # Login con admin
            try:
                from app.config import settings as cfg
                r = client.post(
                    "/login",
                    data={"phone": cfg.default_admin_phone, "password": cfg.default_admin_password},
                )
                check(
                    "POST /login con admin redirige al sistema",
                    r.status_code in (302, 303),
                    f"status={r.status_code}",
                )
            except Exception as exc:
                check("POST /login", False, str(exc))

    except ImportError:
        warn("httpx no disponible, saltando pruebas HTTP")


# ── 6. SCHEDULER ──────────────────────────────────────────────────────────────
def check_scheduler():
    title("6. Scheduler")
    try:
        from app.config import settings
        check("scheduler_enabled en config", settings.scheduler_enabled)
        check(f"daily_close_time = {settings.daily_close_time}", bool(settings.daily_close_time))
    except Exception as exc:
        check("Configuración de scheduler", False, str(exc))


# ── RESUMEN ───────────────────────────────────────────────────────────────────
def summary():
    total = len(PASSED) + len(FAILED)
    print(f"\n{BOLD}{'-'*50}{RESET}")
    print(f"{BOLD}Resultado: {GREEN}{len(PASSED)} OK{RESET}  {RED}{len(FAILED)} FALLIDOS{RESET}  de {total} checks")
    if FAILED:
        print(f"\n{RED}Checks fallidos:{RESET}")
        for f in FAILED:
            print(f"  • {f}")
    else:
        print(f"\n{GREEN}Todo en orden.{RESET}")
    print()


# ── MAIN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Diagnóstico de conexiones Torqly")
    parser.add_argument("--internal", action="store_true", help="Solo checks internos (sin servidor)")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="URL del servidor")
    args = parser.parse_args()

    print(f"\n{BOLD}=== Diagnóstico de conexiones Torqly ==={RESET}")

    check_database()
    check_auth_internal()
    check_google()
    check_integrations()
    check_scheduler()

    if not args.internal:
        check_http(args.url)
    else:
        warn("Pruebas HTTP omitidas (--internal)")

    summary()
    sys.exit(1 if FAILED else 0)
