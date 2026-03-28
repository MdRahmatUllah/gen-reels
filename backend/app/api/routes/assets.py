from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_db_dep, get_settings_dep, require_auth
from app.schemas.renders import AssetSignedUrlResponse
from app.services.render_service import RenderService

router = APIRouter()


@router.post("/{asset_id}/signed-url", response_model=AssetSignedUrlResponse)
def create_signed_asset_url(
    asset_id: str,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return RenderService(db, settings).get_asset_signed_url(auth, asset_id)
