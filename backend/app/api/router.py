from fastapi import APIRouter

from app.api.routes import (
    admin,
    assets,
    auth,
    billing,
    brand_kits,
    comments,
    ideas,
    local_workers,
    notifications,
    presets,
    projects,
    remix,
    renders,
    reviews,
    scene_plans,
    series,
    scripts,
    templates,
    usage,
    video_library,
    workspace,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(series.router, prefix="/series", tags=["series"])
api_router.include_router(ideas.router, prefix="/projects", tags=["ideas"])
api_router.include_router(scripts.router, prefix="/projects", tags=["scripts"])
api_router.include_router(scene_plans.router, prefix="/projects", tags=["scene-plans"])
api_router.include_router(renders.router, prefix="/projects", tags=["renders"])
api_router.include_router(presets.router, prefix="/presets", tags=["presets"])
api_router.include_router(usage.router, prefix="/usage", tags=["usage"])
api_router.include_router(billing.router, prefix="/billing", tags=["billing"])
api_router.include_router(renders.standalone_router, prefix="/renders", tags=["renders"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(assets.router, prefix="/assets", tags=["assets"])
api_router.include_router(templates.router, prefix="/templates", tags=["templates"])
api_router.include_router(brand_kits.router, prefix="/brand-kits", tags=["brand-kits"])
api_router.include_router(comments.router, prefix="/comments", tags=["comments"])
api_router.include_router(reviews.router, prefix="/reviews", tags=["reviews"])
api_router.include_router(workspace.router, prefix="/workspace", tags=["workspace"])
api_router.include_router(local_workers.router, prefix="/local-workers", tags=["local-workers"])
api_router.include_router(local_workers.router, prefix="/workers", tags=["workers"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(video_library.router, prefix="/video-library", tags=["video-library"])
api_router.include_router(remix.router, prefix="/remix", tags=["remix"])
