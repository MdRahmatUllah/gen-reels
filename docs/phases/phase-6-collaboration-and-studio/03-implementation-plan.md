# Phase 6 Implementation Plan

## Backend Work

- Expand role and permission checks across project, preset, and export resources.
- Build brand kit models and enforcement hooks.
- Implement comments, review requests, and audit event services.
- Add shared template and asset visibility rules.

## Frontend Work

- Build team settings and membership management views.
- Add review queue and review action surfaces.
- Add comments and review notes where they fit naturally in project flows.
- Build brand kit configuration screens.

## Infra Work

- Extend event logging and audit retention.
- Add monitoring for permission errors and collaboration activity.

## QA Work

- Test role boundaries and permission-denied paths.
- Test approval flows on scripts, scene plans, and exports.
- Test brand kit enforcement and shared asset visibility.
- Test audit trail completeness.

## Milestones

- Milestone 1: roles and permissions
- Milestone 2: brand kits and shared presets
- Milestone 3: comments and reviews
- Milestone 4: auditability and workspace hardening

## Acceptance Criteria

- Multiple users can collaborate without overwriting each other blindly.
- Workspace-level branding can shape or constrain project output.
- Reviews and approvals are trackable after the fact.

