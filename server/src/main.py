from contextlib import asynccontextmanager
from pathlib import Path
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from .config import settings, BASE_DIR
from .database import init_db, SessionLocal
from .api import api_router
from .services.watchdog import HeartbeatWatchdog
from .services.dispatcher import JobDispatcher

async def run_periodic_dispatcher(interval_seconds: int = 5):
    """Periodically drain queued jobs when agents are idle."""
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            db = SessionLocal()
            try:
                await JobDispatcher.dispatch_next_job(db)
            finally:
                db.close()
        except asyncio.CancelledError:
            break
        except Exception:
            pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize DB tables and Heartbeat Watchdog
    init_db()
    watchdog_task = asyncio.create_task(
        HeartbeatWatchdog.run_periodic_watchdog(interval_seconds=10, timeout_seconds=settings.WS_HEARTBEAT_TIMEOUT_SEC)
    )
    dispatcher_task = asyncio.create_task(run_periodic_dispatcher(interval_seconds=3))
    yield
    # Shutdown: Cleanly cancel background tasks
    watchdog_task.cancel()
    dispatcher_task.cancel()
    try:
        await watchdog_task
    except asyncio.CancelledError:
        pass
    try:
        await dispatcher_task
    except asyncio.CancelledError:
        pass

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Control Plane API for Enterprise Playwright Test Orchestration",
    lifespan=lifespan,
)

# CORS middleware for Frontend UI dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

UI_DIR = Path(BASE_DIR).parent / "ui"

@app.get("/", tags=["Dashboard"])
def get_dashboard():
    """Serve the UiPath-style interactive dashboard."""
    index_file = UI_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "UiPath-style dashboard UI directory initialized"}

if UI_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(UI_DIR)), name="static")

@app.get("/health", tags=["Health"])
def health_check():
    """Service health and readiness probe."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "api_version": "v1",
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server.src.main:app", host="0.0.0.0", port=8000, reload=True)
