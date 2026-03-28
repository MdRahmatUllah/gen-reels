# Deployment, Observability, And Security

## Environment Strategy

- Local development with Docker Compose
- Shared staging environment for feature validation
- Production environment with isolated services and managed storage

## Deployment Units

- React frontend application
- FastAPI application service
- Celery planning worker pool
- Celery frame-generation worker pool
- Celery video-generation worker pool
- Celery audio-normalization and retiming worker pool
- Celery FFmpeg composition worker pool
- Celery Beat scheduler
- PostgreSQL
- Redis
- MinIO or compatible object storage
- Reverse proxy and TLS termination

## Local Docker Compose Baseline

The local stack should include:

- `web`
- `api`
- `worker-planning`
- `worker-media`
- `worker-composition`
- `beat`
- `postgres`
- `redis`
- `minio`

Phase 7 or local open-source execution can add GPU-enabled worker containers without changing the control-plane service graph.

## Worker Autoscaling Strategy

Workers must scale on queue depth, not CPU utilization.

| Worker Pool | Scaling Signal | Min | Max | Notes |
| --- | --- | --- | --- | --- |
| Planning workers | Queue depth > 5 | 1 | 10 | Low-cost, fast tasks |
| Frame generation workers | Queue depth > 2 | 1 | 20 | API-rate-bound or GPU-bound |
| Video generation workers | Queue depth > 1 | 1 | 10 | API-rate-bound or GPU-bound |
| Audio normalization and retime workers | Queue depth > 3 | 1 | 10 | CPU-heavy but cheaper than video |
| FFmpeg composition workers | Queue depth > 1 | 1 | 8 | CPU-heavy |
| Maintenance workers | Always 1 | 1 | 1 | Beat schedule only |

## CI/CD Expectations

- Lint and test on every pull request
- Build container images for app and worker services
- Run database migrations as part of controlled deployment
- Promote from staging to production only after smoke tests on API, queue, and storage
- Container images are tagged with the git commit SHA, never `latest` in production

## Secret Management

- Azure Key Vault is the preferred secret manager when running Azure-first infrastructure.
- Alternate cloud secret managers remain valid if the deployment target changes.
- No plaintext secrets in environment variables in staging or production.
- Platform-managed API keys for hosted generation providers are stored in the secret manager.
- BYO workspace credentials use a separate encrypted table in PostgreSQL with envelope encryption.

## Media Asset Delivery

Generated assets and exports are never served through the API server. They are delivered via pre-signed object storage URLs generated against MinIO-compatible object storage.

| Use Case | URL TTL | Notes |
| --- | --- | --- |
| In-app asset preview | 1 hour | Refreshed on page load |
| Export download | 5 minutes | Short TTL to limit link sharing |
| Worker upload URL | Step deadline duration | Provided at job pickup |
| Reference image for generation | 30 minutes | Sufficient for one generation request |

## Observability

- Structured logs across app and worker services using JSON format with consistent field names
- Metrics for queue depth, job duration, provider latency, retry rates, and export completion rate
- Traces or correlation IDs across HTTP requests, job executions, and provider calls
- Dashboards for queue health, provider health, business metrics, and cost by modality
- Alerts on abnormal chained-scene invalidation rates and unexpected provider-returned clip audio

## Security Model

- Short-lived access tokens with refresh token rotation
- Workspace-scoped authorization checks on all project and asset routes
- Encryption at rest for secrets and sensitive workspace configuration
- Signed URLs with configured TTL for export and asset delivery
- Content moderation on inputs and outputs

## File And Asset Safety

- Validate upload types and sizes at the API layer before issuing upload URLs
- Scan uploaded files with the moderation provider if user media upload is introduced
- Keep all generated and user assets in private buckets
- Use lifecycle policies to transition intermediate assets to cold storage and delete expired assets automatically

## Reliability And Recovery

- Database backups with point-in-time recovery
- MinIO or equivalent object storage versioning on the exports bucket
- Dead-letter queue for unrecoverable Celery tasks
- Usage and billing reconciliation job runs hourly

## Cost Controls

- Per-plan quotas and credit enforcement
- Alerts on provider cost spikes
- Queue-level circuit breakers
- Operator tooling to pause expensive modalities independently
- Separate tracking for paired-image steps so image cost growth is visible before it reaches billing incidents
