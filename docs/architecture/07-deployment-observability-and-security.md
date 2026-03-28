# Deployment, Observability, And Security

## Environment Strategy

- Local development with Docker Compose
- Shared staging environment for feature validation
- Production environment with isolated services and managed storage

## Deployment Units

- React frontend application (static hosting via CDN)
- FastAPI application service
- Celery worker pool (planning and generation tasks)
- Celery FFmpeg composition worker pool (CPU-optimized instances)
- Celery Beat scheduler (one instance, not scaled horizontally)
- PostgreSQL (managed database service)
- Redis (managed cache and broker)
- S3-compatible storage (managed object store)
- Reverse proxy and TLS termination

## Worker Autoscaling Strategy

Workers must scale on **queue depth**, not CPU utilization. CPU utilization responds too slowly and is misleading for queue-bound workloads.

| Worker Pool | Scaling Signal | Min | Max | Notes |
|---|---|---|---|---|
| Planning workers | Queue depth > 5 | 1 | 10 | Low-cost, fast tasks |
| Image generation workers | Queue depth > 2 | 1 | 20 | API-rate-bound |
| Video generation workers | Queue depth > 1 | 1 | 10 | API-rate-bound or GPU-bound |
| FFmpeg composition workers | Queue depth > 1 | 1 | 8 | CPU-heavy |
| Maintenance workers | Always 1 | 1 | 1 | Celery Beat schedule only |

Scale-down should be gradual (remove one worker at a time) and always wait for in-progress tasks to complete — never terminate a busy container. Target maximum queue wait time of 60 seconds as the primary SLO signal.

## CI/CD Expectations

- Lint and test on every pull request
- Build container images for app and worker services
- Run database migrations as part of controlled deployment (never auto-migrate in production)
- Promote from staging to production only after smoke tests on API, queue, and storage
- Container images are tagged with the git commit SHA, never `latest` in production

## Secret Management

Secret management uses the cloud provider's native secret manager as the system of record:

- AWS: AWS Secrets Manager
- GCP: Google Secret Manager
- Azure: Azure Key Vault

**Rules:**
- No plaintext secrets in environment variables in staging or production. Secrets are injected at runtime by the secret manager SDK or a secrets-aware deployment tool.
- Doppler is acceptable for local development secret synchronization.
- Secret rotation must be possible without a service restart. Services must re-read secrets on a configurable refresh interval.
- Platform-managed API keys for hosted generation providers are stored in the secret manager.
- Workspace API keys for automation and webhook verification are separate Phase 6 credentials, stored as hashes in PostgreSQL and never recoverable after creation.
- BYO workspace credentials (Phase 7) use a separate encrypted table in PostgreSQL with Key Management Service (KMS) envelope encryption.

## Media Asset Delivery — Signed URL Policy

Generated assets and exports are never served through the API server. They are delivered via pre-signed object storage URLs.

| Use Case | URL TTL | Notes |
|---|---|---|
| In-app asset preview | 1 hour | Refreshed on page load |
| Export download | 5 minutes | Short TTL to limit link sharing |
| Worker upload URL | Step deadline duration | Provided at job pickup |
| Reference image for generation | 30 minutes | Sufficient for one generation request |

The platform provides a `POST /assets/{asset_id}/signed-url` endpoint that generates a fresh signed URL. The frontend calls this endpoint whenever a URL is needed rather than caching URLs. Expired URL errors from the frontend should trigger a re-sign request, not a page refresh.

## Observability

- Structured logs across app and worker services using JSON format with consistent field names (`correlation_id`, `workspace_id`, `job_id`, `step_id`, `provider_id`)
- Metrics for queue depth, job duration, provider latency, retry rates, and export completion rate
- Traces or correlation IDs across HTTP requests, job executions, and provider calls
- Dashboards for:
  - Queue health per worker pool (depth, age of oldest task, throughput)
  - Provider health (latency p50/p95, error rate, cost per unit)
  - Business metrics (renders started, renders completed, exports downloaded, active workspaces)
  - Cost by modality and by workspace plan tier

## Security Model

- Short-lived access tokens (15 minutes) with refresh token rotation — see `12-authentication-and-identity.md`
- Workspace-scoped authorization checks on all project and asset routes
- Encryption at rest for secrets and sensitive workspace configuration using KMS envelope encryption
- Signed URLs with configured TTL for export and asset delivery — no direct S3 public access
- Content moderation on inputs and outputs — see `09-content-moderation-and-safety.md`

## File And Asset Safety

- Validate upload types and sizes at the API layer before issuing upload URLs
- Scan uploaded files with the moderation provider if user media upload is introduced (Phase 6)
- Keep all generated and user assets in private buckets — no public bucket access allowed
- Use lifecycle policies to transition intermediate assets to cold storage and delete expired assets automatically

## Reliability And Recovery

- Database: daily automated backups with point-in-time recovery. Restore procedure must be tested quarterly.
- Object storage: versioning enabled on exports bucket. Critical exports replicated to a second region.
- Dead-letter queue: unrecoverable Celery tasks after exhausting retries are routed to a dead-letter queue. Ops team receives an alert within 5 minutes. Dead-letter contents are inspectable via the admin UI.
- Usage and billing reconciliation: `reconcile_usage_vs_billing` job runs hourly. Discrepancies above a threshold trigger an alert and are logged to a reconciliation audit table. Reconciliation failures must not affect user-facing credit balances.

## Cost Controls

- Per-plan quotas and credit enforcement — see `11-rate-limiting-and-quota-enforcement.md`
- Alerts on provider cost spikes: alert when a workspace's hourly provider spend exceeds 3× its 7-day rolling average
- Queue-level circuit breakers: if the video generation queue depth exceeds a configurable threshold (default: 500 steps), new render job creation is paused and the team is alerted
- Operator tooling to pause expensive modalities (image, video, music) independently if a provider becomes unstable or abnormally expensive

