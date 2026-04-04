# YouTube Publishing Implementation Plan

## Goal

Add a production-oriented publishing pipeline that lets each platform user:

1. upload a video into the platform
2. transcribe voiceover with the local Whisper small model
3. generate YouTube metadata from the transcript
4. review and approve metadata
5. connect multiple YouTube accounts through Google OAuth
6. configure per-account daily schedules
7. batch schedule or immediately publish videos through backend workers

## Backend Shape

### Data model

- `youtube_accounts`
  - one row per connected YouTube channel per platform user
  - stores encrypted access and refresh tokens
  - stores Google email, channel ID, title, handle, token expiry, and default-account flag
- `videos`
  - canonical publishing asset uploaded into platform storage
  - tracks processing and publishing lifecycle
- `video_transcripts`
  - single transcript record per video
  - stores full transcript text and word timestamps
- `video_metadata_versions`
  - versioned generated and manually-approved metadata
  - stores title options, recommended title, final title, description, tags, and hook summary
- `publish_schedules`
  - one active daily schedule per YouTube account
  - stores timezone plus one or more local publish slots
- `publish_jobs`
  - single publish action with immediate or scheduled mode
  - tracks attempts, status, progress, YouTube video ID, and failure detail
- `audit_logs`
  - structured audit trail for account connect/disconnect, schedule changes, and upload lifecycle

### Services

- `integrations/youtube/oauth.py`
  - creates and validates OAuth state
  - exchanges auth code
  - refreshes tokens
- `integrations/youtube/client.py`
  - fetches Google profile and authenticated channel info
  - uploads video through YouTube Data API resumable upload flow
- `integrations/youtube/service.py`
  - coordinates OAuth completion
  - validates upload metadata and token freshness
- `integrations/youtube/scheduler.py`
  - validates local slots and timezones
  - converts local schedule slots into future UTC publish times
- `services/video_service.py`
  - stores uploaded videos
  - extracts audio
  - transcribes with local Whisper
  - generates metadata through the existing routed text provider abstraction
- `services/youtube_account_service.py`
  - upserts connected accounts
  - preserves refresh tokens across reconnects
  - manages default account selection
- `services/publish_schedule_service.py`
  - creates and updates per-account daily schedules
  - previews next future UTC slots
- `services/publish_job_service.py`
  - creates immediate and scheduled publish jobs
  - previews batch scheduling assignments
  - enqueues due scheduled jobs
  - executes resumable upload publishing

### Workers

- `workers/video_processing.py`
  - `video.process_upload`
  - `video.generate_metadata`
- `workers/youtube_publish.py`
  - `youtube.publish_job`
  - `youtube.enqueue_due_jobs`

## Frontend Shape

### Pages

- `Connected YouTube Accounts`
- `Publishing Videos`
- `Video Metadata Review`
- `Schedule Settings`
- `Batch Scheduler`
- `Publish Queue Monitor`

### API and hooks

- `frontend/src/lib/youtube-api.ts`
- `frontend/src/hooks/use-youtube-publishing.ts`
- `frontend/src/types/youtube.ts`

## Processing Flow

1. User uploads a video from the React app.
2. Backend stores the asset and creates a `videos` row.
3. Celery queues `video.process_upload`.
4. Worker extracts audio and transcribes with local Whisper small.
5. Transcript is sent to the routed text provider to generate YouTube metadata.
6. User reviews metadata and approves a final version.
7. User either:
   - publishes immediately, or
   - schedules the next available future slot, or
   - batch schedules multiple approved videos
8. Beat runs `youtube.enqueue_due_jobs` every minute.
9. Publishing worker performs resumable `videos.insert` upload.
10. Job and video state move to `published` or `failed`, and audit logs are written.

## Extension Notes

- Add richer provider-specific prompt controls inside `generate_video_metadata` if brand voice needs more structure.
- Add webhook or SSE push events for publish-job progress if polling becomes limiting.
- Add explicit retry policy tuning per error code once real YouTube failure patterns are observed in production.
- Add thumbnail upload, playlist assignment, category, and language fields as a follow-up.
