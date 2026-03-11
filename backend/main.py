"""
ShopSerp FastAPI application entry-point.

Starts the async database, background scheduler, serves API routes
and the static frontend.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.config import settings
from backend.database import init_db
from backend.schemas import HealthResponse

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("shopserp")

# ── Scheduler helpers ─────────────────────────────────────────────────────────

def _start_scheduler() -> None:
    """Start the background scheduler for periodic monitor checks."""
    try:
        from backend.scheduler import start_scheduler
        start_scheduler()
        logger.info("Background scheduler started")
    except Exception:
        logger.exception("Failed to start background scheduler")


def _stop_scheduler() -> None:
    try:
        from backend.scheduler import stop_scheduler
        stop_scheduler()
        logger.info("Background scheduler stopped")
    except Exception:
        pass


# ── Lifespan ──────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup
    logger.info("Initialising database...")
    await init_db()
    logger.info("Database ready")

    _start_scheduler()

    yield

    # Shutdown
    _stop_scheduler()


# ── Application ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="ShopSerp",
    description="Self-hosted Google Shopping price tracker",
    version="0.1.0",
    lifespan=lifespan,
)

# ── CORS (permissive for self-hosted use) ─────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API routes ────────────────────────────────────────────────────────────────
# Import routers only if modules exist; the stubs ship with empty __init__.py
# so we guard against ImportError until the router files are created.

_router_modules = (
    ("backend.routers.search", "search"),
    ("backend.routers.monitors", "monitors"),
    ("backend.routers.analytics", "analytics"),
    ("backend.routers.settings_router", "settings_router"),
)

for _module_path, _attr in _router_modules:
    try:
        import importlib

        _mod = importlib.import_module(_module_path)
        _router = getattr(_mod, "router", None)
        if _router is not None:
            app.include_router(_router, prefix="/api")
            logger.info("Registered router from %s", _module_path)
    except ModuleNotFoundError:
        logger.debug("Router module %s not yet implemented, skipping", _module_path)

# ── Health check ──────────────────────────────────────────────────────────────


@app.get("/api/health", response_model=HealthResponse, tags=["health"])
@app.get("/health", include_in_schema=False)
async def health_check() -> HealthResponse:
    return HealthResponse()


# ── Static frontend ──────────────────────────────────────────────────────────

_frontend_dir = Path(__file__).resolve().parent.parent / "frontend"

if _frontend_dir.is_dir():
    app.mount("/assets", StaticFiles(directory=str(_frontend_dir / "assets")), name="assets") if (_frontend_dir / "assets").is_dir() else None

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str) -> FileResponse:
        """Serve the SPA index.html for any path not matched by the API."""
        file_path = _frontend_dir / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        index = _frontend_dir / "index.html"
        if index.is_file():
            return FileResponse(str(index))
        from fastapi.responses import JSONResponse

        return JSONResponse({"detail": "Frontend not built yet"}, status_code=404)
