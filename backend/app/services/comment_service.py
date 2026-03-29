from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select

from app.api.deps import AuthContext
from app.core.errors import ApiError
from app.models.entities import Comment, User
from app.schemas.comments import CommentCreateRequest, CommentResolveRequest
from app.services.audit_service import record_audit_event
from app.services.collaboration_targets import resolve_workspace_target
from app.services.permissions import require_workspace_review
from app.services.presenters import comment_to_dict
from app.services.workspace_service import WorkspaceService


class CommentService:
    def __init__(self, db) -> None:
        self.db = db

    def _serialize_comments(self, comments: list[Comment]) -> list[dict[str, object]]:
        user_ids = {
            user_id
            for comment in comments
            for user_id in (comment.author_user_id, comment.resolved_by_user_id)
            if user_id is not None
        }
        users_by_id = {}
        if user_ids:
            users_by_id = {
                user.id: user.full_name
                for user in self.db.scalars(select(User).where(User.id.in_(user_ids))).all()
            }
        payloads: list[dict[str, object]] = []
        for comment in comments:
            payload = comment_to_dict(comment)
            payload["author_name"] = users_by_id.get(comment.author_user_id)
            payload["resolved_by_name"] = (
                users_by_id.get(comment.resolved_by_user_id) if comment.resolved_by_user_id else None
            )
            payloads.append(payload)
        return payloads

    def list_comments(
        self,
        auth: AuthContext,
        *,
        project_id: str | None = None,
        target_type: str | None = None,
        target_id: str | None = None,
    ) -> list[dict[str, object]]:
        query = select(Comment).where(Comment.workspace_id == UUID(auth.workspace_id))
        if project_id:
            query = query.where(Comment.project_id == UUID(project_id))
        if target_type:
            query = query.where(Comment.target_type == target_type)
        if target_id:
            query = query.where(Comment.target_id == target_id)
        comments = self.db.scalars(query.order_by(Comment.created_at.asc())).all()
        return self._serialize_comments(comments)

    def create_comment(self, auth: AuthContext, payload: CommentCreateRequest) -> dict[str, object]:
        require_workspace_review(auth, message="Only reviewers, members, or admins can comment.")
        target = resolve_workspace_target(self.db, auth.workspace_id, payload.target_type, payload.target_id)
        if payload.project_id is not None and target.project_id is not None and payload.project_id != str(target.project_id):
            raise ApiError(
                400,
                "comment_project_mismatch",
                "The comment target does not belong to the supplied project.",
            )
        comment = Comment(
            workspace_id=UUID(auth.workspace_id),
            project_id=target.project_id if payload.project_id is None else UUID(payload.project_id),
            target_type=payload.target_type,
            target_id=payload.target_id,
            author_user_id=UUID(auth.user_id),
            body=payload.body,
            metadata_payload=payload.metadata_payload,
        )
        self.db.add(comment)
        self.db.flush()
        record_audit_event(
            self.db,
            workspace_id=comment.workspace_id,
            user_id=UUID(auth.user_id),
            event_type="comments.created",
            target_type="comment",
            target_id=str(comment.id),
            payload={"target_type": comment.target_type, "target_id": comment.target_id},
        )
        WorkspaceService(self.db).emit_workspace_event(
            comment.workspace_id,
            "comments.created",
            {
                "comment_id": str(comment.id),
                "target_type": comment.target_type,
                "target_id": comment.target_id,
            },
        )
        self.db.commit()
        self.db.refresh(comment)
        return self._serialize_comments([comment])[0]

    def resolve_comment(
        self,
        auth: AuthContext,
        comment_id: str,
        payload: CommentResolveRequest | None = None,
    ) -> dict[str, object]:
        require_workspace_review(auth, message="Only reviewers, members, or admins can resolve comments.")
        comment = self.db.scalar(
            select(Comment).where(
                Comment.id == UUID(comment_id),
                Comment.workspace_id == UUID(auth.workspace_id),
            )
        )
        if not comment:
            raise ApiError(404, "comment_not_found", "Comment not found.")
        comment.resolved_at = comment.resolved_at or datetime.now(UTC)
        comment.resolved_by_user_id = UUID(auth.user_id)
        record_audit_event(
            self.db,
            workspace_id=comment.workspace_id,
            user_id=UUID(auth.user_id),
            event_type="comments.resolved",
            target_type="comment",
            target_id=str(comment.id),
            payload={
                "target_type": comment.target_type,
                "target_id": comment.target_id,
                "note": payload.note if payload else None,
            },
        )
        WorkspaceService(self.db).emit_workspace_event(
            comment.workspace_id,
            "comments.resolved",
            {"comment_id": str(comment.id)},
        )
        self.db.commit()
        self.db.refresh(comment)
        return self._serialize_comments([comment])[0]
