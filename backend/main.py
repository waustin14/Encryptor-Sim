from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.app.api.auth import router as auth_router
from backend.app.api.system import router as system_router
from backend.app.db.session import create_session_factory
from backend.app.services.daemon_ipc import send_command
from backend.app.services.isolation_validation_service import record_validation_result
from backend.app.ws.system import router as system_ws_router

# Path to frontend static files
STATIC_DIR = Path(__file__).parent / "static"

def sync_validation_result_from_daemon() -> None:
    with suppress(Exception):
        response = send_command("get_validation_result")
        result = response.get("result")
        if result is not None:
            session_factory = create_session_factory()
            session = session_factory()
            try:
                record_validation_result(session, result)
            finally:
                session.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    sync_validation_result_from_daemon()
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(auth_router)
app.include_router(system_router)
app.include_router(system_ws_router)

# Serve frontend static files (must be mounted AFTER API routes)
# html=True enables SPA fallback - serves index.html for non-file routes
if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
