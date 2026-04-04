from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_db_dep, get_settings_dep, require_auth
from app.schemas.videos import (
    ApproveVideoMetadataRequest,
    BatchScheduleRequest,
    BatchScheduleResponse,
    PublishJobResponse,
    ScheduleVideoRequest,
    VideoActionAcceptedResponse,
    VideoResponse,
)
from app.services.publish_job_service import PublishJobService
from app.services.video_service import VideoService

router = APIRouter()


@router.get("", response_model=list[VideoResponse])
def list_videos(
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return VideoService(db, settings).list_videos(auth)


@router.get("/{video_id}", response_model=VideoResponse)
def get_video(
    video_id: str,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return VideoService(db, settings).get_video(auth, video_id)


@router.post("/upload", response_model=VideoResponse, status_code=201)
async def upload_video(
    file: UploadFile = File(...),
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    bytes_payload = await file.read()
    service = VideoService(db, settings)
    video = service.upload_video(
        auth,
        file_name=file.filename or "upload.mp4",
        content_type=file.content_type,
        bytes_payload=bytes_payload,
    )
    from app.workers.video_processing import process_uploaded_video_task

    process_uploaded_video_task.delay(str(video["id"]))
    return video


@router.post("/{video_id}/generate-metadata", response_model=VideoActionAcceptedResponse)
def generate_metadata(
    video_id: str,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    service = VideoService(db, settings)
    video = service.get_video(auth, video_id)
    if video.get("transcript") is None:
        from app.workers.video_processing import process_uploaded_video_task

        process_uploaded_video_task.delay(video_id)
        return {"video_id": video["id"], "status": "queued", "message": "Transcription and metadata generation queued."}

    from app.workers.video_processing import regenerate_video_metadata_task

    regenerate_video_metadata_task.delay(video_id)
    return {"video_id": video["id"], "status": "queued", "message": "Metadata regeneration queued."}


@router.post("/{video_id}/approve-metadata", response_model=VideoResponse)
def approve_metadata(
    video_id: str,
    payload: ApproveVideoMetadataRequest,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return VideoService(db, settings).approve_metadata(
        auth,
        video_id=video_id,
        metadata_version_id=str(payload.metadata_version_id) if payload.metadata_version_id else None,
        title=payload.title,
        description=payload.description,
        tags=payload.tags,
        hook_summary=payload.hook_summary,
        youtube_account_id=str(payload.youtube_account_id) if payload.youtube_account_id else None,
    )


@router.post("/{video_id}/schedule", response_model=PublishJobResponse)
def schedule_video(
    video_id: str,
    payload: ScheduleVideoRequest,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return PublishJobService(db, settings).schedule_video(auth, video_id, payload)


@router.post("/batch-schedule", response_model=BatchScheduleResponse)
def batch_schedule_videos(
    payload: BatchScheduleRequest,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return PublishJobService(db, settings).batch_schedule(auth, payload)
