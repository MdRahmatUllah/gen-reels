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

