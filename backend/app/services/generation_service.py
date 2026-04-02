from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select, true, update
from sqlalchemy.orm import Session

from app.api.deps import AuthContext
from app.core.config import Settings
from app.core.errors import AdapterError, ApiError
from app.integrations.azure import ModerationProvider, TextProvider
from app.models.entities import (
    IdeaCandidate,
    IdeaCandidateStatus,
    ExecutionMode,
    IdeaSet,
    JobKind,
    JobStatus,
    Project,
    ProjectBrief,
    ProjectStage,
    ProviderErrorCategory,
    ProviderRun,
    ProviderRunStatus,
    RenderJob,
    RenderStep,
    ScriptSource,
    ScriptVersion,
    StepKind,
)
from app.schemas.scripts import ScriptPatchRequest
from app.services.audit_service import record_audit_event
from app.services.billing_service import BillingService
from app.services.brand_kit_service import BrandKitService
from app.services.moderation_service import moderate_text_or_raise
from app.services.permissions import require_workspace_edit
from app.services.presenters import (
    idea_set_to_dict,
    job_to_dict,
    script_version_to_dict,
)
from app.services.routing_service import RoutingService


class GenerationService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    def _get_project(self, project_id: str, workspace_id: str, *, include_internal: bool = False) -> Project:
        project = self.db.scalar(
            select(Project).where(
                Project.id == UUID(project_id),
                Project.workspace_id == UUID(workspace_id),
                Project.deleted_at.is_(None),
                (true() if include_internal else Project.is_internal.is_(False)),
            )
        )
        if not project:
            raise ApiError(404, "project_not_found", "Project not found.")
        return project

    def _assert_mutation_rights(self, project: Project, auth: AuthContext) -> None:
        require_workspace_edit(
            auth,
            message="Only workspace members or admins can perform this action.",
        )

    def _hash_request(self, payload: dict[str, object]) -> str:
        encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _set_step_checkpoint(self, step: RenderStep, payload: dict[str, object] | None = None) -> None:
        step.checkpoint_payload = payload or {}
        step.last_checkpoint_at = datetime.now(timezone.utc)

    def _record_step_retry(
        self,
        step: RenderStep,
        *,
        requested_by_user_id: str | UUID | None,
        reason: str,
        recovery_source_step_id: UUID | None = None,
    ) -> None:
        history = list(step.retry_history or [])
        history.append(
            {
                "requested_by_user_id": str(requested_by_user_id) if requested_by_user_id else None,
                "reason": reason,
                "at": datetime.now(timezone.utc).isoformat(),
                "recovery_source_step_id": str(recovery_source_step_id) if recovery_source_step_id else None,
            }
        )
        step.retry_history = history
        step.retry_count += 1
        step.recovery_source_step_id = recovery_source_step_id

    def _finalize_provider_run(
        self,
        provider_run: ProviderRun,
        *,
        started_at: float,
        response_payload: dict[str, object] | None = None,
        error: AdapterError | None = None,
    ) -> None:
        provider_run.latency_ms = round((time.perf_counter() - started_at) * 1000)
        provider_run.completed_at = datetime.now(timezone.utc)
        if error:
            provider_run.status = ProviderRunStatus.failed
            provider_run.error_category = ProviderErrorCategory(error.category)
            provider_run.error_code = error.code
            provider_run.error_message = error.message
            return

        provider_run.status = ProviderRunStatus.completed
        provider_run.response_payload = response_payload
        BillingService(self.db, self.settings).capture_provider_run_usage(provider_run)

    @staticmethod
    def _provider_run_payload(decision) -> dict[str, object]:
        return decision.to_payload() if decision else {}

    @staticmethod
    def _provider_execution_mode(decision):
        return decision.execution_mode if decision else ExecutionMode.hosted

    def _brief_payload(self, brief: ProjectBrief) -> dict[str, object]:
        return {
            "objective": brief.objective,
            "hook": brief.hook,
            "target_audience": brief.target_audience,
            "call_to_action": brief.call_to_action,
            "brand_north_star": brief.brand_north_star,
            "guardrails": brief.guardrails,
            "must_include": brief.must_include,
            "approval_steps": brief.approval_steps,
        }

    def _idea_payload(self, candidate: IdeaCandidate) -> dict[str, object]:
        return {
            "id": str(candidate.id),
            "title": candidate.title,
            "hook": candidate.hook,
            "summary": candidate.summary,
            "tags": candidate.tags,
        }

    def _get_idempotent_job(
        self,
        *,
        project_id,
        user_id,
        job_kind: JobKind,
        idempotency_key: str,
        request_hash: str,
    ) -> RenderJob | None:
        window_start = datetime.now(timezone.utc) - timedelta(hours=self.settings.idempotency_retention_hours)
        existing = self.db.scalar(
            select(RenderJob).where(
                RenderJob.project_id == project_id,
                RenderJob.created_by_user_id == user_id,
                RenderJob.job_kind == job_kind,
                RenderJob.idempotency_key == idempotency_key,
                RenderJob.created_at >= window_start,
            )
        )
        if existing:
            if existing.request_hash != request_hash:
                raise ApiError(
                    409,
                    "idempotency_conflict",
                    "This Idempotency-Key was already used for a different request.",
                )
            return existing
        return None

    def list_ideas(self, auth: AuthContext, project_id: str) -> list[dict[str, object]]:
        project = self._get_project(project_id, auth.workspace_id)
        idea_sets = self.db.scalars(
            select(IdeaSet).where(IdeaSet.project_id == project.id).order_by(IdeaSet.created_at.desc())
        ).all()
        response: list[dict[str, object]] = []
        for idea_set in idea_sets:
            candidates = self.db.scalars(
                select(IdeaCandidate)
                .where(IdeaCandidate.idea_set_id == idea_set.id)
                .order_by(IdeaCandidate.order_index.asc())
            ).all()
            response.append(idea_set_to_dict(idea_set, candidates))
        return response

    def queue_idea_generation(
        self,
        auth: AuthContext,
        project_id: str,
        *,
        idempotency_key: str,
        moderation_provider: ModerationProvider,
    ) -> dict[str, object]:
        if not idempotency_key:
            raise ApiError(400, "missing_idempotency_key", "Idempotency-Key header is required.")
        project = self._get_project(project_id, auth.workspace_id)
        self._assert_mutation_rights(project, auth)
        if not project.active_brief_id:
            raise ApiError(400, "missing_brief", "A saved brief is required before idea generation.")

        brief = self.db.get(ProjectBrief, project.active_brief_id)
        assert brief is not None
        brief_payload = self._brief_payload(brief)
        moderate_text_or_raise(
            self.db,
            provider=moderation_provider,
            text=json.dumps(brief_payload, default=str),
            target_type="idea_generation_input",
            user_id=UUID(auth.user_id),
            project_id=project.id,
            workspace_id=project.workspace_id,
            target_id=project_id,
        )
        request_payload = {"project_id": project_id, "brief_id": str(brief.id), "brief_version": brief.version_number}
        request_hash = self._hash_request(request_payload)
        existing = self._get_idempotent_job(
            project_id=project.id,
            user_id=UUID(auth.user_id),
            job_kind=JobKind.idea_generation,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
        if existing:
            return {"job_id": existing.id, "job_status": existing.status.value, "project_id": project.id}

        job = RenderJob(
            workspace_id=project.workspace_id,
            project_id=project.id,
            created_by_user_id=UUID(auth.user_id),
            job_kind=JobKind.idea_generation,
            status=JobStatus.queued,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            payload=request_payload,
        )
        self.db.add(job)
        self.db.flush()
        self.db.add(
            RenderStep(
                render_job_id=job.id,
                project_id=project.id,
                step_kind=StepKind.idea_generation,
                status=JobStatus.queued,
                input_payload=request_payload,
            )
        )
        record_audit_event(
            self.db,
            workspace_id=project.workspace_id,
            user_id=UUID(auth.user_id),
            event_type="ideas.generation_queued",
            target_type="render_job",
            target_id=str(job.id),
            payload=request_payload,
        )
        self.db.commit()
        from app.workers.tasks import generate_ideas_task

        generate_ideas_task.delay(str(job.id))
        return {"job_id": job.id, "job_status": job.status.value, "project_id": project.id}

    def select_idea(self, auth: AuthContext, project_id: str, idea_id: str) -> dict[str, object]:
        project = self._get_project(project_id, auth.workspace_id)
        self._assert_mutation_rights(project, auth)
        candidate = self.db.scalar(
            select(IdeaCandidate).where(
                IdeaCandidate.id == UUID(idea_id),
                IdeaCandidate.project_id == project.id,
            )
        )
        if not candidate:
            raise ApiError(404, "idea_not_found", "Idea not found.")

        self.db.execute(
            update(IdeaCandidate)
            .where(IdeaCandidate.project_id == project.id, IdeaCandidate.status == IdeaCandidateStatus.selected)
            .values(status=IdeaCandidateStatus.generated)
        )
        candidate.status = IdeaCandidateStatus.selected
        project.selected_idea_id = candidate.id
        project.stage = ProjectStage.script
        record_audit_event(
            self.db,
            workspace_id=project.workspace_id,
            user_id=UUID(auth.user_id),
            event_type="ideas.selected",
            target_type="idea_candidate",
            target_id=str(candidate.id),
            payload={},
        )
        self.db.commit()
        return {"idea_id": candidate.id, "project_id": project.id, "status": candidate.status.value}

    def list_scripts(self, auth: AuthContext, project_id: str) -> list[dict[str, object]]:
        project = self._get_project(project_id, auth.workspace_id)
        scripts = self.db.scalars(
            select(ScriptVersion)
            .where(ScriptVersion.project_id == project.id)
            .order_by(ScriptVersion.version_number.desc())
        ).all()
        return [script_version_to_dict(script) for script in scripts]

    def queue_script_generation(
        self,
        auth: AuthContext,
        project_id: str,
        *,
        idempotency_key: str,
        moderation_provider: ModerationProvider,
    ) -> dict[str, object]:
        if not idempotency_key:
            raise ApiError(400, "missing_idempotency_key", "Idempotency-Key header is required.")
        project = self._get_project(project_id, auth.workspace_id)
        self._assert_mutation_rights(project, auth)
        if not project.active_brief_id:
            raise ApiError(400, "missing_brief", "A saved brief is required before script generation.")
        if not project.selected_idea_id:
            raise ApiError(400, "missing_selected_idea", "Select one idea before generating a script.")

        brief = self.db.get(ProjectBrief, project.active_brief_id)
        idea = self.db.get(IdeaCandidate, project.selected_idea_id)
        assert brief is not None and idea is not None
        moderate_text_or_raise(
            self.db,
            provider=moderation_provider,
            text=json.dumps({"brief": self._brief_payload(brief), "idea": self._idea_payload(idea)}, default=str),
            target_type="script_generation_input",
            user_id=UUID(auth.user_id),
            project_id=project.id,
            workspace_id=project.workspace_id,
            target_id=project_id,
        )

        request_payload = {
            "project_id": project_id,
            "brief_id": str(brief.id),
            "brief_version": brief.version_number,
            "selected_idea_id": str(idea.id),
        }
        request_hash = self._hash_request(request_payload)
        existing = self._get_idempotent_job(
            project_id=project.id,
            user_id=UUID(auth.user_id),
            job_kind=JobKind.script_generation,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
        if existing:
            return {"job_id": existing.id, "job_status": existing.status.value, "project_id": project.id}

        job = RenderJob(
            workspace_id=project.workspace_id,
            project_id=project.id,
            created_by_user_id=UUID(auth.user_id),
            job_kind=JobKind.script_generation,
            status=JobStatus.queued,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            payload=request_payload,
        )
        self.db.add(job)
        self.db.flush()
        self.db.add(
            RenderStep(
                render_job_id=job.id,
                project_id=project.id,
                step_kind=StepKind.script_generation,
                status=JobStatus.queued,
                input_payload=request_payload,
            )
        )
        record_audit_event(
            self.db,
            workspace_id=project.workspace_id,
            user_id=UUID(auth.user_id),
            event_type="scripts.generation_queued",
            target_type="render_job",
            target_id=str(job.id),
            payload=request_payload,
        )
        self.db.commit()
        from app.workers.tasks import generate_script_task

        generate_script_task.delay(str(job.id))
        return {"job_id": job.id, "job_status": job.status.value, "project_id": project.id}

    def patch_script(self, auth: AuthContext, project_id: str, script_version_id: str, payload: ScriptPatchRequest):
        project = self._get_project(project_id, auth.workspace_id)
        self._assert_mutation_rights(project, auth)
        parent = self.db.scalar(
            select(ScriptVersion).where(
                ScriptVersion.id == UUID(script_version_id),
                ScriptVersion.project_id == project.id,
            )
        )
        if not parent:
            raise ApiError(404, "script_not_found", "Script version not found.")
        if payload.version is not None and payload.version != parent.version:
            raise ApiError(
                409,
                "script_version_conflict",
                "This script changed since you last loaded it.",
                details={
                    "expected_version": payload.version,
                    "current_version": parent.version,
                    "current": script_version_to_dict(parent),
                },
            )
        if payload.approval_state == "approved":
            raise ApiError(
                400,
                "script_approval_requires_explicit_action",
                "Use the dedicated script approval endpoint to approve a script version.",
            )

        next_version = (
            self.db.scalar(
                select(func.max(ScriptVersion.version_number)).where(ScriptVersion.project_id == project.id)
            )
            or 0
        ) + 1
        lines = [line.model_dump() for line in payload.lines]
        script_text = "\n".join(
            f"{line.get('beat', '')}\n{line.get('narration', '')}\n{line.get('caption', '')}" for line in lines
        )
        BrandKitService(self.db).validate_text_against_brand_kit(project, script_text)
        total_words = sum(len(str(line["narration"]).split()) for line in lines)
        estimated_duration = sum(int(line["duration_sec"]) for line in lines)
        script = ScriptVersion(
            project_id=project.id,
            based_on_idea_id=project.selected_idea_id,
            created_by_user_id=UUID(auth.user_id),
            parent_version_id=parent.id,
            version_number=next_version,
            version=1,
            source_type=ScriptSource.manual,
            approval_state="draft",
            total_words=total_words,
            estimated_duration_seconds=estimated_duration,
            reading_time_label=f"{estimated_duration}s draft narration",
            lines=lines,
        )
        self.db.add(script)
        self.db.flush()
        project.active_script_version_id = script.id
        project.active_scene_plan_id = None
        project.stage = ProjectStage.script
        record_audit_event(
            self.db,
            workspace_id=project.workspace_id,
            user_id=UUID(auth.user_id),
            event_type="scripts.version_created",
            target_type="script_version",
            target_id=str(script.id),
            payload={"source": "manual", "parent_version_id": str(parent.id)},
        )
        self.db.commit()
        return script_version_to_dict(script)

    def _get_job_and_step(self, job_id: str, step_kind: StepKind) -> tuple[RenderJob, RenderStep]:
        job = self.db.get(RenderJob, UUID(job_id))
        if not job:
            raise ApiError(404, "job_not_found", "Job not found.")
        step = self.db.scalar(
            select(RenderStep).where(
                RenderStep.render_job_id == job.id,
                RenderStep.step_kind == step_kind,
            )
        )
        if not step:
            raise ApiError(404, "job_step_not_found", "Job step not found.")
        return job, step

    def mark_job_retry(self, job_id: str, error: AdapterError) -> None:
        job = self.db.get(RenderJob, UUID(job_id))
        if not job:
            return
        step = self.db.scalar(select(RenderStep).where(RenderStep.render_job_id == job.id))
        job.status = JobStatus.queued
        job.retry_count += 1
        job.error_code = error.code
        job.error_message = error.message
        if step:
            step.status = JobStatus.queued
            step.error_code = error.code
            step.error_message = error.message
        self.db.commit()

    def mark_job_failed(self, job_id: str, error: AdapterError) -> None:
        job = self.db.get(RenderJob, UUID(job_id))
        if not job:
            return
        step = self.db.scalar(select(RenderStep).where(RenderStep.render_job_id == job.id))
        job.status = JobStatus.failed
        job.error_code = error.code
        job.error_message = error.message
        job.completed_at = datetime.now(timezone.utc)
        if step:
            step.status = JobStatus.failed
            step.error_code = error.code
            step.error_message = error.message
            step.completed_at = datetime.now(timezone.utc)
        self.db.commit()

    def execute_idea_job(self, job_id: str, text_provider: TextProvider | None = None) -> None:
        job, step = self._get_job_and_step(job_id, StepKind.idea_generation)
        project = self.db.get(Project, job.project_id)
        brief = self.db.get(ProjectBrief, project.active_brief_id if project else None) if project else None
        if not project or not brief:
            raise AdapterError("internal", "missing_job_input", "Idea generation inputs are missing.")
        resolved_text_provider, routing_decision = (
            (text_provider, None)
            if text_provider is not None
            else RoutingService(self.db, self.settings).build_text_provider_for_workspace(project.workspace_id)
        )

        job.status = JobStatus.running
        job.started_at = datetime.now(timezone.utc)
        step.status = JobStatus.running
        step.started_at = datetime.now(timezone.utc)
        provider_run = ProviderRun(
            render_job_id=job.id,
            render_step_id=step.id,
            project_id=project.id,
            workspace_id=project.workspace_id,
            execution_mode=self._provider_execution_mode(routing_decision),
            worker_id=routing_decision.worker_id if routing_decision else None,
            provider_credential_id=(
                routing_decision.provider_credential_id if routing_decision else None
            ),
            provider_name=(
                routing_decision.provider_name
                if routing_decision
                else ("azure_openai" if not self.settings.use_stub_providers else "stub_text_provider")
            ),
            provider_model=(
                routing_decision.provider_model
                if routing_decision
                else (self.settings.azure_openai_chat_deployment or "stub")
            ),
            operation="idea_generation",
            request_hash=job.request_hash,
            status=ProviderRunStatus.running,
            request_payload=self._brief_payload(brief),
            routing_decision_payload=self._provider_run_payload(routing_decision),
        )
        self.db.add(provider_run)
        self.db.commit()

        started = time.perf_counter()
        try:
            output = resolved_text_provider.generate_ideas(self._brief_payload(brief))
        except AdapterError as error:
            self._finalize_provider_run(provider_run, started_at=started, error=error)
            self.db.commit()
            raise

        ideas = output.get("ideas") or []
        if len(ideas) != 5:
            raise AdapterError("internal", "invalid_idea_count", "Provider returned an invalid idea count.")
        idea_set = IdeaSet(
            project_id=project.id,
            source_brief_id=brief.id,
            created_by_user_id=job.created_by_user_id,
            prompt_input=self._brief_payload(brief),
        )
        self.db.add(idea_set)
        self.db.flush()
        for index, raw_idea in enumerate(ideas, start=1):
            self.db.add(
                IdeaCandidate(
                    idea_set_id=idea_set.id,
                    project_id=project.id,
                    title=str(raw_idea["title"]),
                    hook=str(raw_idea["hook"]),
                    summary=str(raw_idea["summary"]),
                    tags=list(raw_idea.get("tags", [])),
                    order_index=index,
                )
            )

        project.stage = ProjectStage.script
        self._finalize_provider_run(provider_run, started_at=started, response_payload=output)
        job.status = JobStatus.completed
        job.completed_at = datetime.now(timezone.utc)
        step.status = JobStatus.completed
        step.completed_at = datetime.now(timezone.utc)
        step.output_payload = {"idea_set_id": str(idea_set.id)}
        self._set_step_checkpoint(step, {"idea_set_id": str(idea_set.id)})
        record_audit_event(
            self.db,
            workspace_id=project.workspace_id,
            user_id=job.created_by_user_id,
            event_type="ideas.generated",
            target_type="idea_set",
            target_id=str(idea_set.id),
            payload={},
        )
        self.db.commit()

    def execute_script_job(self, job_id: str, text_provider: TextProvider | None = None) -> None:
        job, step = self._get_job_and_step(job_id, StepKind.script_generation)
        project = self.db.get(Project, job.project_id)
        brief = self.db.get(ProjectBrief, project.active_brief_id if project else None) if project else None
        idea = self.db.get(IdeaCandidate, project.selected_idea_id if project else None) if project else None
        if not project or not brief or not idea:
            raise AdapterError("internal", "missing_job_input", "Script generation inputs are missing.")
        resolved_text_provider, routing_decision = (
            (text_provider, None)
            if text_provider is not None
            else RoutingService(self.db, self.settings).build_text_provider_for_workspace(project.workspace_id)
        )

        job.status = JobStatus.running
        job.started_at = datetime.now(timezone.utc)
        step.status = JobStatus.running
        step.started_at = datetime.now(timezone.utc)
        provider_run = ProviderRun(
            render_job_id=job.id,
            render_step_id=step.id,
            project_id=project.id,
            workspace_id=project.workspace_id,
            execution_mode=self._provider_execution_mode(routing_decision),
            worker_id=routing_decision.worker_id if routing_decision else None,
            provider_credential_id=(
                routing_decision.provider_credential_id if routing_decision else None
            ),
            provider_name=(
                routing_decision.provider_name
                if routing_decision
                else ("azure_openai" if not self.settings.use_stub_providers else "stub_text_provider")
            ),
            provider_model=(
                routing_decision.provider_model
                if routing_decision
                else (self.settings.azure_openai_chat_deployment or "stub")
            ),
            operation="script_generation",
            request_hash=job.request_hash,
            status=ProviderRunStatus.running,
            request_payload={"brief": self._brief_payload(brief), "idea": self._idea_payload(idea)},
            routing_decision_payload=self._provider_run_payload(routing_decision),
        )
        self.db.add(provider_run)
        self.db.commit()

        started = time.perf_counter()
        try:
            output = resolved_text_provider.generate_script(
                brief_payload=self._brief_payload(brief),
                selected_idea=self._idea_payload(idea),
            )
        except AdapterError as error:
            self._finalize_provider_run(provider_run, started_at=started, error=error)
            self.db.commit()
            raise

        lines = output.get("lines") or []
        if not lines:
            raise AdapterError("internal", "empty_script_output", "Provider returned an empty script.")
        next_version = (
            self.db.scalar(select(func.max(ScriptVersion.version_number)).where(ScriptVersion.project_id == project.id))
            or 0
        ) + 1
        estimated_duration = int(output.get("estimated_duration_seconds") or sum(int(line["duration_sec"]) for line in lines))
        total_words = sum(len(str(line["narration"]).split()) for line in lines)
        script = ScriptVersion(
            project_id=project.id,
            based_on_idea_id=idea.id,
            created_by_user_id=job.created_by_user_id,
            version_number=next_version,
            source_type=ScriptSource.generated,
            approval_state="draft",
            total_words=total_words,
            estimated_duration_seconds=estimated_duration,
            reading_time_label=output.get("reading_time_label") or f"{estimated_duration}s draft narration",
            lines=lines,
        )
        self.db.add(script)
        self.db.flush()
        project.active_script_version_id = script.id
        project.active_scene_plan_id = None
        project.stage = ProjectStage.script
        self._finalize_provider_run(provider_run, started_at=started, response_payload=output)
        job.status = JobStatus.completed
        job.completed_at = datetime.now(timezone.utc)
        step.status = JobStatus.completed
        step.completed_at = datetime.now(timezone.utc)
        step.output_payload = {"script_version_id": str(script.id)}
        self._set_step_checkpoint(step, {"script_version_id": str(script.id)})
        record_audit_event(
            self.db,
            workspace_id=project.workspace_id,
            user_id=job.created_by_user_id,
            event_type="scripts.generated",
            target_type="script_version",
            target_id=str(script.id),
            payload={},
        )
        self.db.commit()

    def expire_stale_jobs(self) -> int:
        threshold = datetime.now(timezone.utc) - timedelta(minutes=self.settings.planning_job_timeout_minutes)
        stale_jobs = self.db.scalars(
            select(RenderJob).where(
                RenderJob.queue_name == "planning",
                RenderJob.status.in_([JobStatus.queued, JobStatus.running]),
                RenderJob.created_at < threshold,
            )
        ).all()
        for job in stale_jobs:
            job.status = JobStatus.failed
            job.error_code = "job_timeout"
            job.error_message = "The planning job expired before completion."
            job.completed_at = datetime.now(timezone.utc)
            step = self.db.scalar(select(RenderStep).where(RenderStep.render_job_id == job.id))
            if step:
                step.status = JobStatus.failed
                step.error_code = "job_timeout"
                step.error_message = "The planning job expired before completion."
                step.completed_at = datetime.now(timezone.utc)
        self.db.commit()
        return len(stale_jobs)
