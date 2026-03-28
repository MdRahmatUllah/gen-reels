# Phase 7 Integrations

## External Integrations

- Secret management or KMS service
- BYO provider APIs accessed on behalf of the workspace

## Internal Platform Integrations

- Existing provider adapter contracts
- Usage ledger and billing model
- Worker orchestration and queueing

## Contract Requirements

- BYO credential writes must be encrypted before storage.
- Local worker agents must authenticate and report supported modalities and health status.
- Routing decisions must be logged with enough detail to explain why a provider path was chosen.
- Local worker outputs must be uploaded through signed object-storage URLs rather than proxied through the API.
- Workspace registration credentials and worker registration tokens must be independently rotatable.

## Error Strategy

- Invalid BYO credentials must fail clearly and isolate the problem to the workspace using them.
- Offline local workers should not block the entire orchestration layer.
- Routing policy misconfiguration should fail closed and prompt operator or user action.

## Cost Notes

- This phase should reduce hosted cost for advanced users, but it increases support and security complexity.
- Do not enable broad local execution until hosted usage accounting and operational visibility are already trusted.
