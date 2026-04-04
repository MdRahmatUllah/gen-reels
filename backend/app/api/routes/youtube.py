from __future__ import annotations

import logging
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import (
    AuthContext,
    get_db_dep,
    get_redis_dep,
    get_settings_dep,
    require_auth,
)
from app.core.errors import AdapterError, ApiError
from app.schemas.common import MessageResponse
from app.schemas.videos import PublishJobResponse
from app.schemas.youtube import OAuthConnectResponse, PublishScheduleResponse, PublishScheduleUpsertRequest, YouTubeAccountResponse
from app.services.publish_job_service import PublishJobService
from app.services.publish_schedule_service import PublishScheduleService
from app.services.youtube_account_service import YouTubeAccountService

logger = logging.getLogger(__name__)

integration_router = APIRouter()
schedule_router = APIRouter()
publish_jobs_router = APIRouter()


@integration_router.get("/connect", response_model=OAuthConnectResponse)
def connect_youtube_account(
    redirect_path: str = Query(default="/app/publishing/accounts"),
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
    redis_client=Depends(get_redis_dep),
):
    authorization_url = YouTubeAccountService(db, settings, redis_client=redis_client).request_connect_url(
        auth,
        redirect_path=redirect_path,
    )
    return {"authorization_url": authorization_url}


@integration_router.get("/callback")
def youtube_callback(
    state: str,
    code: str,
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
    redis_client=Depends(get_redis_dep),
):
    service = YouTubeAccountService(db, settings, redis_client=redis_client)
    try:
        _, redirect_url = service.complete_callback(state=state, code=code)
        return RedirectResponse(redirect_url, status_code=302)
    except (ApiError, AdapterError) as exc:
        error_code = getattr(exc, "code", "youtube_callback_failed")
        logger.warning(
            "youtube_callback_failed code=%s message=%s",
            error_code,
            getattr(exc, "message", str(exc)),
        )
        query = urlencode(
            {
                "youtube": "failed",
                "error": error_code,
                "error_message": getattr(exc, "message", str(exc)),
            }
        )
        return RedirectResponse(
            f"{settings.frontend_url_resolved}/app/publishing/accounts?{query}",
            status_code=302,
        )


@integration_router.get("/accounts", response_model=list[YouTubeAccountResponse])
def list_youtube_accounts(
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return YouTubeAccountService(db, settings).list_accounts(auth)


@integration_router.post("/disconnect/{youtube_account_id}", response_model=MessageResponse)
def disconnect_youtube_account(
    youtube_account_id: str,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    YouTubeAccountService(db, settings).disconnect(auth, youtube_account_id)
    return {"message": "YouTube account disconnected."}


@integration_router.post("/accounts/{youtube_account_id}/default", response_model=YouTubeAccountResponse)
def set_default_youtube_account(
    youtube_account_id: str,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return YouTubeAccountService(db, settings).set_default(auth, youtube_account_id)


@schedule_router.get("/schedules", response_model=list[PublishScheduleResponse])
def list_publish_schedules(
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return PublishScheduleService(db, settings).list_schedules(auth)


@schedule_router.post("/schedules", response_model=PublishScheduleResponse, status_code=201)
def create_publish_schedule(
    payload: PublishScheduleUpsertRequest,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return PublishScheduleService(db, settings).create_schedule(auth, payload)


@schedule_router.put("/schedules/{schedule_id}", response_model=PublishScheduleResponse)
def update_publish_schedule(
    schedule_id: str,
    payload: PublishScheduleUpsertRequest,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return PublishScheduleService(db, settings).update_schedule(auth, schedule_id, payload)


@publish_jobs_router.get("/publish-jobs", response_model=list[PublishJobResponse])
def list_publish_jobs(
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return PublishJobService(db, settings).list_jobs(auth)
