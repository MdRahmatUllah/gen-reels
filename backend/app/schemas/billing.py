from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class CreditLedgerEntryResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    project_id: UUID | None
    render_job_id: UUID | None
    render_step_id: UUID | None
    provider_run_id: UUID | None
    export_id: UUID | None
    kind: str
    billable_unit: str
    quantity: int
    credits_delta: int
    amount_cents: int
    currency: str
    balance_after: int
    idempotency_key: str
    metadata_payload: dict[str, object]
    created_at: datetime


class SubscriptionResponse(BaseModel):
    id: UUID | None = None
    workspace_id: UUID
    provider_name: str
    provider_customer_id: str | None = None
    provider_subscription_id: str | None = None
    plan_name: str
    status: str
    monthly_credit_allowance: int
    current_period_start_at: datetime | None = None
    current_period_end_at: datetime | None = None
    cancel_at_period_end: bool
    metadata_payload: dict[str, object]
    created_at: datetime | None = None
    updated_at: datetime | None = None


class UsageSummaryResponse(BaseModel):
    workspace_id: UUID
    plan_name: str
    credits_remaining: int
    credits_total: int
    monthly_budget_cents: int
    current_period_start_at: datetime | None = None
    current_period_end_at: datetime | None = None
    month_provider_cost_cents: int
    month_credits_used: int
    month_export_count: int
    month_provider_run_count: int
    month_execution_mode_summary: dict[str, dict[str, int]]
    recent_entries: list[CreditLedgerEntryResponse]


class BillingUrlResponse(BaseModel):
    workspace_id: UUID
    url: str
    provider_name: str
    status: str
