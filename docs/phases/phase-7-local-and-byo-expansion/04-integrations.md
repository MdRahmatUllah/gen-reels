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
- Local workers must declare whether they support ordered-reference image generation and first/last-frame video.
