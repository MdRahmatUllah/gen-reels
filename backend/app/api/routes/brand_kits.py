from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_db_dep, require_auth
from app.schemas.brand_kits import BrandKitCreateRequest, BrandKitResponse, BrandKitUpdateRequest
from app.services.brand_kit_service import BrandKitService

router = APIRouter()


@router.get("", response_model=list[BrandKitResponse])
def list_brand_kits(
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
):
    return BrandKitService(db).list_brand_kits(auth)


@router.post("", response_model=BrandKitResponse)
def create_brand_kit(
    payload: BrandKitCreateRequest,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
):
    return BrandKitService(db).create_brand_kit(auth, payload)


@router.patch("/{brand_kit_id}", response_model=BrandKitResponse)
def patch_brand_kit(
    brand_kit_id: str,
    payload: BrandKitUpdateRequest,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
):
    return BrandKitService(db).update_brand_kit(auth, brand_kit_id, payload)
