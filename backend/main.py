import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles

from backend.app.api.auth import router as auth_router
from backend.app.api.interfaces import router as interfaces_router
from backend.app.api.monitoring import router as monitoring_router
from backend.app.api.peers import router as peers_router
from backend.app.api.routes import router as routes_router
from backend.app.api.system import router as system_router
from backend.app.config import get_settings
from backend.app.db.init import init_db
from backend.app.db.session import create_session_factory
from backend.app.services.daemon_ipc import send_command
from backend.app.services.isolation_validation_service import record_validation_result
from backend.app.ws.monitoring import router as monitoring_ws_router
from backend.app.ws.system import router as system_ws_router

# Path to frontend static files
STATIC_DIR = Path(__file__).parent / "static"

def sync_validation_result_from_daemon() -> None:
    with suppress(Exception):
        response = send_command("get_validation_result")
        result = response.get("result")
        if result is not None:
            settings = get_settings()
            session_factory = create_session_factory(settings.database_url)
            session = session_factory()
            try:
                record_validation_result(session, result)
            finally:
                session.close()


logger = logging.getLogger(__name__)

_background_tasks: list[asyncio.Task] = []


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    sync_validation_result_from_daemon()

    # Start background polling tasks for monitoring
    from backend.app.ws.background_tasks import poll_interface_stats, poll_tunnel_status

    tunnel_task = asyncio.create_task(poll_tunnel_status())
    stats_task = asyncio.create_task(poll_interface_stats())
    _background_tasks.extend([tunnel_task, stats_task])
    logger.info("Background monitoring tasks started")

    yield

    # Cancel background tasks on shutdown
    for task in _background_tasks:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
    _background_tasks.clear()
    logger.info("Background monitoring tasks stopped")


app = FastAPI(lifespan=lifespan)
app.include_router(auth_router)
app.include_router(interfaces_router)
app.include_router(monitoring_router)
app.include_router(peers_router)
app.include_router(routes_router)
app.include_router(system_router)
app.include_router(monitoring_ws_router)
app.include_router(system_ws_router)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Encryptor Simulator API",
        version="1.0.0",
        description="API for managing IPsec tunnels and network configuration",
        routes=app.routes,
    )

    openapi_schema.setdefault("components", {})
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": (
                "JWT access token obtained from POST /api/v1/auth/login. "
                "Access tokens expire after 1 hour; use POST /api/v1/auth/refresh "
                "with the refresh token to obtain a new access token."
            ),
        }
    }

    # Apply Bearer auth to all endpoints except those tagged "auth"
    # Note: This assumes all non-auth endpoints require authentication.
    # If adding public endpoints in the future, tag them appropriately.
    for path_operations in openapi_schema.get("paths", {}).values():
        for operation in path_operations.values():
            if isinstance(operation, dict) and "auth" not in operation.get("tags", []):
                operation["security"] = [{"BearerAuth": []}]

    app.openapi_schema = openapi_schema
    return openapi_schema


app.openapi = custom_openapi

# Serve frontend static files (must be mounted AFTER API routes)
# html=True enables SPA fallback - serves index.html for non-file routes
if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
