"""Safe, user-facing wrappers around FFmpeg commands."""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Sequence


class FFmpegError(RuntimeError):
    """Raised when FFmpeg is unavailable or cannot process a video."""


def ensure_ffmpeg_available() -> None:
    if shutil.which("ffmpeg") is None:
        raise FFmpegError(
            "Video processing is not available on this server. Please contact support."
        )


def run_ffmpeg(command: Sequence[str], action: str) -> None:
    """Run an FFmpeg command and replace technical failures with a safe message."""

    ensure_ffmpeg_available()
    try:
        subprocess.run(
            list(command),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            check=True,
            text=True,
        )
    except subprocess.CalledProcessError as error:
        raise FFmpegError(
            f"We could not {action}. Check that the video is a valid MP4 and try again."
        ) from error
