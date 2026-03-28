# Phase 4 Overview: Reliability And Billing

## Objective

Make rendering stable, recoverable, and commercially measurable so the product can scale without hidden operational or margin problems.

## In Scope

- Scene-level retries and resumability
- Provider run tracking and cost capture
- Usage ledger and credit accounting
- Billing and subscription plumbing
- Operator moderation review queue and quarantine handling
- Admin queue visibility and operational controls
- Alerting and failure reporting
- Cost controls calibrated for frame-pair image generation and 60-120 second renders

## What Users Get

- More reliable renders with transparent retry status
- Clear visibility into what failed and what was retried
- Usage and credit awareness before and during renders
- Safer recovery paths for moderated assets
- A product that can recover from common provider issues without full reruns

## Exit Criteria

- Failed renders can resume from the last successful step or scene without restarting
- Usage records map to real provider runs with no unresolved discrepancies
- The team can inspect queue health and cost hotspots without ad hoc scripts
- Users receive notifications when renders fail permanently
