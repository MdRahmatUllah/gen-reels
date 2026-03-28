# Phase 4 Overview: Reliability And Billing

## Objective

Make rendering stable, recoverable, and commercially measurable so the product can scale without hidden operational or margin problems.

## Why This Phase Exists

The first end-to-end render is only the beginning. Without checkpointing, retries, cost visibility, and billing controls, the platform will be expensive to operate and frustrating for users.

## In Scope

- Scene-level retries and resumability (resume from last successful step, not from the beginning)
- Provider run tracking and cost capture
- Usage ledger and credit accounting
- Billing and subscription plumbing
- Operator moderation review queue and quarantine handling
- Admin queue visibility and operational controls
- Alerting and failure reporting
- Dead-letter handling and user notification for unrecoverable jobs

## Out Of Scope

- Advanced team collaboration
- Local execution
- Deep creative polish beyond operational reliability

## What Users Get

- More reliable renders with transparent retry status
- Clear visibility into what failed and what was retried
- Usage and credit awareness before and during renders
- Safer recovery paths for moderated assets
- A product that can recover from common provider issues without full reruns
- Notification when a render fails permanently with actionable guidance

## Deliverables

- Durable render checkpointing (resume from step N, not step 1)
- Usage ledger model
- Subscription and billing integration points
- Moderation review tooling for operators
- Admin job inspection surfaces
- Dead-letter queue and operator review workflow
- Operational dashboards and alerts

## Dead-Letter Escalation Path

When a render step exhausts all automatic retries:

1. The step is marked `dead_letter` and moved to the dead-letter queue.
2. An alert is sent to the operations team within 5 minutes.
3. The operator reviews the failure in the Admin UI with full provider run history, error details, and retry log.
4. The operator chooses: **replay** (re-enqueue the step) or **abandon** (mark the render job as permanently failed).
5. If abandoned, the user is notified via in-app notification and email with a human-readable explanation and a manual retry link that creates a fresh render job from the same approved inputs.

Dead-letter steps and their history are never deleted — they form part of the permanent audit trail.

## Exit Criteria

- Failed renders can resume from the last successful step or scene without restarting
- Usage records map to real provider runs with no unresolved discrepancies
- The team can inspect queue health and cost hotspots without ad hoc scripts
- Users receive notifications when renders fail permanently

