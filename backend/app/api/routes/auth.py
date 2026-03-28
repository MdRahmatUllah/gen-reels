from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_db_dep, get_redis_dep, get_settings_dep, require_auth
from app.schemas.auth import (
    LoginRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    SessionResponse,
    WorkspaceSelectRequest,
)
from app.schemas.common import MessageResponse
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/login", response_model=SessionResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
    redis_client=Depends(get_redis_dep),
):
    service = AuthService(db, settings, redis_client)
    session_payload, access_token, refresh_token = service.login(
        email=payload.email,
        password=payload.password,
        workspace_id=payload.workspace_id,
        user_agent=request.headers.get("User-Agent"),
        ip_address=request.client.host if request.client else None,
    )
    service.set_auth_cookies(response, access_token=access_token, refresh_token=refresh_token)
    return session_payload


@router.post("/logout", response_model=MessageResponse)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
    redis_client=Depends(get_redis_dep),
):
    service = AuthService(db, settings, redis_client)
    service.logout(request.cookies.get(settings.refresh_cookie_name))
    service.clear_auth_cookies(response)
    return {"message": "Logged out."}


@router.get("/session", response_model=SessionResponse)
def get_session(
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
    redis_client=Depends(get_redis_dep),
):
    service = AuthService(db, settings, redis_client)
    return service.session_snapshot(auth)


@router.post("/refresh", response_model=SessionResponse)
def refresh(
    request: Request,
    response: Response,
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
    redis_client=Depends(get_redis_dep),
):
    refresh_token = request.cookies.get(settings.refresh_cookie_name)
    service = AuthService(db, settings, redis_client)
    session_payload, access_token, new_refresh_token = service.refresh(refresh_token or "")
    service.set_auth_cookies(response, access_token=access_token, refresh_token=new_refresh_token)
    return session_payload


@router.post("/password-reset/request", response_model=MessageResponse, status_code=status.HTTP_202_ACCEPTED)
def request_password_reset(
    payload: PasswordResetRequest,
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
    redis_client=Depends(get_redis_dep),
):
    service = AuthService(db, settings, redis_client)
    service.request_password_reset(payload.email)
    return {"message": "If an account exists for that email, a reset link has been sent."}


@router.post("/password-reset/confirm", response_model=MessageResponse)
def confirm_password_reset(
    payload: PasswordResetConfirmRequest,
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
    redis_client=Depends(get_redis_dep),
):
    service = AuthService(db, settings, redis_client)
    service.confirm_password_reset(payload.token, payload.new_password)
    return {"message": "Password updated."}


@router.post("/workspace/select", response_model=SessionResponse)
def select_workspace(
    payload: WorkspaceSelectRequest,
    response: Response,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
    redis_client=Depends(get_redis_dep),
):
    service = AuthService(db, settings, redis_client)
    session_payload, access_token = service.select_workspace(auth, payload.workspace_id)
    service.set_auth_cookies(response, access_token=access_token, refresh_token=None)
    return session_payload
