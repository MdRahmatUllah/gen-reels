from __future__ import annotations

import json
import tempfile
from pathlib import Path

from app.core.config import Settings
from app.integrations.ffmpeg import FFmpegError, FFmpegRunner


def _frame_rate_from_probe(stream: dict[str, object]) -> float | None:
    raw_value = str(stream.get("avg_frame_rate") or stream.get("r_frame_rate") or "0/0")
    if "/" not in raw_value:
        try:
            return float(raw_value)
        except ValueError:
            return None
    numerator, denominator = raw_value.split("/", 1)
    try:
        numerator_value = float(numerator)
        denominator_value = float(denominator)
    except ValueError:
        return None
    if denominator_value == 0:
        return None
    return round(numerator_value / denominator_value, 3)


def _probe_result(settings: Settings, input_name: str, *, workdir: Path) -> dict[str, object]:
    return FFmpegRunner(settings).probe(input_name, workdir=workdir)


def probe_media_bytes(
    settings: Settings,
    *,
    file_name: str,
    bytes_payload: bytes,
) -> dict[str, object]:
    runner = FFmpegRunner(settings)
    if not runner.available():
        return {}
    with tempfile.TemporaryDirectory() as temp_dir:
        workdir = Path(temp_dir)
        input_name = Path(file_name).name
        (workdir / input_name).write_bytes(bytes_payload)
        try:
            return _probe_result(settings, input_name, workdir=workdir)
        except FFmpegError:
            return {}


def strip_audio_from_video(
    settings: Settings,
    *,
    source_bytes: bytes,
    source_file_name: str,
) -> tuple[bytes, dict[str, object]]:
    runner = FFmpegRunner(settings)
    if not runner.available() or not source_file_name.lower().endswith(".mp4"):
        return source_bytes, {"has_audio_stream": False}
    with tempfile.TemporaryDirectory() as temp_dir:
        workdir = Path(temp_dir)
        input_name = f"input{Path(source_file_name).suffix or '.mp4'}"
        (workdir / input_name).write_bytes(source_bytes)
        try:
            runner.run(
                "ffmpeg",
                [
                    "-y",
                    "-i",
                    input_name,
                    "-map",
                    "0:v:0",
                    "-c:v",
                    "copy",
                    "-an",
                    "silent.mp4",
                ],
                workdir=workdir,
            )
            metadata = _probe_result(settings, "silent.mp4", workdir=workdir)
        except FFmpegError:
            return source_bytes, {"has_audio_stream": False}
        stream = next(
            (item for item in metadata.get("streams", []) if item.get("codec_type") == "video"),
            {},
        )
        format_payload = metadata.get("format", {})
        return (workdir / "silent.mp4").read_bytes(), {
            "duration_ms": int(float(format_payload.get("duration") or 0) * 1000),
            "width": int(stream.get("width") or 0) or None,
            "height": int(stream.get("height") or 0) or None,
            "frame_rate": _frame_rate_from_probe(stream),
            "has_audio_stream": False,
        }


def retime_video_to_target(
    settings: Settings,
    *,
    source_bytes: bytes,
    source_file_name: str,
    target_duration_ms: int,
) -> tuple[bytes, dict[str, object]]:
    runner = FFmpegRunner(settings)
    if not runner.available() or not source_file_name.lower().endswith(".mp4"):
        return source_bytes, {"duration_ms": target_duration_ms}
    with tempfile.TemporaryDirectory() as temp_dir:
        workdir = Path(temp_dir)
        input_name = f"input{Path(source_file_name).suffix or '.mp4'}"
        (workdir / input_name).write_bytes(source_bytes)
        try:
            probe = _probe_result(settings, input_name, workdir=workdir)
        except FFmpegError:
            return source_bytes, {"duration_ms": target_duration_ms}
        video_stream = next(
            (item for item in probe.get("streams", []) if item.get("codec_type") == "video"),
            {},
        )
        format_payload = probe.get("format", {})
        clip_duration_ms = int(float(format_payload.get("duration") or 0) * 1000) or target_duration_ms
        ratio = target_duration_ms / max(clip_duration_ms, 1)
        if 0.92 <= ratio <= 1.08:
            strategy = "speed_adjust"
            args = [
                "-y",
                "-i",
                input_name,
                "-vf",
                f"setpts={ratio:.6f}*PTS",
                "-an",
                "-r",
                "24",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "retimed.mp4",
            ]
        elif target_duration_ms > clip_duration_ms:
            strategy = "freeze_pad"
            pad_seconds = max(0.0, (target_duration_ms - clip_duration_ms) / 1000)
            args = [
                "-y",
                "-i",
                input_name,
                "-vf",
                f"tpad=stop_mode=clone:stop_duration={pad_seconds:.3f}",
                "-an",
                "-r",
                "24",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "retimed.mp4",
            ]
        else:
            strategy = "trim"
            args = [
                "-y",
                "-i",
                input_name,
                "-t",
                f"{target_duration_ms / 1000:.3f}",
                "-an",
                "-r",
                "24",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "retimed.mp4",
            ]
        try:
            runner.run("ffmpeg", args, workdir=workdir)
            metadata = _probe_result(settings, "retimed.mp4", workdir=workdir)
        except FFmpegError:
            return source_bytes, {"duration_ms": target_duration_ms, "timing_alignment_strategy": strategy}
        stream = next(
            (item for item in metadata.get("streams", []) if item.get("codec_type") == "video"),
            {},
        )
        format_out = metadata.get("format", {})
        return (workdir / "retimed.mp4").read_bytes(), {
            "duration_ms": int(float(format_out.get("duration") or 0) * 1000) or target_duration_ms,
            "width": int(stream.get("width") or video_stream.get("width") or 0) or None,
            "height": int(stream.get("height") or video_stream.get("height") or 0) or None,
            "frame_rate": _frame_rate_from_probe(stream) or _frame_rate_from_probe(video_stream),
            "timing_alignment_strategy": strategy,
            "has_audio_stream": False,
        }


_COLOR_FILTER_GRAPHS: dict[str, str] = {
    "warm": "colorbalance=rs=0.1:gs=0.0:bs=-0.1",
    "cool": "colorbalance=rs=-0.1:gs=0.0:bs=0.12",
    "sepia": "colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131",
    "grayscale": "hue=s=0",
    "vintage": "colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131,curves=m='0/0 0.5/0.45 1/0.9'",
    "vibrant": "eq=saturation=1.5:contrast=1.05",
    "moody": "eq=saturation=0.7:contrast=1.15:brightness=-0.05",
}


def apply_video_effects(
    settings: Settings,
    *,
    source_bytes: bytes,
    source_file_name: str,
    brightness: float = 0.0,
    contrast: float = 0.0,
    saturation: float = 0.0,
    speed: float = 1.0,
    fade_in_sec: float = 0.0,
    fade_out_sec: float = 0.0,
    color_filter: str = "none",
    vignette_strength: float = 0.0,
) -> tuple[bytes, dict[str, object]]:
    """Apply video effects using FFmpeg filter chains.

    Parameters use the same range conventions as the frontend:
      brightness/contrast/saturation: -50..50 (0 = no change)
      speed: 0.25..2.0 (1.0 = normal)
      vignette_strength: 0..100 (0 = off)
      color_filter: one of _COLOR_FILTER_GRAPHS keys or "none"
    """
    runner = FFmpegRunner(settings)
    if not runner.available():
        return source_bytes, {"effects_applied": False}

    with tempfile.TemporaryDirectory() as temp_dir:
        workdir = Path(temp_dir)
        ext = Path(source_file_name).suffix or ".mp4"
        (workdir / f"input{ext}").write_bytes(source_bytes)

        video_filters: list[str] = []

        eq_parts: list[str] = []
        if brightness != 0:
            eq_parts.append(f"brightness={brightness / 100:.3f}")
        if contrast != 0:
            eq_parts.append(f"contrast={1 + contrast / 50:.3f}")
        if saturation != 0:
            eq_parts.append(f"saturation={1 + saturation / 50:.3f}")
        if eq_parts:
            video_filters.append(f"eq={':'.join(eq_parts)}")

        if color_filter in _COLOR_FILTER_GRAPHS:
            video_filters.append(_COLOR_FILTER_GRAPHS[color_filter])

        if vignette_strength > 0:
            angle = f"PI/4*{vignette_strength / 100:.2f}"
            video_filters.append(f"vignette=angle={angle}")

        if speed != 1.0 and 0.25 <= speed <= 4.0:
            video_filters.append(f"setpts={1 / speed:.6f}*PTS")

        try:
            probe = _probe_result(settings, f"input{ext}", workdir=workdir)
        except FFmpegError:
            return source_bytes, {"effects_applied": False}

        format_payload = probe.get("format", {})
        total_duration = float(format_payload.get("duration") or 0)

        if fade_in_sec > 0:
            video_filters.append(f"fade=t=in:st=0:d={fade_in_sec:.2f}")
        if fade_out_sec > 0 and total_duration > fade_out_sec:
            fade_start = total_duration - fade_out_sec
            video_filters.append(f"fade=t=out:st={fade_start:.2f}:d={fade_out_sec:.2f}")

        if not video_filters:
            return source_bytes, {"effects_applied": False, "reason": "no_filters"}

        vf_chain = ",".join(video_filters)

        audio_filters: list[str] = []
        if speed != 1.0 and 0.25 <= speed <= 4.0:
            audio_filters.append(f"atempo={speed:.6f}")
        if fade_in_sec > 0:
            audio_filters.append(f"afade=t=in:st=0:d={fade_in_sec:.2f}")
        if fade_out_sec > 0 and total_duration > fade_out_sec:
            fade_start = total_duration - fade_out_sec
            audio_filters.append(f"afade=t=out:st={fade_start:.2f}:d={fade_out_sec:.2f}")

        args = [
            "-y",
            "-i", f"input{ext}",
            "-vf", vf_chain,
        ]
        if audio_filters:
            args.extend(["-af", ",".join(audio_filters)])
        args.extend([
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-preset", "fast",
            "output.mp4",
        ])

        try:
            runner.run("ffmpeg", args, workdir=workdir)
        except FFmpegError:
            return source_bytes, {"effects_applied": False, "reason": "ffmpeg_error"}

        out_probe = _probe_result(settings, "output.mp4", workdir=workdir)
        out_stream = next(
            (s for s in out_probe.get("streams", []) if s.get("codec_type") == "video"),
            {},
        )
        out_format = out_probe.get("format", {})
        return (workdir / "output.mp4").read_bytes(), {
            "effects_applied": True,
            "duration_ms": int(float(out_format.get("duration") or 0) * 1000),
            "width": int(out_stream.get("width") or 0) or None,
            "height": int(out_stream.get("height") or 0) or None,
            "frame_rate": _frame_rate_from_probe(out_stream),
            "filters": vf_chain,
        }


_SLIDE_EFFECTS: dict[str, dict[str, str]] = {
    "ken_burns": {
        "start": "z='min(zoom+0.0015,1.3)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
        "end": "z='if(eq(on,1),1.3,max(zoom-0.0015,1.0))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
    },
    "zoom_in": {
        "start": "z='min(zoom+0.0015,1.3)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
        "end": "z='1.0':x='0':y='0'",
    },
    "zoom_out": {
        "start": "z='if(eq(on,1),1.3,max(zoom-0.0015,1.0))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
        "end": "z='if(eq(on,1),1.3,max(zoom-0.0015,1.0))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
    },
    "pan_left": {
        "start": "z='1.15':x='iw*0.12*(on/max({p},1))':y='ih/2-(ih/zoom/2)'",
        "end": "z='1.15':x='iw*0.12*(on/max({p},1))':y='ih/2-(ih/zoom/2)'",
    },
    "pan_right": {
        "start": "z='1.15':x='iw*0.12*(1-(on/max({p},1)))':y='ih/2-(ih/zoom/2)'",
        "end": "z='1.15':x='iw*0.12*(1-(on/max({p},1)))':y='ih/2-(ih/zoom/2)'",
    },
}


def create_slide_clip_from_images(
    settings: Settings,
    *,
    start_frame_bytes: bytes,
    end_frame_bytes: bytes,
    target_duration_ms: int,
    animation_effect: str = "ken_burns",
    width: int = 1080,
    height: int = 1920,
) -> tuple[bytes, dict[str, object]]:
    """Create an animated slide video clip from two still images.

    Phase 1: start image with Ken Burns / zoom / pan effect (~85% of duration)
    Phase 2: crossfade from start to end (~15% of duration, capped at 0.8 s)
    Phase 3: end image continues its effect (overlaps with phase 2 xfade)

    The output is a silent MP4 at 24 fps with exact duration = target_duration_ms.
    """
    runner = FFmpegRunner(settings)
    duration_s = max(0.5, target_duration_ms / 1000.0)
    xfade_s = min(duration_s * 0.15, 0.8)
    xfade_s = min(xfade_s, duration_s * 0.4)  # clamp for very short clips
    phase1_s = duration_s - xfade_s
    xfade_offset = max(0.0, phase1_s - xfade_s)
    phase1_frames = max(1, int((phase1_s + xfade_s) * 24))
    phase2_frames = max(1, int((duration_s + xfade_s) * 24))

    if not runner.available():
        payload: dict[str, object] = {
            "duration_ms": target_duration_ms,
            "animation_effect": animation_effect,
            "generation_mode": "slide_fallback_manifest",
            "fallback_format": "json",
        }
        import json as _json
        return _json.dumps(payload, indent=2).encode("utf-8"), {
            **payload,
            "has_audio_stream": False,
            "width": width,
            "height": height,
            "frame_rate": 24.0,
        }

    effect_key = animation_effect if animation_effect in _SLIDE_EFFECTS else "ken_burns"
    raw_effect = _SLIDE_EFFECTS[effect_key]
    start_expr = raw_effect["start"].replace("{p}", str(phase1_frames))
    end_expr = raw_effect["end"].replace("{p}", str(phase2_frames))

    scale_pad = (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},setsar=1"
    )
    filter_complex = (
        f"[0:v]{scale_pad},"
        f"zoompan={start_expr}:d={phase1_frames}:s={width}x{height}:fps=24[v0];"
        f"[1:v]{scale_pad},"
        f"zoompan={end_expr}:d={phase2_frames}:s={width}x{height}:fps=24[v1];"
        f"[v0][v1]xfade=transition=fade:duration={xfade_s:.3f}:offset={xfade_offset:.3f},"
        f"format=yuv420p[v]"
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        workdir = Path(temp_dir)
        (workdir / "start.png").write_bytes(start_frame_bytes)
        (workdir / "end.png").write_bytes(end_frame_bytes)
        try:
            runner.run(
                "ffmpeg",
                [
                    "-y",
                    "-loop", "1",
                    "-t", f"{phase1_s + xfade_s:.3f}",
                    "-i", "start.png",
                    "-loop", "1",
                    "-t", f"{duration_s + xfade_s:.3f}",
                    "-i", "end.png",
                    "-filter_complex", filter_complex,
                    "-map", "[v]",
                    "-t", f"{duration_s:.3f}",
                    "-r", "24",
                    "-c:v", "libx264",
                    "-preset", "fast",
                    "-pix_fmt", "yuv420p",
                    "-an",
                    "slide.mp4",
                ],
                workdir=workdir,
            )
            probe = _probe_result(settings, "slide.mp4", workdir=workdir)
        except FFmpegError:
            payload = {
                "duration_ms": target_duration_ms,
                "animation_effect": animation_effect,
                "generation_mode": "slide_ffmpeg_error_fallback",
                "fallback_format": "json",
            }
            import json as _json
            return _json.dumps(payload, indent=2).encode("utf-8"), {
                **payload,
                "has_audio_stream": False,
                "width": width,
                "height": height,
                "frame_rate": 24.0,
            }
        video_stream = next(
            (s for s in probe.get("streams", []) if s.get("codec_type") == "video"),
            {},
        )
        format_payload = probe.get("format", {})
        actual_duration_ms = int(float(format_payload.get("duration") or duration_s) * 1000)
        return (workdir / "slide.mp4").read_bytes(), {
            "duration_ms": actual_duration_ms,
            "has_audio_stream": False,
            "width": int(video_stream.get("width") or width),
            "height": int(video_stream.get("height") or height),
            "frame_rate": _frame_rate_from_probe(video_stream) or 24.0,
            "animation_effect": animation_effect,
            "generation_mode": "slide_ken_burns",
        }


def compose_reel_export(
    settings: Settings,
    *,
    clip_files: list[tuple[str, bytes]],
    narration_files: list[tuple[str, bytes]],
    music_file: tuple[str, bytes] | None,
    subtitle_text: str | None,
) -> tuple[bytes, bytes, dict[str, object]]:
    runner = FFmpegRunner(settings)
    manifest = {
        "clip_count": len(clip_files),
        "narration_count": len(narration_files),
        "has_music": music_file is not None,
        "has_subtitles": bool(subtitle_text),
    }
    if not runner.available():
        manifest_bytes = json.dumps(manifest, indent=2).encode("utf-8")
        return manifest_bytes, manifest_bytes, {"duration_ms": 0, "fallback_manifest": True}

    with tempfile.TemporaryDirectory() as temp_dir:
        workdir = Path(temp_dir)
        clip_paths: list[str] = []
        narration_wavs: list[str] = []
        for index, (name, payload) in enumerate(clip_files, start=1):
            clip_name = f"clip_{index:02d}{Path(name).suffix or '.mp4'}"
            (workdir / clip_name).write_bytes(payload)
            clip_paths.append(clip_name)
        for index, (name, payload) in enumerate(narration_files, start=1):
            input_name = f"narration_src_{index:02d}{Path(name).suffix}"
            output_name = f"narration_{index:02d}.wav"
            (workdir / input_name).write_bytes(payload)
            runner.run(
                "ffmpeg",
                [
                    "-y",
                    "-i",
                    input_name,
                    "-ar",
                    "24000",
                    "-ac",
                    "1",
                    output_name,
                ],
                workdir=workdir,
            )
            narration_wavs.append(output_name)
        (workdir / "clips.txt").write_text(
            "".join(f"file '{clip_path}'\n" for clip_path in clip_paths),
            encoding="utf-8",
        )
        (workdir / "narrations.txt").write_text(
            "".join(f"file '{audio_path}'\n" for audio_path in narration_wavs),
            encoding="utf-8",
        )
        runner.run(
            "ffmpeg",
            [
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                "clips.txt",
                "-an",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "video_track.mp4",
            ],
            workdir=workdir,
        )
        runner.run(
            "ffmpeg",
            [
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                "narrations.txt",
                "-ar",
                "24000",
                "-ac",
                "1",
                "narration_track.wav",
            ],
            workdir=workdir,
        )
        narration_probe = _probe_result(settings, "narration_track.wav", workdir=workdir)
        total_duration_seconds = float((narration_probe.get("format") or {}).get("duration") or 1.0)

        if music_file is not None:
            music_name = f"music_src{Path(music_file[0]).suffix}"
            (workdir / music_name).write_bytes(music_file[1])
            runner.run(
                "ffmpeg",
                [
                    "-y",
                    "-stream_loop",
                    "-1",
                    "-i",
                    music_name,
                    "-t",
                    f"{total_duration_seconds:.3f}",
                    "-ar",
                    "24000",
                    "-ac",
                    "1",
                    "music_loop.wav",
                ],
                workdir=workdir,
            )
            fade_start = max(0.0, total_duration_seconds - 0.3)
            runner.run(
                "ffmpeg",
                [
                    "-y",
                    "-i",
                    "narration_track.wav",
                    "-i",
                    "music_loop.wav",
                    "-filter_complex",
                    (
                        f"[1:a]volume=0.2511886432,afade=t=in:st=0:d=0.3,"
                        f"afade=t=out:st={fade_start:.3f}:d=0.3[music];"
                        "[music][0:a]sidechaincompress=threshold=0.06:ratio=12:attack=5:release=250[ducked];"
                        "[0:a][ducked]amix=inputs=2:normalize=0,loudnorm=I=-14:TP=-1.0:LRA=11[aout]"
                    ),
                    "-map",
                    "[aout]",
                    "final_audio.wav",
                ],
                workdir=workdir,
            )
        else:
            runner.run(
                "ffmpeg",
                [
                    "-y",
                    "-i",
                    "narration_track.wav",
                    "-filter:a",
                    "loudnorm=I=-14:TP=-1.0:LRA=11",
                    "final_audio.wav",
                ],
                workdir=workdir,
            )

        final_args = [
            "-y",
            "-i",
            "video_track.mp4",
            "-i",
            "final_audio.wav",
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
        ]
        if subtitle_text:
            (workdir / "subtitles.srt").write_text(subtitle_text, encoding="utf-8")
            final_args.extend(["-vf", "subtitles=subtitles.srt"])
        final_args.append("final.mp4")
        runner.run("ffmpeg", final_args, workdir=workdir)
        final_probe = _probe_result(settings, "final.mp4", workdir=workdir)
        video_stream = next(
            (
                item
                for item in final_probe.get("streams", [])
                if item.get("codec_type") == "video"
            ),
            {},
        )
        final_manifest = {
            **manifest,
            "duration_seconds": float((final_probe.get("format") or {}).get("duration") or 0.0),
        }
        return (
            (workdir / "final.mp4").read_bytes(),
            json.dumps(final_manifest, indent=2).encode("utf-8"),
            {
                "duration_ms": int(final_manifest["duration_seconds"] * 1000),
                "width": int(video_stream.get("width") or 1080),
                "height": int(video_stream.get("height") or 1920),
                "frame_rate": _frame_rate_from_probe(video_stream),
            },
        )

