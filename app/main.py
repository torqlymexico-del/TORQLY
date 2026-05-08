from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import SessionLocal
from app.routes.api import api_router
from app.routes.public_api import router as public_api_router
from app.routes.spa_auth import router as spa_auth_router
from app.routes.webhooks import router as webhook_router
from app.services.bootstrap import ensure_default_admin
from app.services.scheduler import start_scheduler, stop_scheduler
from app.utils.logger import configure_logging, get_logger


configure_logging()
logger = get_logger(__name__)

_static_dir = Path(__file__).resolve().parent / "static"
_dist_dir   = _static_dir / "dist"
_spa_index  = _dist_dir / "index.html"


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        with SessionLocal() as session:
            admin = ensure_default_admin(session)
            if admin:
                logger.info("Usuario bootstrap listo: %s", admin.phone)
    except Exception as exc:
        logger.warning("No fue posible ejecutar bootstrap inicial: %s", exc)
    scheduler_state = start_scheduler()
    if not scheduler_state.get("started"):
        logger.info("Scheduler no iniciado: %s", scheduler_state.get("reason"))
    yield
    stop_scheduler()


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    version="0.1.0",
    description="MVP modular para operación de lavado y detallado automotriz.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Archivos estáticos legacy (CSS/imágenes del sistema anterior)
app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

# Uploads del chat (imágenes, archivos)
_uploads_dir = Path(__file__).resolve().parent.parent / "uploads"
_uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(_uploads_dir)), name="uploads")

# Assets del build de React (JS/CSS compilados)
if (_dist_dir / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(_dist_dir / "assets")), name="spa-assets")

# Rutas de API y webhooks
app.include_router(api_router)
app.include_router(public_api_router)
app.include_router(webhook_router)

# Rutas server-side mínimas: Google OAuth + logout
app.include_router(spa_auth_router)


@app.get("/health")
def healthcheck() -> dict:
    return {
        "status": "ok",
        "app": settings.app_name,
        "warnings": settings.integration_warnings(),
        "scheduler_enabled": settings.scheduler_enabled,
        "daily_close_time": settings.daily_close_time,
    }


@app.get("/favicon.svg", include_in_schema=False)
def favicon():
    f = _dist_dir / "favicon.svg"
    if f.exists():
        return FileResponse(str(f))
    return HTMLResponse("", status_code=404)


@app.get("/icons.svg", include_in_schema=False)
def icons_svg():
    f = _dist_dir / "icons.svg"
    if f.exists():
        return FileResponse(str(f))
    return HTMLResponse("", status_code=404)


# SPA catch-all: cualquier ruta que no sea API ni OAuth sirve el index.html de React
@app.get("/{full_path:path}", include_in_schema=False)
def spa_fallback(full_path: str):
    if _spa_index.exists():
        return FileResponse(str(_spa_index))
    return HTMLResponse(
        "<h2>Frontend no compilado.</h2><p>Ejecuta: <code>cd frontend && npm run build</code></p>",
        status_code=503,
    )
