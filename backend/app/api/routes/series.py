from __future__ import annotations

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_db_dep, get_settings_dep, require_auth
from app.schemas.series import (
    SeriesCatalogResponse,
    SeriesCreateRequest,
    SeriesDetailResponse,
    SeriesRunCreateRequest,
    SeriesRunResponse,
    SeriesScriptResponse,
    SeriesSummaryResponse,
    SeriesUpdateRequest,
)
from app.services.routing_service import RoutingService
from app.services.series_generation_service import SeriesGenerationService
from app.services.series_service import SeriesService

router = APIRouter()


@router.get("/catalog", response_model=SeriesCatalogResponse)
def get_series_catalog(
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    del auth, settings
    return SeriesService(db).get_series_catalog()


@router.get("", response_model=list[SeriesSummaryResponse])
def list_series(
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
):
    return SeriesService(db).list_series(auth)


@router.post("", response_model=SeriesDetailResponse, status_code=status.HTTP_201_CREATED)
def create_series(
    payload: SeriesCreateRequest,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    moderation_provider, _decision = RoutingService(db, settings).build_moderation_provider_for_workspace(
        auth.workspace_id
    )
    return SeriesService(db).create_series(auth, payload, moderation_provider)


@router.get("/{series_id}", response_model=SeriesDetailResponse)
def get_series_detail(
    series_id: str,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
):
    return SeriesService(db).get_series_detail(auth, series_id)


@router.patch("/{series_id}", response_model=SeriesDetailResponse)
def update_series(
    series_id: str,
    payload: SeriesUpdateRequest,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    moderation_provider, _decision = RoutingService(db, settings).build_moderation_provider_for_workspace(
        auth.workspace_id
    )
    return SeriesService(db).update_series(auth, series_id, payload, moderation_provider)


@router.get("/{series_id}/scripts", response_model=list[SeriesScriptResponse])
def list_series_scripts(
    series_id: str,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return SeriesGenerationService(db, settings).list_series_scripts(auth, series_id)


@router.post(
    "/{series_id}/runs",
    response_model=SeriesRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def start_series_run(
    series_id: str,
    payload: SeriesRunCreateRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    moderation_provider, _decision = RoutingService(db, settings).build_moderation_provider_for_workspace(
        auth.workspace_id
    )
    return SeriesGenerationService(db, settings).queue_series_run(
        auth,
        series_id,
        payload,
        idempotency_key=idempotency_key,
        moderation_provider=moderation_provider,
    )


@router.get("/{series_id}/runs/{run_id}", response_model=SeriesRunResponse)
def get_series_run(
    series_id: str,
    run_id: str,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return SeriesGenerationService(db, settings).get_series_run(auth, series_id, run_id)
