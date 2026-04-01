from __future__ import annotations

import mimetypes
import re
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AuthContext
from app.core.config import Settings
from app.core.errors import ApiError
from app.integrations.storage import StorageClient, build_storage_client
from app.models.entities import VideoLibraryItem, VideoLibraryProject
from app.schemas.video_library import (
    BrowseFolderResponse,
    LocalVideoFile,
    MoveToProjectRequest,
    UploadLocalFileRequest,
    VideoLibraryItemResponse,
    VideoLibraryProjectCreate,
    VideoLibraryProjectResponse,
)

VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".wmv", ".m4v", ".ts", ".mts", ".mpg", ".mpeg"}
VIDEO_LIBRARY_BUCKET = "reels-video-library"
PRESIGNED_URL_TTL = 3600

# Windows drive letter pattern: C:\, D:/, F:\Folder etc.
_WIN_DRIVE_RE = re.compile(r"^([A-Za-z]):[/\\](.*)", re.DOTALL)


def _resolve_path(raw: str) -> Path:
    """
    Translate a Windows-style path entered by the user into a path that exists
    inside the Docker container.

    Docker mounts host drives at /mnt/<lowercase-letter>  (e.g. F:\ → /mnt/f).
    On non-Docker / native Windows environments the raw path is used as-is.
    """
    m = _WIN_DRIVE_RE.match(raw)
    if m:
        drive = m.group(1).lower()
        rest = m.group(2).replace("\\", "/")
        # Try the mounted path first; fall back to the raw path so the service
        # still works when run natively on Windows.
        container_path = Path(f"/mnt/{drive}/{rest}")
        if container_path.exists():
            return container_path
        # Try /drive/... (some Docker Desktop setups use this)
        alt_path = Path(f"/{drive}/{rest}")
        if alt_path.exists():
            return alt_path
    return Path(raw)


def _project_to_response(p: VideoLibraryProject) -> VideoLibraryProjectResponse:
    return VideoLibraryProjectResponse(
        id=str(p.id),
        workspace_id=str(p.workspace_id),
        name=p.name,
        description=p.description,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


def _item_to_response(item: VideoLibraryItem, url: str) -> VideoLibraryItemResponse:
    return VideoLibraryItemResponse(
        id=str(item.id),
        workspace_id=str(item.workspace_id),
        project_id=str(item.project_id) if item.project_id else None,
        file_name=item.file_name,
        content_type=item.content_type,
        size_bytes=item.size_bytes,
        duration_ms=item.duration_ms,
        width=item.width,
        height=item.height,
        url=url,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


class VideoLibraryService:
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

    def list_projects(self, auth: AuthContext) -> list[VideoLibraryProjectResponse]:
        rows = self.db.scalars(
            select(VideoLibraryProject)
            .where(VideoLibraryProject.workspace_id == uuid.UUID(auth.workspace_id))
            .order_by(VideoLibraryProject.created_at.desc())
        ).all()
        return [_project_to_response(r) for r in rows]

    def create_project(self, auth: AuthContext, payload: VideoLibraryProjectCreate) -> VideoLibraryProjectResponse:
        project = VideoLibraryProject(
            workspace_id=uuid.UUID(auth.workspace_id),
            name=payload.name,
            description=payload.description,
        )
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return _project_to_response(project)

    # ── Browse local folder ───────────────────────────────────────────────────

    def browse_folder(self, folder_path: str) -> BrowseFolderResponse:
        path = _resolve_path(folder_path)
        if not path.exists():
            raise ApiError(400, "invalid_path", f"Path does not exist: {folder_path}")
        if not path.is_dir():
            raise ApiError(400, "invalid_path", f"Path is not a directory: {folder_path}")

        files: list[LocalVideoFile] = []
        for entry in sorted(path.iterdir()):
            if entry.is_file() and entry.suffix.lower() in VIDEO_EXTENSIONS:
                mime, _ = mimetypes.guess_type(entry.name)
                files.append(
                    LocalVideoFile(
                        name=entry.name,
                        path=str(entry.resolve()),
                        size_bytes=entry.stat().st_size,
                        content_type=mime or "video/mp4",
                    )
                )
        return BrowseFolderResponse(path=str(path.resolve()), files=files)

    # ── Upload ────────────────────────────────────────────────────────────────

    def upload_file(self, auth: AuthContext, payload: UploadLocalFileRequest) -> VideoLibraryItemResponse:
        local_path = _resolve_path(payload.local_path)
        if not local_path.exists() or not local_path.is_file():
            raise ApiError(400, "invalid_path", f"File not found: {payload.local_path}")
        if local_path.suffix.lower() not in VIDEO_EXTENSIONS:
            raise ApiError(400, "unsupported_type", f"Not a supported video file: {local_path.suffix}")

        # Validate project ownership if provided
        project_id: uuid.UUID | None = None
        if payload.project_id:
            project = self.db.scalar(
                select(VideoLibraryProject).where(
                    VideoLibraryProject.id == uuid.UUID(payload.project_id),
                    VideoLibraryProject.workspace_id == uuid.UUID(auth.workspace_id),
                )
            )
            if not project:
                raise ApiError(404, "project_not_found", "Video library project not found.")
            project_id = project.id

        mime, _ = mimetypes.guess_type(local_path.name)
        content_type = mime or "video/mp4"
        item_id = uuid.uuid4()
        object_name = f"{auth.workspace_id}/{item_id}/{local_path.name}"

        data = local_path.read_bytes()
        self.storage.ensure_bucket(VIDEO_LIBRARY_BUCKET)
        self.storage.put_bytes(VIDEO_LIBRARY_BUCKET, object_name, data, content_type=content_type)

        item = VideoLibraryItem(
            id=item_id,
            workspace_id=uuid.UUID(auth.workspace_id),
            project_id=project_id,
            file_name=local_path.name,
            bucket_name=VIDEO_LIBRARY_BUCKET,
            object_name=object_name,
            content_type=content_type,
            size_bytes=len(data),
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)

        url = self.storage.presigned_get_url(VIDEO_LIBRARY_BUCKET, object_name, ttl_seconds=PRESIGNED_URL_TTL)
        return _item_to_response(item, url)

    # ── List uploaded ─────────────────────────────────────────────────────────

    def list_uploaded(
        self,
        auth: AuthContext,
        project_id: str | None = None,
    ) -> list[VideoLibraryItemResponse]:
        q = select(VideoLibraryItem).where(
            VideoLibraryItem.workspace_id == uuid.UUID(auth.workspace_id)
        )
        if project_id:
            q = q.where(VideoLibraryItem.project_id == uuid.UUID(project_id))
        q = q.order_by(VideoLibraryItem.created_at.desc())
        rows = self.db.scalars(q).all()

        result = []
        for item in rows:
            url = self.storage.presigned_get_url(item.bucket_name, item.object_name, ttl_seconds=PRESIGNED_URL_TTL)
            result.append(_item_to_response(item, url))
        return result

    # ── Move to project ───────────────────────────────────────────────────────

    def move_to_project(
        self, auth: AuthContext, item_id: str, payload: MoveToProjectRequest
    ) -> VideoLibraryItemResponse:
        item = self.db.scalar(
            select(VideoLibraryItem).where(
                VideoLibraryItem.id == uuid.UUID(item_id),
                VideoLibraryItem.workspace_id == uuid.UUID(auth.workspace_id),
            )
        )
        if not item:
            raise ApiError(404, "item_not_found", "Video library item not found.")

        if payload.project_id:
            project = self.db.scalar(
                select(VideoLibraryProject).where(
                    VideoLibraryProject.id == uuid.UUID(payload.project_id),
                    VideoLibraryProject.workspace_id == uuid.UUID(auth.workspace_id),
                )
            )
            if not project:
                raise ApiError(404, "project_not_found", "Video library project not found.")
            item.project_id = project.id
        else:
            item.project_id = None

        self.db.commit()
        self.db.refresh(item)
        url = self.storage.presigned_get_url(item.bucket_name, item.object_name, ttl_seconds=PRESIGNED_URL_TTL)
        return _item_to_response(item, url)

    # ── Delete ────────────────────────────────────────────────────────────────

    def delete_item(self, auth: AuthContext, item_id: str) -> None:
        item = self.db.scalar(
            select(VideoLibraryItem).where(
                VideoLibraryItem.id == uuid.UUID(item_id),
                VideoLibraryItem.workspace_id == uuid.UUID(auth.workspace_id),
            )
        )
        if not item:
            raise ApiError(404, "item_not_found", "Video library item not found.")
        self.storage.delete_object(item.bucket_name, item.object_name)
        self.db.delete(item)
        self.db.commit()

    # ── Stream local file ─────────────────────────────────────────────────────

    def get_local_file_path(self, file_path: str) -> Path:
        path = _resolve_path(file_path)
        if not path.exists() or not path.is_file():
            raise ApiError(404, "file_not_found", "Local file not found.")
        if path.suffix.lower() not in VIDEO_EXTENSIONS:
            raise ApiError(400, "unsupported_type", "Not a supported video file.")
        return path
