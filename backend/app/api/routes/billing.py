from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_db_dep, get_settings_dep, require_auth
from app.schemas.billing import BillingUrlResponse, SubscriptionResponse, UsageSummaryResponse
from app.services.billing_service import BillingService

router = APIRouter()


@router.get("", response_model=UsageSummaryResponse)
def get_usage(
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return BillingService(db, settings).get_usage(auth)


@router.get("/subscription", response_model=SubscriptionResponse)
def get_subscription(
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return BillingService(db, settings).get_subscription_for_workspace(auth)


@router.post("/checkout", response_model=BillingUrlResponse)
def create_checkout_session(
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return BillingService(db, settings).create_checkout_session(auth)


@router.post("/portal", response_model=BillingUrlResponse)
def create_portal_session(
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return BillingService(db, settings).create_portal_session(auth)

