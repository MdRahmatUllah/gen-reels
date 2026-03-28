# Composition And Audio-Visual Consistency

## Why This Document Exists

Each scene in a reel is generated independently - a different frame pair, a different video clip, a different narration take. Without deliberate composition engineering, the final merged export will look and sound like a collage.

This document defines the platform's strategy for ensuring that independently generated assets assemble into a single cohesive video with seamless visual transitions, consistent audio, and a continuous music bed.

## The Composition Problem

Five independent failure modes can break the final video's perceived quality:

| Failure | Cause | Effect On Viewer |
| --- | --- | --- |
| Visual tone drift | Color grading varies between AI-generated clips | Jarring color jumps at scene cuts |
| Clip duration mismatch | Narration audio is longer or shorter than the video clip | Video freezes or narration cuts off |
| Audio level inconsistency | Narration from different TTS calls varies in loudness | Volume jumps between scenes |
| Music discontinuity | Music track loops, restarts, or disappears | Obvious edit artifacts in the background track |
| Scene transition abruptness | Hard cuts between clips with different motion characteristics | Visually jarring transitions |

## Composition Inputs

Before the composition step begins, the following assets must all be in a `completed` state and verified:

| Asset | Source | Required |
| --- | --- | --- |
| Silent or normalized video clip per scene | Video generation plus source-audio stripping | Yes |
| Narration audio per scene | Narration generation step | Yes |
| Approved consistency pack snapshot | Stored at render job creation | Yes |
| Music track | Music preparation step | Yes, unless `allow_export_without_music` is true |
| Subtitle file | Subtitle generation step | Optional |
| Approved frame pair per scene | Stored after frame-pair review | Used for validation and lineage |

## Pre-Composition Validation

### 1. Consistency Pack Provenance Check

Verify that every scene clip asset references the same `consistency_pack_snapshot_id` as the render job.

### 2. Duration Verification

For each scene:

- target narration and clip duration should land in the 5-8 second authoring range before final assembly
- if the clip and narration differ slightly, prefer bounded speed adjustment first
- if narration remains longer after max stretch, freeze-pad the clip
- if the clip remains significantly longer than narration, trim it

### 3. Asset Stream Probe

Probe each video clip and audio file using `ffprobe` to confirm:

- uniform resolution and frame rate across all clips
- no corrupt or zero-byte assets
- source video audio has already been removed or is marked ignored by policy

## Scene Assembly Strategy

```mermaid
flowchart LR
    Clips["Silent Scene Clips + Narration"] --> Sync["Per-Scene A/V Sync"]
    Sync --> Transition["Scene Transitions"]
    Transition --> Timeline["Scene Timeline"]
    Timeline --> MusicMix["Music Underlay Mix"]
    MusicMix --> Subtitle["Subtitle Burn-In"]
    Subtitle --> Normalise["Loudness Normalisation"]
    Normalise --> Export["Final Export"]
```

### Step 1: Source Audio Policy

Provider-returned clip audio is not mixed into the final export by default.

- If the provider supports silent output, request silent output.
- Otherwise strip clip audio immediately after generation, for example with `ffmpeg -i input.mp4 -an -c:v copy output_silent.mp4`.
- The final mix uses narration plus music, not the source clip soundtrack.

### Step 2: Per-Scene A/V Sync

For each scene:

- narration begins at timestamp 0 of the scene clip
- silent scenes can run without narration
- clip retiming uses bounded speed adjustment before pad or trim

Suggested default bounds:

- clip speed adjustment: `0.92x` to `1.08x`
- narration speed change: disabled by default

### Step 3: Scene Transitions

The platform supports:

| Mode | Description | Suitable For |
| --- | --- | --- |
| `hard_cut` | Direct cut from one scene to the next | Fast-paced, high-energy content |
| `crossfade` | 0.25-0.5 second dissolve between scenes | Narrative, testimonial, educational |

Scene transitions must never be longer than 0.5 seconds because they compete with the 5-8 second scene length.

### Step 4: Music Underlay Mix

Music is mixed as a continuous bed across the entire video at a fixed level below narration:

- music target level: about -20 dBFS in sections without narration
- music ducking under narration: -12 dB with 0.3 second fades
- music timing: start at the beginning and fade out over the final 1.5 seconds

### Step 5: Subtitle Burn-In

If the subtitle file is present:

- subtitles are timed to narration audio, not to the raw video clip
- subtitles are burned using the configured subtitle style
- if the subtitle file is absent, this step is skipped silently

### Step 6: Loudness Normalisation

Apply loudness normalisation to the final mixed audio stream:

- target: -14 LUFS integrated
- true peak limit: -1.0 dBTP
- use a two-pass loudness normalization flow

## FFmpeg Composition Command Structure

The composition worker builds and executes a structured FFmpeg command. The command is constructed programmatically and logged in the composition provider run record.

## Voice Continuity Across Scenes

For the audio mix to sound like one continuous narrator:

- all narration steps within a single render job must use the same `voice_preset_id`
- the narration provider must be called with identical voice parameters on every scene within the job
- voice parameters are frozen at render job creation

## What Consistency Looks Like In Practice

A well-composed 60-120 second reel from this platform should have:

- a single character appearance maintained across scenes
- narration that flows as one read
- continuous background music that never abruptly starts or stops
- clean scene transitions
- uniform visual resolution and framing

## Failure Handling

| Failure | Action |
| --- | --- |
| `consistency_snapshot_mismatch` | Fail composition and notify the user |
| `duration_mismatch_exceeds_tolerance` | Fail composition and show a per-scene timing report |
| `asset_stream_corrupt` | Fail composition and allow scene retry |
| `composition_timeout` | Fail composition, alert operations, and allow operator replay |
| `music_preparation_failed` | Continue without music only if allowed by settings |
| FFmpeg non-zero exit | Capture stdout and stderr in provider run and fail composition |

## Implementation Phasing

| Phase | Composition Work |
| --- | --- |
| Phase 3 | Full FFmpeg composition with narration sync, source-audio stripping, retiming, music underlay, and loudness normalization |
| Phase 4 | Composition observability: duration, file size, loudness level in export metadata |
| Phase 5 | Crossfade support and subtitle style controls applied at composition time |
| Phase 6 | Per-scene composition preview before final composition |
