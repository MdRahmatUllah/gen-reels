from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class VideoLibraryProjectCreate(BaseModel):
    name: str
    description: str | None = None


class VideoLibraryProjectResponse(BaseModel):
    id: str
    workspace_id: str
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class LocalVideoFile(BaseModel):
    name: str
    path: str
    size_bytes: int
    content_type: str


class BrowseFolderResponse(BaseModel):
    path: str
    files: list[LocalVideoFile]


class UploadLocalFileRequest(BaseModel):
    local_path: str
    project_id: str | None = None


class VideoLibraryItemResponse(BaseModel):
    id: str
    workspace_id: str
    project_id: str | None
    file_name: str
    content_type: str
    size_bytes: int
    duration_ms: int | None
    width: int | None
    height: int | None
    url: str
    created_at: datetime
    updated_at: datetime


class MoveToProjectRequest(BaseModel):
    project_id: str | None


class LocalFolderProjectCreate(BaseModel):
    name: str
    path: str


class LocalFolderProjectResponse(BaseModel):
    id: str
    workspace_id: str
    name: str
    path: str
    created_at: datetime
