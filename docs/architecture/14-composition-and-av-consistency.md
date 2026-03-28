# Composition And Audio-Visual Consistency

## Why This Document Exists

Each scene in a reel is generated independently — a different image, a different video clip, a different narration take. Without deliberate composition engineering, the final merged export will look and sound like a collage: mismatched visual tone, inconsistent audio levels, jarring scene cuts, and music that loops awkwardly or disappears between scenes.

This document defines the platform's strategy for ensuring that independently generated assets assemble into a single cohesive video with seamless visual transitions, consistent audio, and a continuous music bed.

---

## The Composition Problem

Five independent failure modes can break the final video's perceived quality:

| Failure | Cause | Effect On Viewer |
|---|---|---|
| Visual tone drift | Color grading varies between AI-generated clips | Jarring color jumps at scene cuts |
| Clip duration mismatch | Narration audio is longer or shorter than the video clip | Video freezes or narration cuts off |
| Audio level inconsistency | Narration from different TTS calls varies in loudness | Volume jumps between scenes |
| Music discontinuity | Music track loops, restarts, or disappears | Obvious edit artifacts in the background track |
| Scene transition abruptness | Hard cuts between clips with different motion characteristics | Visually jarring transitions |

The composition worker must address all five before writing the final export.

---

## Composition Inputs

Before the composition step begins, the following assets must all be in a `completed` state and verified:

| Asset | Source | Required |
|---|---|---|
| Video clip per scene | Video generation step or preview asset | ✅ All scenes |
| Narration audio per scene | Narration generation step | ✅ All scenes |
| Approved consistency pack snapshot | Stored at render job creation | ✅ Required |
| Music track | Music preparation step | ✅ Required (or `allow_export_without_music: true`) |
| Subtitle file | Subtitle generation step | ❌ Optional (non-blocking) |
| Keyframe reference per scene | Stored after keyframe review | Used for pre-composition validation only |

The composition step will **not begin** if any required asset is missing, in a failed state, or has not passed output moderation. The orchestration service enforces this gate.

---

## Pre-Composition Validation

Before FFmpeg begins, the composition worker runs:

### 1. Consistency Pack Provenance Check
Verify that every scene clip asset references the **same `consistency_pack_snapshot_id`** as the render job. If any scene clip was generated against a different or missing snapshot, the composition step fails with `consistency_snapshot_mismatch`. This prevents visually inconsistent exports from silently being delivered.

### 2. Duration Verification
For each scene, verify:
- Narration audio duration ≤ video clip duration + 2 seconds (the 2-second tolerance allows music tail to carry over).
- If the narration is longer than the clip, the composition worker **extends the clip duration** using the clip's last frame (freeze-frame pad) rather than cutting the narration off.
- If the clip is significantly longer than narration (>3 seconds excess), speed-match or trim rather than leaving a silent section.

### 3. Asset Stream Probe
Probe each video clip and audio file using `ffprobe` to confirm:
- Uniform resolution and frame rate across all clips (must match the export profile).
- All audio files are single-channel (mono) or multi-channel (stereo) — do not mix mono and stereo.
- No corrupt or zero-byte assets.

---

## Scene Assembly Strategy

```mermaid
flowchart LR
    Clips[\"Scene Clips + Narration\"] --> Sync[\"Per-Scene A/V Sync\"]
    Sync --> Transition[\"Scene Transitions\"]
    Transition --> Timeline[\"Scene Timeline\"]
    Timeline --> MusicMix[\"Music Underlay Mix\"]
    MusicMix --> Subtitle[\"Subtitle Burn-In\"]
    Subtitle --> Normalise[\"Loudness Normalisation\"]
    Normalise --> Export[\"Final Export\"]
```

### Step 1: Per-Scene A/V Sync

For each scene, align the narration audio to the start of the video clip:
- The narration begins at timestamp 0 of the scene clip.
- If a scene has no narration (silent scene), the clip runs at its natural duration with no audio pad.

### Step 2: Scene Transitions

The platform supports two modes selectable at the visual preset level:

| Mode | Description | Suitable For |
|---|---|---|
| `hard_cut` | Direct cut from one scene to the next | Fast-paced, high-energy content |
| `crossfade` | 0.25–0.5 second dissolve between scenes | Narrative, testimonial, educational |

Default is `hard_cut`. Crossfade adds a short overlap window and must be accounted for in total duration calculation. Scene transitions must **never** be longer than 0.5 seconds — anything longer competes with the 5–10 second scene length.

### Step 3: Music Underlay Mix

Music is mixed as a continuous bed across the **entire video** at a fixed level below narration:

- **Music target level:** −20 dBFS LUFs (LUFS integrated) in sections without narration.
- **Music ducking under narration:** Music attenuates by −12 dB during narration passages and returns to full level during any silent pause. Ducking uses a fade-in and fade-out of 0.3 seconds to avoid audible pumping.
- **Music timing:** The music track starts at the beginning of the video and fades out over the final 1.5 seconds of the export. If the selected music track is shorter than the total video duration, it loops with a 2-second crossfade loop point to prevent a hard restart.
- **Music tail:** The last scene's narration may end before the video clip ends. The music sustains through the natural end of the last clip, then fades.

### Step 4: Subtitle Burn-In

If the subtitle file is present:
- Subtitles are timed to narration audio, not to the video clip.
- Burn subtitles onto the video track using the configured subtitle style (font, size, color, position — from the visual preset or export profile).
- If the subtitle file is absent, this step is skipped silently.

### Step 5: Loudness Normalisation

Apply loudness normalisation to the final mixed audio stream:
- Target: **−14 LUFS** integrated loudness, which is the recommended level for TikTok and Instagram Reels.
- True peak limit: **−1.0 dBTP** to prevent clipping on all consumer devices.
- Apply a two-pass normalisation: probe the integrated loudness, then apply the correction gain.

---

## FFmpeg Composition Command Structure

The composition worker builds and executes a structured FFmpeg command. The command is constructed programmatically — never interpolated from user-provided strings — and logged in its entirety in the `provider_run` record for the composition step.

```
ffmpeg
  -i scene_1.mp4 -i scene_1_narration.aac
  -i scene_2.mp4 -i scene_2_narration.aac
  ... (all scene clips and narration files)
  -i music_track.mp3
  -filter_complex "
    [0:v][2:v]... concat=n=N:v=1:a=0 [video];
    [1:a][3:a]... concat=n=N:v=0:a=1 [narration];
    [music_stream] aloop ... [looped_music];
    [narration][looped_music] sidechaincompress ... [ducked_music];
    [narration][ducked_music] amix=inputs=2 [audio_mix];
    [audio_mix] loudnorm=I=-14:TP=-1.0:LRA=11 [final_audio]
  "
  -map [video] -map [final_audio]
  -c:v libx264 -preset fast -crf 23
  -c:a aac -b:a 192k
  -movflags +faststart
  output.mp4
```

Key safety rules:
- The FFmpeg command must be built from a validated asset manifest, not from raw user input.
- All input file paths must be pre-signed S3 URLs validated before the command is constructed.
- Any FFmpeg process that runs for more than 10 minutes is considered hung and is terminated with a `composition_timeout` error.

---

## Voice Continuity Across Scenes

For the audio mix to sound like one continuous narrator (not multiple different voices), the platform enforces:

- All narration steps within a single render job must use the **same `voice_preset_id`**.
- If a scene-specific voice override is requested, it must be the same voice preset. Voice-per-scene is not supported in Phases 3–4.
- The narration provider must be called with identical voice parameters (voice ID, speed, pitch, stability) on every scene within the same render job.
- Voice parameters are frozen at render job creation from the `voice_preset` snapshot. In-flight changes to the voice preset do not affect the current render job.

---

## What Consistency Looks Like In Practice

A well-composed 30-second reel from this platform should have:

- A **single character appearance** maintained across all 4–6 scene clips (same face, outfit, lighting treatment) — enforced by the consistency pack.
- **Narration that flows as one read** — same voice, same pacing, no volume jumps between scenes — enforced by voice preset freezing and loudness normalisation.
- **Continuous background music** that sits under the narrator's voice and never abruptly starts or stops — enforced by the music ducking and looping strategy.
- **Clean scene transitions** that guide the viewer without announcing themselves — enforced by the configurable transition mode (default: hard cut for short-form content).
- **Uniform visual resolution and framing** from the first to the last scene — enforced by consistency pack camera defaults and pre-composition asset stream probing.

---

## Failure Handling

| Failure | Action |
|---|---|
| `consistency_snapshot_mismatch` | Fail composition. Notify user. Do not deliver a visually split export. |
| `duration_mismatch_exceeds_tolerance` | Fail composition. Show per-scene timing report in render monitor. |
| `asset_stream_corrupt` | Fail composition. Mark the problematic scene step as failed. Allow scene retry. |
| `composition_timeout` | Fail composition. Alert operations team. Allow operator replay. |
| `music_preparation_failed` | If `allow_export_without_music: true`, continue without music. Otherwise fail composition. |
| FFmpeg non-zero exit | Capture stdout/stderr in provider run. Fail composition. Allow replay. |

---

## Implementation Phasing

| Phase | Composition Work |
|---|---|
| Phase 3 | Full FFmpeg composition with narration sync, music underlay, music ducking, hard cut transitions, loudness normalisation |
| Phase 4 | Composition observability: duration, file size, loudness level in export metadata |
| Phase 5 | Crossfade transition support; subtitle style controls applied at composition time |
| Phase 6 | Per-scene composition preview before final composition (team review of timeline) |

---

## Cross-References

- Visual consistency of scene clips: `08-visual-consistency-and-asset-memory.md`
- Music source strategy per phase: `05-job-orchestration-and-render-pipeline.md` → Music Step
- Subtitle non-blocking delivery: `05-job-orchestration-and-render-pipeline.md` → Subtitle Step
- Narration voice preset model: `04-data-model-and-storage.md` → `voice_presets`
- Export asset storage and metadata: `04-data-model-and-storage.md` → Generation And Assets
