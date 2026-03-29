from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_db_dep, get_settings_dep, get_storage_dep, require_auth
from app.schemas.automation import (
    WebhookDeliveryResponse,
    WebhookEndpointCreateRequest,
    WebhookEndpointCreateResponse,
    WebhookEndpointResponse,
    WebhookEndpointUpdateRequest,
    WorkspaceApiKeyCreateRequest,
    WorkspaceApiKeyCreateResponse,
    WorkspaceApiKeyResponse,
)
from app.schemas.common import MessageResponse
from app.schemas.execution import (
    ExecutionPolicyResponse,
    ExecutionPolicyUpdateRequest,
    LocalWorkerResponse,
    ProviderCredentialCreateRequest,
    ProviderCredentialResponse,
    ProviderCredentialUpdateRequest,
    WorkspaceAuthConfigurationCreateRequest,
    WorkspaceAuthConfigurationResponse,
    WorkspaceAuthConfigurationUpdateRequest,
)
from app.schemas.workspace import (
    AuditEventResponse,
    WorkspaceMemberCreateRequest,
    WorkspaceMemberResponse,
    WorkspaceMemberUpdateRequest,
)
from app.services.execution_policy_service import ExecutionPolicyService
from app.services.local_worker_service import LocalWorkerService
from app.services.provider_credential_service import ProviderCredentialService
from app.services.workspace_service import WorkspaceService

router = APIRouter()


@router.get("/members", response_model=list[WorkspaceMemberResponse])
def list_members(
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return WorkspaceService(db, settings).list_members(auth)


@router.post("/members", response_model=WorkspaceMemberResponse)
def create_member(
    payload: WorkspaceMemberCreateRequest,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return WorkspaceService(db, settings).create_member(auth, payload)


@router.patch("/members/{member_id}", response_model=WorkspaceMemberResponse)
def patch_member(
    member_id: str,
    payload: WorkspaceMemberUpdateRequest,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return WorkspaceService(db, settings).update_member(auth, member_id, payload)


@router.delete("/members/{member_id}", response_model=MessageResponse)
def delete_member(
    member_id: str,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    WorkspaceService(db, settings).remove_member(auth, member_id)
    return {"message": "Workspace member removed."}


@router.get("/audit-events", response_model=list[AuditEventResponse])
def list_audit_events(
    project_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return WorkspaceService(db, settings).list_audit_events(auth, project_id=project_id, limit=limit)


@router.get("/api-keys", response_model=list[WorkspaceApiKeyResponse])
def list_api_keys(
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return WorkspaceService(db, settings).list_api_keys(auth)


@router.post("/api-keys", response_model=WorkspaceApiKeyCreateResponse)
def create_api_key(
    payload: WorkspaceApiKeyCreateRequest,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return WorkspaceService(db, settings).create_api_key(auth, payload)


@router.post("/api-keys/{api_key_id}:revoke", response_model=WorkspaceApiKeyResponse)
def revoke_api_key(
    api_key_id: str,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return WorkspaceService(db, settings).revoke_api_key(auth, api_key_id)


@router.get("/provider-credentials", response_model=list[ProviderCredentialResponse])
def list_provider_credentials(
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return ProviderCredentialService(db, settings).list_credentials(auth)


@router.post("/provider-credentials", response_model=ProviderCredentialResponse)
def create_provider_credential(
    payload: ProviderCredentialCreateRequest,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return ProviderCredentialService(db, settings).create_credential(auth, payload)


@router.patch("/provider-credentials/{credential_id}", response_model=ProviderCredentialResponse)
def patch_provider_credential(
    credential_id: str,
    payload: ProviderCredentialUpdateRequest,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return ProviderCredentialService(db, settings).update_credential(auth, credential_id, payload)


@router.post("/provider-credentials/{credential_id}:validate", response_model=ProviderCredentialResponse)
def validate_provider_credential(
    credential_id: str,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return ProviderCredentialService(db, settings).validate_credential(auth, credential_id)


@router.post("/provider-credentials/{credential_id}:revoke", response_model=ProviderCredentialResponse)
def revoke_provider_credential(
    credential_id: str,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return ProviderCredentialService(db, settings).revoke_credential(auth, credential_id)


@router.get("/execution-policy", response_model=ExecutionPolicyResponse)
def get_execution_policy(
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
):
    return ExecutionPolicyService(db).get_policy(auth)


@router.put("/execution-policy", response_model=ExecutionPolicyResponse)
def put_execution_policy(
    payload: ExecutionPolicyUpdateRequest,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
):
    return ExecutionPolicyService(db).update_policy(auth, payload)


@router.get("/local-workers", response_model=list[LocalWorkerResponse])
def list_local_workers(
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
    storage=Depends(get_storage_dep),
):
    return LocalWorkerService(db, settings, storage).list_workers(auth)


@router.post("/local-workers/{worker_id}:revoke", response_model=LocalWorkerResponse)
def revoke_local_worker(
    worker_id: str,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
    storage=Depends(get_storage_dep),
):
    return LocalWorkerService(db, settings, storage).revoke_worker(auth, worker_id)



@router.get("/webhooks", response_model=list[WebhookEndpointResponse])
def list_webhooks(
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return WorkspaceService(db, settings).list_webhook_endpoints(auth)


@router.post("/webhooks", response_model=WebhookEndpointCreateResponse)
def create_webhook(
    payload: WebhookEndpointCreateRequest,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return WorkspaceService(db, settings).create_webhook_endpoint(auth, payload)


@router.patch("/webhooks/{endpoint_id}", response_model=WebhookEndpointResponse)
def patch_webhook(
    endpoint_id: str,
    payload: WebhookEndpointUpdateRequest,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return WorkspaceService(db, settings).update_webhook_endpoint(auth, endpoint_id, payload)


@router.delete("/webhooks/{endpoint_id}", response_model=MessageResponse)
def delete_webhook(
    endpoint_id: str,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    WorkspaceService(db, settings).delete_webhook_endpoint(auth, endpoint_id)
    return {"message": "Webhook endpoint deleted."}


@router.post("/webhooks/{endpoint_id}:test", response_model=WebhookDeliveryResponse)
def test_webhook(
    endpoint_id: str,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return WorkspaceService(db, settings).test_webhook_endpoint(auth, endpoint_id)


@router.get("/webhook-deliveries", response_model=list[WebhookDeliveryResponse])
def list_webhook_deliveries(
    endpoint_id: str | None = None,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return WorkspaceService(db, settings).list_webhook_deliveries(auth, endpoint_id)


@router.get("/auth-configurations", response_model=list[WorkspaceAuthConfigurationResponse])
def list_auth_configurations(
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return WorkspaceService(db, settings).list_auth_configurations(auth)


@router.post("/auth-configurations", response_model=WorkspaceAuthConfigurationResponse)
def create_auth_configuration(
    payload: WorkspaceAuthConfigurationCreateRequest,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return WorkspaceService(db, settings).create_auth_configuration(auth, payload)


@router.patch(
    "/auth-configurations/{configuration_id}",
    response_model=WorkspaceAuthConfigurationResponse,
)
def patch_auth_configuration(
    configuration_id: str,
    payload: WorkspaceAuthConfigurationUpdateRequest,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return WorkspaceService(db, settings).update_auth_configuration(auth, configuration_id, payload)
