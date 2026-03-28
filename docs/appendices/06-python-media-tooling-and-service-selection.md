# Python Media Tooling And Service Selection

## Purpose

This appendix documents the Python-side media stack, supporting services, and implementation rules chosen for the platform. It serves as the definitive reference for which tools to use for each media processing task.

---

## Python Media Tooling

| Tool | Role | Use When | Recommendation |
|---|---|---|---|
| **FFmpeg** (CLI) | Rendering engine | All production composition, stripping, retiming, loudness normalisation, subtitle burn-in | ✅ Primary — source of truth |
| **ffmpeg-python** | Python FFmpeg wrapper | Building validated FFmpeg command graphs programmatically | ✅ Primary — used in composition worker |
| **ffprobe** (CLI) | Stream validation and metadata | Pre-composition asset probing, duration/codec/resolution checks | ✅ Required — for all validation |
| **PyAV** | Packet and frame inspection | Direct stream access beyond plain FFmpeg commands, frame-level analysis | ⚠️ Optional — use only when ffmpeg-python cannot express the operation |
| **MoviePy** | High-level prototyping | Quick experiments and demo builds | ❌ Not for production — too slow, too many silent failures |
| **Pillow** (PIL) | Image inspection and manipulation | Thumbnail generation, format conversion, metadata extraction | ✅ When working with still images |
| **minio-py** (MinIO SDK) | Object storage access | Asset upload, download, pre-signed URL generation | ✅ Primary — all storage operations |
| **boto3** | S3-compatible storage access | Alternative to minio-py if deploying to AWS S3 | ⚠️ Alternative — same API |

### FFmpeg Version Requirements

- Minimum: FFmpeg 6.0+
- Required filters: `loudnorm`, `setpts`, `atempo`, `tpad`, `sidechaincompress`, `amix`, `concat`
- Required codecs: `libx264`, `aac`, `libopus`
- The composition worker Dockerfile must install a specific FFmpeg version, not rely on OS package defaults.

### ffmpeg-python Usage Pattern

```python
import ffmpeg

# Example: audio strip
(
    ffmpeg
    .input("input.mp4")
    .output("output_silent.mp4", an=None, c="copy", v="copy")
    .overwrite_output()
    .run()
)

# Example: speed adjustment (1.1x)
(
    ffmpeg
    .input("input.mp4")
    .filter("setpts", "PTS/1.1")
    .output("output_retimed.mp4")
    .overwrite_output()
    .run()
)

# Example: loudness normalisation
(
    ffmpeg
    .input("input.mp4")
    .output("output_normalised.mp4",
            af="loudnorm=I=-14:TP=-1.0:LRA=11")
    .overwrite_output()
    .run()
)
```

---

## Recommended Supporting Services

| Service | Role | Phase |
|---|---|---|
| **PostgreSQL** | System of record for domain data, workflow state, usage | Phase 1 |
| **Redis** | Queue broker (Celery), cache, rate-limit counters, SSE buffering | Phase 1 |
| **MinIO** | S3-compatible object storage for all media assets | Phase 1 |
| **Docker / Docker Compose** | Container runtime and local development orchestration | Phase 1 |
| **Celery** | Distributed task queue for all async generation and processing | Phase 1 |
| **Celery Beat** | Scheduled task runner for maintenance jobs | Phase 1 |
| **Secret manager** (Azure Key Vault or equivalent) | Hosted credential storage for API keys and secrets | Phase 3+ |
| **Error tracking** (Sentry or equivalent) | Exception capture and alerting | Phase 3+ |
| **Metrics** (Prometheus + Grafana or equivalent) | Operational visibility, queue depth, provider latency | Phase 4+ |

---

## Default Implementation Rules

1. **Build FFmpeg commands programmatically** using `ffmpeg-python`. Never interpolate user-provided strings into FFmpeg commands.
2. **Strip provider-returned video audio** before final composition unless a feature flag says otherwise. This is not optional.
3. **Use bounded clip retiming** (0.85x–1.15x speed adjustment) before resorting to freeze-pad or trim.
4. **Keep media processing in worker services**, never in the frontend or API layer.
5. **Log all FFmpeg commands** — the full command string is stored in the `provider_run` record for the composition step.
6. **Probe before composition** — use `ffprobe` to validate resolution, codec, frame rate, and audio stream presence before building the FFmpeg filter graph.
7. **Use MinIO SDK (minio-py)** for all object storage operations. If deploying to AWS S3, swap the endpoint configuration — the SDK call patterns remain identical.
8. **Pin FFmpeg version** in the composition worker Dockerfile. FFmpeg filter behaviour varies across versions; the platform must run a tested, pinned version.

---

## Cross-References

- Composition worker architecture: `architecture/14-composition-and-av-consistency.md`
- MinIO storage configuration: `architecture/17-minio-storage-configuration.md`
- Docker strategy: `architecture/16-containerization-and-docker-strategy.md`
- Provider adapters and SDK usage: `architecture/06-provider-abstraction-and-integration-architecture.md`
