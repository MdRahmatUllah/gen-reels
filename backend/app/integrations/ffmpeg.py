from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from app.core.config import Settings


class FFmpegError(RuntimeError):
    pass


class FFmpegRunner:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _local_binary(self, tool: str) -> str | None:
        configured = self.settings.ffmpeg_bin if tool == "ffmpeg" else self.settings.ffprobe_bin
        resolved = shutil.which(configured)
        if resolved:
            return resolved
        return None

    @staticmethod
    def _docker_available() -> bool:
        return shutil.which("docker") is not None

    def available(self) -> bool:
        return self._local_binary("ffmpeg") is not None or self._docker_available()

    def _command(self, tool: str, args: list[str], workdir: Path) -> list[str]:
        local_binary = self._local_binary(tool)
        if local_binary is not None:
            return [local_binary, *args]
        if not self._docker_available():
            raise FFmpegError(f"{tool} is not available locally and Docker fallback is unavailable.")
        return [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{workdir.resolve()}:/workspace",
            "-w",
            "/workspace",
            "--entrypoint",
            tool,
            self.settings.ffmpeg_docker_image,
            *args,
        ]

    def run(self, tool: str, args: list[str], *, workdir: Path) -> subprocess.CompletedProcess[str]:
        command = self._command(tool, args, workdir)
        completed = subprocess.run(
            command,
            cwd=str(workdir),
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            stderr = completed.stderr.strip() or completed.stdout.strip()
            raise FFmpegError(stderr or f"{tool} command failed.")
        return completed

    def probe(self, input_file: str, *, workdir: Path) -> dict[str, object]:
        completed = self.run(
            "ffprobe",
            [
                "-v",
                "error",
                "-print_format",
                "json",
                "-show_streams",
                "-show_format",
                input_file,
            ],
            workdir=workdir,
        )
        return json.loads(completed.stdout or "{}")
