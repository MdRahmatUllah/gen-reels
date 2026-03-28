# Provider Abstraction And Integration Architecture

## Goals

- Avoid coupling product workflows to any single generation vendor.
- Normalize provider outputs into platform-native records.
- Preserve room for hosted providers now and local or BYO execution later.
- Ensure that swapping a provider never requires changes to product or orchestration code, only adapter changes.

## Integration Classes

- Text generation
- Image generation
- Video generation
- TTS and narration
- Music or audio bed generation
- Moderation and content safety
- Billing and payment
- Notifications and email

## Adapter Pattern

Each provider must implement a thin adapter interface with:

- Input normalization
- Output normalization
- Error translation
- Cost extraction
- Latency capture
- Idempotency or retry token support when available

The product calls interfaces such as `TextProvider`, `ImageProvider`, `VideoProvider`, `SpeechProvider`, `MusicProvider`, and `ModerationProvider` rather than provider SDKs directly.

## Adapter Versioning

Each adapter implementation carries a `provider_api_version` field that identifies the external API contract it implements. This is recorded in every `provider_run` entry.

**Breaking change rule:** If a provider changes its API contract in a breaking way (request shape, output schema, authentication mechanism), a new adapter class is created rather than modifying the existing one. The old adapter is deprecated and given a sunset date — it is never deleted immediately. Both adapter versions can coexist to allow staged migration.

**Non-breaking changes** (new optional response fields, rate limit changes, new optional request parameters) are handled in-place with no version bump.

## Provider Routing Rules

- Use one primary provider per expensive modality in the first production release.
- Keep one backup provider defined in operator config, not in the user-facing UI.
- Route by workspace plan, feature flag, quota, and provider health in later phases.
- Record the provider chosen and the reason for the routing decision in every provider run.
- Routing falls back to the backup provider only if the primary is unavailable or has exceeded its rate limit — never for quality improvement attempts.

## Fallback Compatibility Matrix

Automatic fallback is only permitted between providers that are **functionally equivalent** for the target operation. Equivalence is defined as:

| Criterion | Requirement |
|---|---|
| Same modality | Both providers must produce the same media type |
| Resolution compatibility | Fallback provider must support the same or better output resolution |
| No visible watermark difference | Fallback outputs must not carry provider-identifying watermarks if the primary does not |
| Same cost class | Fallback must not increase per-unit cost by more than 50% without an operator alert |
| Same content policy behavior | If primary filters a category of content, the fallback must apply equivalent filtering |

If a candidate fallback fails any of these criteria, it is not an automatic fallback option. The render step fails with the primary's error, and the user decides how to proceed.

## Contract Requirements

- Structured prompts and generation settings must be versioned (stored on the consistency pack and provider run).
- Adapters must return normalized metadata including duration, resolution, cost, and provider request identifiers.
- All binary outputs must be written to object storage and referenced by asset records — adapters must never return binary content directly to the orchestration layer.

## Credential Model

- Hosted credentials live in the cloud provider's native secret manager. No plaintext secrets in environment variables in staging or production.
- Workspace BYO credentials (Phase 7) are stored encrypted at rest, with scoped decryption only during job execution, and with strict audit events on every access.
- Local workers receive only the credentials needed for their specific execution policy — never the platform's hosted provider keys.

## Failure And Failure Category Taxonomy

Provider failures must be translated into platform error categories before being stored or surfaced:

| Platform Error Category | Meaning | Retryable |
|---|---|---|
| `provider_unavailable` | 5xx or timeout from provider | Yes |
| `provider_rate_limited` | 429 from provider | Yes (with backoff) |
| `provider_content_rejection` | Provider's own content policy refusal | No |
| `provider_invalid_input` | Malformed prompt or unsupported parameters | No |
| `provider_output_corrupt` | Output received but cannot be read or stored | Yes (limited) |
| `capability_mismatch` | Worker cannot process the step as specified | No for this worker |

The orchestration layer uses these categories to decide whether to retry, reroute, surface to the user, or terminate the step.

## Vendor Evaluation Criteria

When evaluating a new provider for any modality:

- Output quality and consistency
- Cost per successful unit
- Throughput and latency
- Rate limits and concurrency behavior
- Commercial terms and output usage licensing
- Stability of API contracts
- Observability and request tracing support
- Content policy compatibility with the platform's moderation requirements


