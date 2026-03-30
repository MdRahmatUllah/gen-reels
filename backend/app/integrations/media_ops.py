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


def build_slideshow_clip(
    settings: Settings,
    *,
    start_image_bytes: bytes,
    start_image_ext: str,
    end_image_bytes: bytes,
    end_image_ext: str,
    duration_ms: int,
    width: int = 1080,
    height: int = 1920,
    fps: int = 24,
    scene_index: int = 0,
) -> tuple[bytes, dict[str, object]]:
    """Build a silent Ken-Burns motion clip from two still images.

    Structure:
      first ~55 %  — start image with slow zoom/pan
      last  ~55 %  — end image with slow zoom/pan
      overlap zone — 0.4-second crossfade rendered via FFmpeg xfade
    Total output duration equals *duration_ms* ± 1 frame.
    """
    runner = FFmpegRunner(settings)
    if not runner.available():
        return b"", {"duration_ms": duration_ms, "fallback": True, "has_audio_stream": False}

    total_sec = max(2.0, duration_ms / 1000.0)
    xfade_dur = min(0.4, total_sec * 0.15)
    half = total_sec / 2.0 + xfade_dur / 2.0
    dur_a = half
    dur_b = half
    offset = dur_a - xfade_dur

    # Rotate between 4 motion styles so adjacent scenes feel different.
    style = scene_index % 4

    def _zoompan_expr(style_index: int, d_frames: int) -> str:
        n_expr = f"n/{d_frames}"
        if style_index == 0:  # slow zoom-in, centred
            z = f"min(1.0+0.12*{n_expr},1.13)"
            x = "iw/2-(iw/zoom/2)"
            y = "ih/2-(ih/zoom/2)"
        elif style_index == 1:  # slow zoom-out, centred
            z = f"max(1.13-0.12*{n_expr},1.0)"
            x = "iw/2-(iw/zoom/2)"
            y = "ih/2-(ih/zoom/2)"
        elif style_index == 2:  # gentle pan right + slight zoom
            z = "1.05"
            x = f"iw/zoom/2*{n_expr}"
            y = "ih/2-(ih/zoom/2)"
        else:  # gentle pan left + slight zoom
            z = "1.05"
            x = f"iw-(iw/zoom/2)-(iw/zoom/2)*{n_expr}"
            y = "ih/2-(ih/zoom/2)"
        return f"zoompan=z='{z}':x='{x}':y='{y}':d={d_frames}:s={width}x{height}:fps={fps}"

    def _scale_pad_filter() -> str:
        return (
            f"scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height}"
        )

    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp)
        start_name = f"start{start_image_ext or '.jpg'}"
        end_name = f"end{end_image_ext or '.jpg'}"
        (workdir / start_name).write_bytes(start_image_bytes)
        (workdir / end_name).write_bytes(end_image_bytes)

        frames_a = max(2, int(dur_a * fps))
        frames_b = max(2, int(dur_b * fps))

        vf_a = f"{_scale_pad_filter()},{_zoompan_expr(style, frames_a)}"
        vf_b = f"{_scale_pad_filter()},{_zoompan_expr((style + 2) % 4, frames_b)}"

        try:
            runner.run(
                "ffmpeg",
                [
                    "-y", "-loop", "1", "-framerate", str(fps),
                    "-i", start_name,
                    "-vf", vf_a,
                    "-t", f"{dur_a:.4f}",
                    "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-preset", "fast",
                    "part_a.mp4",
                ],
                workdir=workdir,
            )
            runner.run(
                "ffmpeg",
                [
                    "-y", "-loop", "1", "-framerate", str(fps),
                    "-i", end_name,
                    "-vf", vf_b,
                    "-t", f"{dur_b:.4f}",
                    "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-preset", "fast",
                    "part_b.mp4",
                ],
                workdir=workdir,
            )
            runner.run(
                "ffmpeg",
                [
                    "-y",
                    "-i", "part_a.mp4",
                    "-i", "part_b.mp4",
                    "-filter_complex",
                    (
                        f"[0:v][1:v]xfade=transition=fade"
                        f":duration={xfade_dur:.4f}"
                        f":offset={offset:.4f}[vout]"
                    ),
                    "-map", "[vout]",
                    "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-preset", "fast",
                    "slideshow.mp4",
                ],
                workdir=workdir,
            )
            probe = _probe_result(settings, "slideshow.mp4", workdir=workdir)
        except FFmpegError:
            return b"", {"duration_ms": duration_ms, "fallback": True, "has_audio_stream": False}

        video_stream = next(
            (s for s in probe.get("streams", []) if s.get("codec_type") == "video"),
            {},
        )
        fmt = probe.get("format", {})
        actual_duration_ms = int(float(fmt.get("duration") or total_sec) * 1000)
        return (workdir / "slideshow.mp4").read_bytes(), {
            "duration_ms": actual_duration_ms,
            "width": int(video_stream.get("width") or width),
            "height": int(video_stream.get("height") or height),
            "frame_rate": _frame_rate_from_probe(video_stream),
            "has_audio_stream": False,
            "slideshow_style": style,
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

