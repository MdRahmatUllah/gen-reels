from fastapi import APIRouter

from app.api.routes import admin, assets, auth, billing, ideas, presets, projects, renders, scene_plans, scripts, usage

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(ideas.router, prefix="/projects", tags=["ideas"])
api_router.include_router(scripts.router, prefix="/projects", tags=["scripts"])
api_router.include_router(scene_plans.router, prefix="/projects", tags=["scene-plans"])
api_router.include_router(renders.router, prefix="/projects", tags=["renders"])
api_router.include_router(presets.router, prefix="/presets", tags=["presets"])
api_router.include_router(usage.router, prefix="/usage", tags=["usage"])
api_router.include_router(billing.router, prefix="/billing", tags=["billing"])
api_router.include_router(renders.standalone_router, prefix="/renders", tags=["renders"])
api_router.include_router(assets.router, prefix="/assets", tags=["assets"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
