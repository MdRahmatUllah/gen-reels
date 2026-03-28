from __future__ import annotations

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_db_dep, get_settings_dep, require_auth
from app.schemas.scene_plans import ScenePlanJobResponse, ScenePlanPatchRequest, ScenePlanResponse
from app.services.content_planning_service import ContentPlanningService

router = APIRouter()


@router.post(
    "/{project_id}/scene-plan:generate",
    response_model=ScenePlanJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def generate_scene_plan(
    project_id: str,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return ContentPlanningService(db, settings).queue_scene_plan_generation(
        auth,
        project_id,
        idempotency_key=idempotency_key,
    )


@router.post(
    "/{project_id}/scene-plans/{scene_plan_id}:generate-prompt-pairs",
    response_model=ScenePlanJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def generate_prompt_pairs(
    project_id: str,
    scene_plan_id: str,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return ContentPlanningService(db, settings).queue_prompt_pair_generation(
        auth,
        project_id,
        scene_plan_id,
        idempotency_key=idempotency_key,
    )


@router.get("/{project_id}/scene-plans", response_model=list[ScenePlanResponse])
def list_scene_plans(
    project_id: str,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return ContentPlanningService(db, settings).list_scene_plans(auth, project_id)


@router.get("/{project_id}/scene-plans/{scene_plan_id}", response_model=ScenePlanResponse)
def get_scene_plan(
    project_id: str,
    scene_plan_id: str,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return ContentPlanningService(db, settings).get_scene_plan_detail(auth, project_id, scene_plan_id)


@router.patch("/{project_id}/scene-plans/{scene_plan_id}", response_model=ScenePlanResponse)
def patch_scene_plan(
    project_id: str,
    scene_plan_id: str,
    payload: ScenePlanPatchRequest,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return ContentPlanningService(db, settings).patch_scene_plan(
        auth,
        project_id,
        scene_plan_id,
        payload,
    )


@router.post("/{project_id}/scene-plans/{scene_plan_id}:approve", response_model=ScenePlanResponse)
def approve_scene_plan(
    project_id: str,
    scene_plan_id: str,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return ContentPlanningService(db, settings).approve_scene_plan(auth, project_id, scene_plan_id)
