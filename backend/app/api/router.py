from fastapi import APIRouter

from app.api.routes import auth, ideas, projects, scripts

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(ideas.router, prefix="/projects", tags=["ideas"])
api_router.include_router(scripts.router, prefix="/projects", tags=["scripts"])
