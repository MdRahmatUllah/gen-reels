# Phase 7 Architecture

## Components Added

- Workspace provider credential vault
- Local worker registration service
- Routing policy engine
- Worker health and capability tracking
- Hybrid usage accounting

## Data Changes

- Add encrypted BYO credential records
- Add local worker records, capability metadata, and heartbeat history
- Extend provider run records with `execution_mode` and `worker_id`
- Add worker capability flags for ordered-reference images, first/last-frame video, and local TTS

## Risk Controls

- Secrets must never be returned to the frontend after the initial write.
- Local worker trust boundaries are defined in `13-local-worker-agent-protocol.md`.
- Routing must fail closed if a workspace routing policy is invalid, misconfigured, or references an offline worker.
