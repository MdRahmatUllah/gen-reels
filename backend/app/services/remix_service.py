from __future__ import annotations

import random
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AuthContext
from app.core.config import Settings
from app.core.errors import ApiError
from app.integrations.media_ops import apply_video_effects, concat_video_clips
from app.integrations.storage import StorageClient, build_storage_client
from app.models.entities import (
    RemixJob,
    RemixProject,
    RemixVideo,
    VideoLibraryItem,
    VideoLibraryProject,
)
from app.schemas.remix import (
    RemixAnalyzeResponse,
    RemixJobResponse,
    RemixProjectCreate,
    RemixProjectResponse,
    RemixVideoResponse,
)

REMIX_BUCKET = "reels-video-library"
PRESIGNED_URL_TTL = 3600


def _project_to_response(p: RemixProject) -> RemixProjectResponse:
    return RemixProjectResponse(
        id=str(p.id),
        workspace_id=str(p.workspace_id),
        name=p.name,
        source_project_id=str(p.source_project_id) if p.source_project_id else None,
        visual_effects=dict(p.visual_effects or {}),
        target_duration_ms=p.target_duration_ms,
        clip_mode=p.clip_mode,
        output_project_id=str(p.output_project_id) if p.output_project_id else None,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


def _video_to_response(v: RemixVideo) -> RemixVideoResponse:
    return RemixVideoResponse(
        id=str(v.id),
        job_id=str(v.job_id),
        status=v.status,
        clip_ids=list(v.clip_ids or []),
        output_item_id=str(v.output_item_id) if v.output_item_id else None,
        error_message=v.error_message,
        created_at=v.created_at,
    )


def _job_to_response(job: RemixJob, db: Session) -> RemixJobResponse:
    videos = db.scalars(
        select(RemixVideo).where(RemixVideo.job_id == job.id).order_by(RemixVideo.created_at)
    ).all()
    return RemixJobResponse(
        id=str(job.id),
        remix_project_id=str(job.remix_project_id),
        workspace_id=str(job.workspace_id),
        status=job.status,
        total_videos=job.total_videos,
        completed_videos=job.completed_videos,
        failed_videos=job.failed_videos,
        videos=[_video_to_response(v) for v in videos],
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


def _get_source_clips(
    db: Session,
    workspace_id: uuid.UUID,
    source_project_id: uuid.UUID | None,
) -> list[VideoLibraryItem]:
    q = select(VideoLibraryItem).where(
        VideoLibraryItem.workspace_id == workspace_id
    )
    if source_project_id is not None:
        q = q.where(VideoLibraryItem.project_id == source_project_id)
    else:
        q = q.where(VideoLibraryItem.project_id.is_(None))
    return list(db.scalars(q).all())


def _analyze_random(clips: list[VideoLibraryItem], target_ms: int) -> int:
    """In random mode every clip can be the unique first clip of one video."""
    usable = [c for c in clips if (c.duration_ms or 0) > 0]
    return len(usable)


def _analyze_unique(clips: list[VideoLibraryItem], target_ms: int) -> int:
    """In unique mode clips are partitioned: floor(total_duration / target)."""
    total_ms = sum(c.duration_ms or 0 for c in clips)
    if target_ms <= 0:
        return 0
    return max(0, total_ms // target_ms)


def _plan_random_videos(
    clips: list[VideoLibraryItem],
    target_ms: int,
) -> list[list[VideoLibraryItem]]:
    """Plan clip lists for random mode.

    Each video has a unique first clip. Subsequent clips are drawn randomly
    (with replacement) until the target duration is met or exceeded.
    """
    usable = [c for c in clips if (c.duration_ms or 0) > 0]
    if not usable:
        return []

    shuffled_firsts = list(usable)
    random.shuffle(shuffled_firsts)

    plans: list[list[VideoLibraryItem]] = []
    for first in shuffled_firsts:
        selected = [first]
        duration = first.duration_ms or 0
        others = [c for c in usable if c.id != first.id]
        if not others:
            others = usable  # fallback if only one clip
        while duration < target_ms:
            clip = random.choice(others)
            selected.append(clip)
            duration += clip.duration_ms or 0
        plans.append(selected)
    return plans


def _plan_unique_videos(
    clips: list[VideoLibraryItem],
    target_ms: int,
) -> list[list[VideoLibraryItem]]:
    """Plan clip lists for unique mode.

    Clips are partitioned — each clip appears in at most one video.
    Greedy: fill each video bucket until target is reached, then start next.
    """
    usable = [c for c in clips if (c.duration_ms or 0) > 0]
    random.shuffle(usable)

    plans: list[list[VideoLibraryItem]] = []
    current: list[VideoLibraryItem] = []
    current_ms = 0

    for clip in usable:
        current.append(clip)
        current_ms += clip.duration_ms or 0
        if current_ms >= target_ms:
            plans.append(current)
            current = []
            current_ms = 0

    # Discard the last incomplete bucket — it's too short
    return plans


class RemixService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self._storage: StorageClient | None = None

    @property
    def storage(self) -> StorageClient:
        if self._storage is None:
            self._storage = build_storage_client(self.settings)
        return self._storage

    # ── Projects ──────────────────────────────────────────────────────────────

    def list_projects(self, auth: AuthContext) -> list[RemixProjectResponse]:
        rows = self.db.scalars(
            select(RemixProject)
            .where(RemixProject.workspace_id == uuid.UUID(auth.workspace_id))
            .order_by(RemixProject.created_at.desc())
        ).all()
        return [_project_to_response(r) for r in rows]

    def create_project(self, auth: AuthContext, payload: RemixProjectCreate) -> RemixProjectResponse:
        if payload.clip_mode not in ("random", "unique"):
            raise ApiError(400, "invalid_clip_mode", "clip_mode must be 'random' or 'unique'.")
        if payload.target_duration_ms <= 0:
            raise ApiError(400, "invalid_duration", "target_duration_ms must be positive.")

        source_project_id: uuid.UUID | None = None
        if payload.source_project_id:
            proj = self.db.scalar(
                select(VideoLibraryProject).where(
                    VideoLibraryProject.id == uuid.UUID(payload.source_project_id),
                    VideoLibraryProject.workspace_id == uuid.UUID(auth.workspace_id),
                )
            )
            if not proj:
                raise ApiError(404, "source_project_not_found", "Source video library project not found.")
            source_project_id = proj.id

        project = RemixProject(
            workspace_id=uuid.UUID(auth.workspace_id),
            name=payload.name.strip(),
            source_project_id=source_project_id,
            visual_effects=payload.visual_effects,
            target_duration_ms=payload.target_duration_ms,
            clip_mode=payload.clip_mode,
        )
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return _project_to_response(project)

    def get_project(self, auth: AuthContext, project_id: str) -> RemixProjectResponse:
        project = self._get_project(auth, project_id)
        return _project_to_response(project)

    def delete_project(self, auth: AuthContext, project_id: str) -> None:
        project = self._get_project(auth, project_id)
        self.db.delete(project)
        self.db.commit()

    def _get_project(self, auth: AuthContext, project_id: str) -> RemixProject:
        project = self.db.scalar(
            select(RemixProject).where(
                RemixProject.id == uuid.UUID(project_id),
                RemixProject.workspace_id == uuid.UUID(auth.workspace_id),
            )
        )
        if not project:
            raise ApiError(404, "not_found", "Remix project not found.")
        return project

    # ── Analysis ──────────────────────────────────────────────────────────────

    def analyze(self, auth: AuthContext, project_id: str) -> RemixAnalyzeResponse:
        project = self._get_project(auth, project_id)
        clips = _get_source_clips(
            self.db,
            uuid.UUID(auth.workspace_id),
            project.source_project_id,
        )
        clips_with_duration = [c for c in clips if (c.duration_ms or 0) > 0]
        total_duration_ms = sum(c.duration_ms or 0 for c in clips_with_duration)

        if project.clip_mode == "unique":
            possible = _analyze_unique(clips_with_duration, project.target_duration_ms)
        else:
            possible = _analyze_random(clips_with_duration, project.target_duration_ms)

        return RemixAnalyzeResponse(
            possible_videos=possible,
            total_clips=len(clips),
            total_duration_ms=total_duration_ms,
            clips_with_duration=len(clips_with_duration),
        )

    # ── Jobs ──────────────────────────────────────────────────────────────────

    def create_job(self, auth: AuthContext, project_id: str) -> RemixJobResponse:
        project = self._get_project(auth, project_id)
        clips = _get_source_clips(
            self.db,
            uuid.UUID(auth.workspace_id),
            project.source_project_id,
        )

        if project.clip_mode == "unique":
            plans = _plan_unique_videos(clips, project.target_duration_ms)
        else:
            plans = _plan_random_videos(clips, project.target_duration_ms)

        if not plans:
            raise ApiError(400, "no_videos_possible", "Not enough clips to create any videos with the current settings.")

        # Ensure output VideoLibraryProject exists
        if not project.output_project_id:
            output_proj = VideoLibraryProject(
                workspace_id=uuid.UUID(auth.workspace_id),
                name=project.name,
                description=f"Auto-generated by Remix: {project.name}",
            )
            self.db.add(output_proj)
            self.db.flush()
            project.output_project_id = output_proj.id

        job = RemixJob(
            remix_project_id=project.id,
            workspace_id=uuid.UUID(auth.workspace_id),
            status="pending",
            total_videos=len(plans),
        )
        self.db.add(job)
        self.db.flush()

        for plan in plans:
            rv = RemixVideo(
                job_id=job.id,
                workspace_id=uuid.UUID(auth.workspace_id),
                clip_ids=[str(c.id) for c in plan],
                status="pending",
            )
            self.db.add(rv)

        self.db.commit()
        self.db.refresh(job)

        # Dispatch Celery task
        from app.workers.tasks import execute_remix_job_task
        execute_remix_job_task.delay(str(job.id))

        return _job_to_response(job, self.db)

    def get_job(self, auth: AuthContext, job_id: str) -> RemixJobResponse:
        job = self.db.scalar(
            select(RemixJob).where(
                RemixJob.id == uuid.UUID(job_id),
                RemixJob.workspace_id == uuid.UUID(auth.workspace_id),
            )
        )
        if not job:
            raise ApiError(404, "not_found", "Remix job not found.")
        return _job_to_response(job, self.db)

    def list_jobs(self, auth: AuthContext, project_id: str) -> list[RemixJobResponse]:
        project = self._get_project(auth, project_id)
        jobs = self.db.scalars(
            select(RemixJob)
            .where(RemixJob.remix_project_id == project.id)
            .order_by(RemixJob.created_at.desc())
        ).all()
        return [_job_to_response(j, self.db) for j in jobs]

    # ── Execution (called from Celery worker) ─────────────────────────────────

    def execute_job(self, job_id: str) -> None:
        job = self.db.get(RemixJob, uuid.UUID(job_id))
        if not job:
            return

        project = self.db.get(RemixProject, job.remix_project_id)
        if not project:
            return

        job.status = "running"
        self.db.commit()

        videos = list(
            self.db.scalars(
                select(RemixVideo).where(RemixVideo.job_id == job.id)
            ).all()
        )

        fx = dict(project.visual_effects or {})

        for idx, video in enumerate(videos):
            try:
                self._process_remix_video(video, project, fx, idx)
                job.completed_videos += 1
            except Exception as exc:
                video.status = "failed"
                video.error_message = str(exc)[:1000]
                job.failed_videos += 1
            video.updated_at = datetime.now(timezone.utc)
            self.db.commit()

        job.status = "completed" if job.failed_videos == 0 else "failed"
        job.updated_at = datetime.now(timezone.utc)
        self.db.commit()

    def _process_remix_video(
        self,
        video: RemixVideo,
        project: RemixProject,
        fx: dict[str, object],
        index: int,
    ) -> None:
        video.status = "running"
        self.db.commit()

        # Fetch clip bytes from storage
        clip_ids = [uuid.UUID(cid) for cid in video.clip_ids]
        clips = [self.db.get(VideoLibraryItem, cid) for cid in clip_ids]
        clips = [c for c in clips if c is not None]

        if not clips:
            raise ValueError("No valid clips found for this video.")

        clip_bytes_list = [
            self.storage.read_bytes(c.bucket_name, c.object_name)
            for c in clips
        ]

        # Concatenate
        result_bytes, concat_meta = concat_video_clips(
            self.settings,
            clip_bytes_list=clip_bytes_list,
            target_width=1080,
            target_height=1920,
        )

        # Apply visual effects if any are set
        has_fx = (
            fx.get("brightness", 0) != 0
            or fx.get("contrast", 0) != 0
            or fx.get("saturation", 0) != 0
            or fx.get("color_filter", "none") not in ("none", "")
            or fx.get("vignette_strength", 0) > 0
            or fx.get("fade_in_sec", 0) > 0
            or fx.get("fade_out_sec", 0) > 0
        )
        if has_fx:
            result_bytes, _ = apply_video_effects(
                self.settings,
                source_bytes=result_bytes,
                source_file_name="remix.mp4",
                brightness=float(fx.get("brightness", 0)),
                contrast=float(fx.get("contrast", 0)),
                saturation=float(fx.get("saturation", 0)),
                speed=1.0,
                fade_in_sec=float(fx.get("fade_in_sec", 0)),
                fade_out_sec=float(fx.get("fade_out_sec", 0)),
                color_filter=str(fx.get("color_filter", "none")),
                vignette_strength=float(fx.get("vignette_strength", 0)),
            )

        # Upload to MinIO
        file_name = f"{_slugify(project.name)}-{index + 1:04d}.mp4"
        object_name = (
            f"workspace/{project.workspace_id}/remix/{project.id}/videos/{file_name}"
        )
        self.storage.ensure_bucket(REMIX_BUCKET)
        self.storage.put_bytes(REMIX_BUCKET, object_name, result_bytes, content_type="video/mp4")

        # Create VideoLibraryItem
        item = VideoLibraryItem(
            workspace_id=project.workspace_id,
            project_id=project.output_project_id,
            file_name=file_name,
            bucket_name=REMIX_BUCKET,
            object_name=object_name,
            content_type="video/mp4",
            size_bytes=len(result_bytes),
            duration_ms=concat_meta.get("duration_ms"),
            width=concat_meta.get("width"),
            height=concat_meta.get("height"),
        )
        self.db.add(item)
        self.db.flush()

        video.output_item_id = item.id
        video.status = "completed"


def _slugify(name: str) -> str:
    import re
    s = name.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or "remix"
