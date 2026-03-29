from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_db_dep, get_settings_dep, require_auth
from app.schemas.billing import UsageSummaryResponse
from app.services.billing_service import BillingService

router = APIRouter()


@router.get("", response_model=UsageSummaryResponse)
def get_usage(
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return BillingService(db, settings).get_usage(auth)

