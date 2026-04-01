from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select

from app.api.deps import AuthContext
from app.core.errors import ApiError
from app.models.entities import ReviewRequest, ReviewStatus, ReviewTargetType, WorkspaceMember
from app.schemas.reviews import ReviewCreateRequest
from app.services.audit_service import record_audit_event
from app.services.collaboration_targets import resolve_workspace_target
from app.services.content_planning_service import ContentPlanningService
from app.services.notification_service import NotificationService
from app.services.permissions import require_workspace_review
from app.services.presenters import review_request_to_dict
from app.services.workspace_service import WorkspaceService


class ReviewService:
    def __init__(self, db, settings) -> None:
        self.db = db
        self.settings = settings

    def list_reviews(
        self,
        auth: AuthContext,
        *,
        project_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, object]]:
        query = select(ReviewRequest).where(ReviewRequest.workspace_id == UUID(auth.workspace_id))
        if project_id:
            query = query.where(ReviewRequest.project_id == UUID(project_id))
        if status:
            try:
                review_status = ReviewStatus(status)
            except ValueError as exc:
                raise ApiError(400, "invalid_review_status", "Unsupported review status.") from exc
            query = query.where(ReviewRequest.status == review_status)
        reviews = self.db.scalars(query.order_by(ReviewRequest.created_at.desc())).all()
        return [review_request_to_dict(review) for review in reviews]

    def create_review(self, auth: AuthContext, payload: ReviewCreateRequest) -> dict[str, object]:
        require_workspace_review(auth, message="Only reviewers, members, or admins can create reviews.")
        target = resolve_workspace_target(self.db, auth.workspace_id, payload.target_type, payload.target_id)
        if payload.project_id is not None and target.project_id is not None and payload.project_id != str(target.project_id):
            raise ApiError(
                400,
                "review_project_mismatch",
                "The review target does not belong to the supplied project.",
            )
        assigned_to_user_id = UUID(payload.assigned_to_user_id) if payload.assigned_to_user_id else None
        if assigned_to_user_id:
            membership = self.db.scalar(
                select(WorkspaceMember).where(
                    WorkspaceMember.workspace_id == UUID(auth.workspace_id),
                    WorkspaceMember.user_id == assigned_to_user_id,
                )
            )
            if not membership:
                raise ApiError(404, "review_assignee_not_found", "Review assignee is not a workspace member.")

        review = ReviewRequest(
            workspace_id=UUID(auth.workspace_id),
            project_id=target.project_id if payload.project_id is None else UUID(payload.project_id),
            target_type=ReviewTargetType(payload.target_type),
            target_id=payload.target_id,
            requested_by_user_id=UUID(auth.user_id),
            assigned_to_user_id=assigned_to_user_id,
            requested_version=payload.requested_version or target.version,
            request_notes=payload.request_notes,
        )
        self.db.add(review)
        self.db.flush()
        record_audit_event(
            self.db,
            workspace_id=review.workspace_id,
            user_id=UUID(auth.user_id),
            event_type="reviews.created",
            target_type="review_request",
            target_id=str(review.id),
            payload={
                "target_type": review.target_type.value,
                "target_id": review.target_id,
                "requested_version": review.requested_version,
            },
        )
        WorkspaceService(self.db, self.settings).emit_workspace_event(
            review.workspace_id,
            "reviews.created",
            {
                "review_id": str(review.id),
                "target_type": review.target_type.value,
                "target_id": review.target_id,
            },
        )
        NotificationService(self.db, self.settings).notify_review_requested(review)
        self.db.commit()
        self.db.refresh(review)
        return review_request_to_dict(review)

    def approve_review(
        self,
        auth: AuthContext,
        review_id: str,
        *,
        decision_notes: str,
    ) -> dict[str, object]:
        require_workspace_review(auth, message="Only reviewers, members, or admins can approve reviews.")
        review = self.db.scalar(
            select(ReviewRequest).where(
                ReviewRequest.id == UUID(review_id),
                ReviewRequest.workspace_id == UUID(auth.workspace_id),
            )
        )
        if not review:
            raise ApiError(404, "review_not_found", "Review not found.")
        if review.status != ReviewStatus.pending:
            raise ApiError(400, "review_not_pending", "Only pending reviews can be approved.")

        target = resolve_workspace_target(self.db, auth.workspace_id, review.target_type.value, review.target_id)
        if review.requested_version is not None and target.version is not None and review.requested_version != target.version:
            raise ApiError(
                409,
                "review_conflict",
                "The review target changed after the review was requested.",
                details={"current": target.payload},
            )

        if review.target_type == ReviewTargetType.script_version:
            ContentPlanningService(self.db, self.settings).approve_script(
                auth,
                str(target.project_id),
                review.target_id,
            )
        elif review.target_type == ReviewTargetType.scene_plan:
            ContentPlanningService(self.db, self.settings).approve_scene_plan(
                auth,
                str(target.project_id),
                review.target_id,
            )

        review.status = ReviewStatus.approved
        review.decision_notes = decision_notes
        review.decided_by_user_id = UUID(auth.user_id)
        review.decided_at = review.decided_at or datetime.now(timezone.utc)
        record_audit_event(
            self.db,
            workspace_id=review.workspace_id,
            user_id=UUID(auth.user_id),
            event_type="reviews.approved",
            target_type="review_request",
            target_id=str(review.id),
            payload={"target_type": review.target_type.value, "target_id": review.target_id},
        )
        WorkspaceService(self.db, self.settings).emit_workspace_event(
            review.workspace_id,
            "reviews.approved",
            {"review_id": str(review.id), "target_type": review.target_type.value, "target_id": review.target_id},
        )
        self.db.commit()
        self.db.refresh(review)
        return review_request_to_dict(review)

    def reject_review(
        self,
        auth: AuthContext,
        review_id: str,
        *,
        decision_notes: str,
    ) -> dict[str, object]:
        require_workspace_review(auth, message="Only reviewers, members, or admins can reject reviews.")
        review = self.db.scalar(
            select(ReviewRequest).where(
                ReviewRequest.id == UUID(review_id),
                ReviewRequest.workspace_id == UUID(auth.workspace_id),
            )
        )
        if not review:
            raise ApiError(404, "review_not_found", "Review not found.")
        if review.status != ReviewStatus.pending:
            raise ApiError(400, "review_not_pending", "Only pending reviews can be rejected.")

        review.status = ReviewStatus.rejected
        review.decision_notes = decision_notes
        review.decided_by_user_id = UUID(auth.user_id)
        review.decided_at = review.decided_at or datetime.now(timezone.utc)
        record_audit_event(
            self.db,
            workspace_id=review.workspace_id,
            user_id=UUID(auth.user_id),
            event_type="reviews.rejected",
            target_type="review_request",
            target_id=str(review.id),
            payload={"target_type": review.target_type.value, "target_id": review.target_id},
        )
        WorkspaceService(self.db, self.settings).emit_workspace_event(
            review.workspace_id,
            "reviews.rejected",
            {"review_id": str(review.id), "target_type": review.target_type.value, "target_id": review.target_id},
        )
        self.db.commit()
        self.db.refresh(review)
        return review_request_to_dict(review)
