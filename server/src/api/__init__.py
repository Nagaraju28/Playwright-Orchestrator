from fastapi import APIRouter
from .projects import router as projects_router
from .agents import router as agents_router
from .jobs import router as jobs_router
from .websocket import router as ws_router
from .artifacts import router as artifacts_router

api_router = APIRouter()
api_router.include_router(projects_router)
api_router.include_router(agents_router)
api_router.include_router(jobs_router)
api_router.include_router(ws_router)
api_router.include_router(artifacts_router)

__all__ = ["api_router"]
