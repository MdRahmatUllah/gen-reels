from __future__ import annotations

import mimetypes
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_db_dep, get_settings_dep, require_auth
from app.schemas.video_library import (
    BrowseFolderResponse,
    LocalFolderProjectCreate,
    LocalFolderProjectResponse,
    MoveToProjectRequest,
    UploadLocalFileRequest,
    VideoLibraryItemResponse,
    VideoLibraryProjectCreate,
    VideoLibraryProjectResponse,
)
from app.services.video_library_service import VideoLibraryService

router = APIRouter()


# ── Local Folder Projects ─────────────────────────────────────────────────────

@router.get("/local-folders", response_model=list[LocalFolderProjectResponse])
def list_local_folders(
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return VideoLibraryService(db, settings).list_local_folder_projects(auth)


@router.post("/local-folders", response_model=LocalFolderProjectResponse, status_code=201)
def create_local_folder(
    payload: LocalFolderProjectCreate,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return VideoLibraryService(db, settings).create_local_folder_project(auth, payload)


@router.delete("/local-folders/{project_id}", status_code=204)
def delete_local_folder(
    project_id: str,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    VideoLibraryService(db, settings).delete_local_folder_project(auth, project_id)


# ── Upload Projects ───────────────────────────────────────────────────────────

@router.get("/projects", response_model=list[VideoLibraryProjectResponse])
def list_projects(
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return VideoLibraryService(db, settings).list_projects(auth)


@router.post("/projects", response_model=VideoLibraryProjectResponse, status_code=201)
def create_project(
    payload: VideoLibraryProjectCreate,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return VideoLibraryService(db, settings).create_project(auth, payload)


@router.delete("/projects/{project_id}", status_code=204)
def delete_project(
    project_id: str,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    VideoLibraryService(db, settings).delete_project(auth, project_id)


@router.get("/browse", response_model=BrowseFolderResponse)
def browse_folder(
    path: str = Query(..., description="Absolute folder path on the server"),
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return VideoLibraryService(db, settings).browse_folder(path)


@router.post("/upload", response_model=VideoLibraryItemResponse, status_code=201)
def upload_file(
    payload: UploadLocalFileRequest,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return VideoLibraryService(db, settings).upload_file(auth, payload)


@router.get("/uploaded", response_model=list[VideoLibraryItemResponse])
def list_uploaded(
    project_id: str | None = Query(default=None),
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return VideoLibraryService(db, settings).list_uploaded(auth, project_id=project_id)


@router.patch("/uploaded/{item_id}/project", response_model=VideoLibraryItemResponse)
def move_to_project(
    item_id: str,
    payload: MoveToProjectRequest,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return VideoLibraryService(db, settings).move_to_project(auth, item_id, payload)


@router.delete("/uploaded/{item_id}", status_code=204)
def delete_item(
    item_id: str,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    VideoLibraryService(db, settings).delete_item(auth, item_id)


@router.get("/stream")
def stream_local_file(
    path: str = Query(..., description="Absolute file path on the server"),
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    local_path = VideoLibraryService(db, settings).get_local_file_path(path)
    mime, _ = mimetypes.guess_type(local_path.name)
    return FileResponse(
        path=str(local_path),
        media_type=mime or "video/mp4",
        filename=local_path.name,
    )
