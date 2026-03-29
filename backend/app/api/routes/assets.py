from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_db_dep, get_settings_dep, require_auth
from app.schemas.assets import AssetReuseRequest
from app.schemas.renders import AssetResponse, AssetSignedUrlResponse
from app.services.asset_service import AssetService
from app.services.render_service import RenderService

router = APIRouter()


@router.get("/library", response_model=list[AssetResponse])
def list_asset_library(
    search: str | None = Query(default=None),
    asset_role: str | None = Query(default=None),
    asset_type: str | None = Query(default=None),
    project_id: str | None = Query(default=None),
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return AssetService(db, settings).list_library_assets(
        auth,
        search=search,
        asset_role=asset_role,
        asset_type=asset_type,
        project_id=project_id,
    )


@router.post("/{asset_id}:reuse", response_model=AssetResponse)
def reuse_asset(
    asset_id: str,
    payload: AssetReuseRequest,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return AssetService(db, settings).reuse_asset(auth, asset_id, payload)


@router.post("/{asset_id}/signed-url", response_model=AssetSignedUrlResponse)
def create_signed_asset_url(
    asset_id: str,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return RenderService(db, settings).get_asset_signed_url(auth, asset_id)
