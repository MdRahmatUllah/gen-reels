from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import func, select

from app.api.deps import AuthContext
from app.core.errors import ApiError
from app.models.entities import (
    CreditLedgerEntry,
    CreditLedgerEntryKind,
    ExportRecord,
    ProviderRun,
    ProviderRunStatus,
    Subscription,
    SubscriptionStatus,
    Workspace,
    WorkspaceRole,
)
from app.services.audit_service import record_audit_event


@dataclass(frozen=True)
class ProviderUsageEstimate:
    billable_unit: str
    quantity: int
    credits_delta: int
    amount_cents: int
    currency: str = "USD"
    continuity_mode: str | None = None


class BillingService:
    def __init__(self, db, settings) -> None:
        self.db = db
        self.settings = settings

    def _get_workspace(self, workspace_id: str | UUID) -> Workspace:
        workspace = self.db.get(Workspace, UUID(str(workspace_id)))
        if not workspace:
            raise ApiError(404, "workspace_not_found", "Workspace not found.")
        return workspace

    def _assert_workspace_admin(self, auth: AuthContext) -> None:
        if auth.workspace_role != WorkspaceRole.admin:
            raise ApiError(403, "forbidden", "Only workspace admins can manage billing.")

    def _subscription_period(self, subscription: Subscription | None) -> tuple[datetime, datetime]:
        if subscription and subscription.current_period_start_at and subscription.current_period_end_at:
            return subscription.current_period_start_at, subscription.current_period_end_at

        now = datetime.now(UTC)
        start = datetime(now.year, now.month, 1, tzinfo=UTC)
        if now.month == 12:
            end = datetime(now.year + 1, 1, 1, tzinfo=UTC)
        else:
            end = datetime(now.year, now.month + 1, 1, tzinfo=UTC)
        return start, end

    def _get_subscription(self, workspace_id: UUID) -> Subscription | None:
        return self.db.scalar(select(Subscription).where(Subscription.workspace_id == workspace_id))

    def _subscription_to_dict(self, workspace: Workspace, subscription: Subscription | None) -> dict[str, object]:
        if subscription:
            return {
                "id": subscription.id,
                "workspace_id": workspace.id,
                "provider_name": subscription.provider_name,
                "provider_customer_id": subscription.provider_customer_id,
                "provider_subscription_id": subscription.provider_subscription_id,
                "plan_name": subscription.plan_name,
                "status": subscription.status.value,
                "monthly_credit_allowance": subscription.monthly_credit_allowance,
                "current_period_start_at": subscription.current_period_start_at,
                "current_period_end_at": subscription.current_period_end_at,
                "cancel_at_period_end": subscription.cancel_at_period_end,
                "metadata_payload": subscription.metadata_payload,
                "created_at": subscription.created_at,
                "updated_at": subscription.updated_at,
            }
        period_start, period_end = self._subscription_period(None)
        return {
            "id": None,
            "workspace_id": workspace.id,
            "provider_name": "stub_billing",
            "provider_customer_id": None,
            "provider_subscription_id": None,
            "plan_name": workspace.plan_name,
            "status": SubscriptionStatus.not_configured.value,
            "monthly_credit_allowance": workspace.credits_total,
            "current_period_start_at": period_start,
            "current_period_end_at": period_end,
            "cancel_at_period_end": False,
            "metadata_payload": {},
            "created_at": None,
            "updated_at": None,
        }

    def get_usage(self, auth: AuthContext) -> dict[str, object]:
        workspace = self._get_workspace(auth.workspace_id)
        subscription = self._get_subscription(workspace.id)
        period_start, period_end = self._subscription_period(subscription)
        recent_entries = self.db.scalars(
            select(CreditLedgerEntry)
            .where(CreditLedgerEntry.workspace_id == workspace.id)
            .order_by(CreditLedgerEntry.created_at.desc())
            .limit(50)
        ).all()
        period_entries = self.db.scalars(
            select(CreditLedgerEntry).where(
                CreditLedgerEntry.workspace_id == workspace.id,
                CreditLedgerEntry.created_at >= period_start,
                CreditLedgerEntry.created_at < period_end,
            )
        ).all()
        month_provider_cost_cents = sum(entry.amount_cents for entry in period_entries)
        month_credits_used = sum(-entry.credits_delta for entry in period_entries if entry.credits_delta < 0)
        month_export_count = sum(1 for entry in period_entries if entry.kind == CreditLedgerEntryKind.export_event)
        month_provider_run_count = sum(
            1 for entry in period_entries if entry.kind == CreditLedgerEntryKind.provider_run
        )
        return {
            "workspace_id": workspace.id,
            "plan_name": workspace.plan_name,
            "credits_remaining": workspace.credits_remaining,
            "credits_total": workspace.credits_total,
            "monthly_budget_cents": workspace.monthly_budget_cents,
            "current_period_start_at": period_start,
            "current_period_end_at": period_end,
            "month_provider_cost_cents": month_provider_cost_cents,
            "month_credits_used": month_credits_used,
            "month_export_count": month_export_count,
            "month_provider_run_count": month_provider_run_count,
            "recent_entries": [self.ledger_entry_to_dict(entry) for entry in recent_entries],
        }

    def get_subscription_for_workspace(self, auth: AuthContext) -> dict[str, object]:
        workspace = self._get_workspace(auth.workspace_id)
        subscription = self._get_subscription(workspace.id)
        return self._subscription_to_dict(workspace, subscription)

    def create_checkout_session(self, auth: AuthContext) -> dict[str, object]:
        self._assert_workspace_admin(auth)
        workspace = self._get_workspace(auth.workspace_id)
        subscription = self._get_subscription(workspace.id)
        if not subscription:
            now = datetime.now(UTC)
            subscription = Subscription(
                workspace_id=workspace.id,
                provider_name="stub_billing",
                plan_name=workspace.plan_name,
                status=SubscriptionStatus.checkout_pending,
                monthly_credit_allowance=workspace.credits_total,
                current_period_start_at=now,
                current_period_end_at=now + timedelta(days=30),
                metadata_payload={},
            )
            self.db.add(subscription)
        else:
            subscription.status = SubscriptionStatus.checkout_pending

        subscription.provider_customer_id = subscription.provider_customer_id or f"cust_{workspace.id.hex[:12]}"
        url = (
            f"{self.settings.frontend_base_url}/billing/checkout"
            f"?workspace_id={workspace.id}&session=stub-{uuid4().hex}"
        )
        subscription.metadata_payload = {**subscription.metadata_payload, "last_checkout_url": url}
        record_audit_event(
            self.db,
            workspace_id=workspace.id,
            user_id=UUID(auth.user_id),
            event_type="billing.checkout_requested",
            target_type="workspace",
            target_id=str(workspace.id),
            payload={"url": url},
        )
        self.db.commit()
        return {
            "workspace_id": workspace.id,
            "url": url,
            "provider_name": subscription.provider_name,
            "status": subscription.status.value,
        }

    def create_portal_session(self, auth: AuthContext) -> dict[str, object]:
        self._assert_workspace_admin(auth)
        workspace = self._get_workspace(auth.workspace_id)
        subscription = self._get_subscription(workspace.id)
        provider_name = subscription.provider_name if subscription else "stub_billing"
        status = subscription.status.value if subscription else SubscriptionStatus.not_configured.value
        url = (
            f"{self.settings.frontend_base_url}/billing/portal"
            f"?workspace_id={workspace.id}&session=stub-{uuid4().hex}"
        )
        if subscription:
            subscription.metadata_payload = {**subscription.metadata_payload, "last_portal_url": url}
        record_audit_event(
            self.db,
            workspace_id=workspace.id,
            user_id=UUID(auth.user_id),
            event_type="billing.portal_requested",
            target_type="workspace",
            target_id=str(workspace.id),
            payload={"url": url},
        )
        self.db.commit()
        return {
            "workspace_id": workspace.id,
            "url": url,
            "provider_name": provider_name,
            "status": status,
        }

    def estimate_render_credit_reserve(self, scene_count: int) -> int:
        return max(1, scene_count) * 8 + 2

    def ensure_render_credits_available(self, workspace_id: UUID, scene_count: int) -> None:
        workspace = self._get_workspace(workspace_id)
        estimated_reserve = self.estimate_render_credit_reserve(scene_count)
        if workspace.credits_remaining < estimated_reserve:
            raise ApiError(
                402,
                "insufficient_credits",
                "This workspace does not have enough credits to start the render.",
            )

    def ledger_entry_to_dict(self, entry: CreditLedgerEntry) -> dict[str, object]:
        return {
            "id": entry.id,
            "workspace_id": entry.workspace_id,
            "project_id": entry.project_id,
            "render_job_id": entry.render_job_id,
            "render_step_id": entry.render_step_id,
            "provider_run_id": entry.provider_run_id,
            "export_id": entry.export_id,
            "kind": entry.kind.value,
            "billable_unit": entry.billable_unit,
            "quantity": entry.quantity,
            "credits_delta": entry.credits_delta,
            "amount_cents": entry.amount_cents,
            "currency": entry.currency,
            "balance_after": entry.balance_after,
            "idempotency_key": entry.idempotency_key,
            "metadata_payload": entry.metadata_payload,
            "created_at": entry.created_at,
        }

    def _estimate_provider_usage(self, provider_run: ProviderRun) -> ProviderUsageEstimate:
        request_payload = dict(provider_run.request_payload or {})
        operation = provider_run.operation
        if operation == "idea_generation":
            return ProviderUsageEstimate("planning_idea_job", 1, -1, 15)
        if operation == "script_generation":
            return ProviderUsageEstimate("planning_script_job", 1, -2, 25)
        if operation == "scene_plan_generation":
            return ProviderUsageEstimate("scene_plan_job", 1, -2, 30)
        if operation == "prompt_pair_generation":
            quantity = len((((request_payload.get("scene_plan") or {}) if isinstance(request_payload.get("scene_plan"), dict) else {}).get("segments") or []))
            quantity = max(1, quantity)
            return ProviderUsageEstimate("prompt_pair_scene", quantity, -quantity, quantity * 4)
        if operation == "frame_pair_generation":
            quantity = 2
            continuity_mode = "reference_chain" if request_payload.get("previous_end_asset_id") else "seed_frame"
            return ProviderUsageEstimate("frame_pair_image", quantity, -(quantity), quantity * 6, continuity_mode=continuity_mode)
        if operation == "video_generation":
            return ProviderUsageEstimate("video_scene", 1, -5, 60)
        if operation == "narration_generation":
            return ProviderUsageEstimate("narration_scene", 1, -1, 5)
        if operation == "music_preparation":
            return ProviderUsageEstimate("music_track", 1, -2, 8)
        return ProviderUsageEstimate(operation or "provider_run", 1, 0, 0)

    def capture_provider_run_usage(self, provider_run: ProviderRun) -> CreditLedgerEntry | None:
        if provider_run.status != ProviderRunStatus.completed:
            return None

        provider_run.external_request_id = provider_run.external_request_id or f"local-{provider_run.id}"
        estimate = self._estimate_provider_usage(provider_run)
        provider_run.normalized_cost_cents = estimate.amount_cents
        provider_run.currency = estimate.currency
        provider_run.billable_quantity = estimate.quantity
        provider_run.continuity_mode = estimate.continuity_mode
        if provider_run.cost_payload is None:
            provider_run.cost_payload = {}
        provider_run.cost_payload = {
            **provider_run.cost_payload,
            "billable_unit": estimate.billable_unit,
            "quantity": estimate.quantity,
            "credits_delta": estimate.credits_delta,
            "amount_cents": estimate.amount_cents,
            "currency": estimate.currency,
        }

        idempotency_key = f"provider-run:{provider_run.id}"
        existing = self.db.scalar(
            select(CreditLedgerEntry).where(CreditLedgerEntry.idempotency_key == idempotency_key)
        )
        if existing:
            return existing

        workspace = self._get_workspace(provider_run.workspace_id)
        balance_after = workspace.credits_remaining + estimate.credits_delta
        workspace.credits_remaining = balance_after
        entry = CreditLedgerEntry(
            workspace_id=workspace.id,
            project_id=provider_run.project_id,
            render_job_id=provider_run.render_job_id,
            render_step_id=provider_run.render_step_id,
            provider_run_id=provider_run.id,
            kind=CreditLedgerEntryKind.provider_run,
            billable_unit=estimate.billable_unit,
            quantity=estimate.quantity,
            credits_delta=estimate.credits_delta,
            amount_cents=estimate.amount_cents,
            currency=estimate.currency,
            balance_after=balance_after,
            idempotency_key=idempotency_key,
            metadata_payload={
                "provider_name": provider_run.provider_name,
                "provider_model": provider_run.provider_model,
                "operation": provider_run.operation,
                "continuity_mode": estimate.continuity_mode,
            },
        )
        self.db.add(entry)
        return entry

    def capture_export_usage(self, export_record: ExportRecord) -> CreditLedgerEntry | None:
        idempotency_key = f"export:{export_record.id}"
        existing = self.db.scalar(
            select(CreditLedgerEntry).where(CreditLedgerEntry.idempotency_key == idempotency_key)
        )
        if existing:
            return existing

        workspace = self._get_workspace(export_record.workspace_id)
        entry = CreditLedgerEntry(
            workspace_id=workspace.id,
            project_id=export_record.project_id,
            render_job_id=export_record.render_job_id,
            export_id=export_record.id,
            kind=CreditLedgerEntryKind.export_event,
            billable_unit="export_completed",
            quantity=1,
            credits_delta=0,
            amount_cents=0,
            currency="USD",
            balance_after=workspace.credits_remaining,
            idempotency_key=idempotency_key,
            metadata_payload={"format": export_record.format, "status": export_record.status},
        )
        self.db.add(entry)
        return entry

    def reconcile_usage_entries(self) -> int:
        created = 0
        provider_runs = self.db.scalars(
            select(ProviderRun).where(ProviderRun.status == ProviderRunStatus.completed)
        ).all()
        for provider_run in provider_runs:
            if self.capture_provider_run_usage(provider_run):
                created += 1

        exports = self.db.scalars(select(ExportRecord).where(ExportRecord.status == "completed")).all()
        for export_record in exports:
            if self.capture_export_usage(export_record):
                created += 1

        self.db.commit()
        return created

