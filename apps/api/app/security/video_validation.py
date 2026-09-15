"""Validation for uploaded dance videos.

Ported from legacy/cadence-streamlit/modules/video_validation.py. The
size/magic-byte/duration/codec rules are unchanged; only the upload
object changed, from Streamlit's UploadedFile (sync, .getbuffer()) to
FastAPI's UploadFile (async, .read()/.seek()).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from fastapi import UploadFile

MAX_UPLOAD_BYTES = 250 * 1024 * 1024
MAX_DURATION_SECONDS = 5 * 60
ALLOWED_SUFFIXES = {".mp4"}

# MP4 / ISO Base Media File Format: bytes 4-7 of the file contain "ftyp"
_MP4_MAGIC_OFFSET = 4
_MP4_MAGIC = b"ftyp"


class VideoValidationError(ValueError):
    """Raised when a video cannot safely be accepted for analysis."""


async def _check_mp4_magic_bytes(upload: UploadFile) -> bool:
    header_region = await upload.read(_MP4_MAGIC_OFFSET + len(_MP4_MAGIC))
    await upload.seek(0)
    header = header_region[_MP4_MAGIC_OFFSET : _MP4_MAGIC_OFFSET + len(_MP4_MAGIC)]
    return header == _MP4_MAGIC


async def validate_uploaded_video(upload: UploadFile) -> None:
    """Validate filename, magic bytes, and size before writing to disk."""

    name = upload.filename or ""
    suffix = Path(name).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise VideoValidationError("Upload an MP4 video.")

    size = upload.size
    if size is None:
        body = await upload.read()
        size = len(body)
        await upload.seek(0)

    if not isinstance(size, int) or size <= 0:
        raise VideoValidationError("The uploaded video is empty or could not be read.")
    if size > MAX_UPLOAD_BYTES:
        raise VideoValidationError("Each video must be 250 MB or smaller.")

    if not await _check_mp4_magic_bytes(upload):
        raise VideoValidationError(
            "The uploaded file does not appear to be a valid MP4. "
            "Please export your video as a standard MP4 and try again."
        )


def validate_saved_video(path: str | Path) -> None:
    """Use ffprobe to confirm the upload is a readable, short video."""

    video_path = Path(path)
    if not video_path.is_file():
        raise VideoValidationError("The uploaded video could not be saved. Please try again.")
    if shutil.which("ffprobe") is None:
        raise VideoValidationError(
            "Video validation is unavailable on this server. Please contact support."
        )

    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration:stream=codec_type,width,height",
        "-of",
        "json",
        str(video_path),
    ]
    try:
        result = subprocess.run(command, capture_output=True, check=True, text=True)
        metadata = json.loads(result.stdout)
        duration = float(metadata["format"]["duration"])
    except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        raise VideoValidationError(
            "This video cannot be read. Export it as a standard MP4 and try again."
        ) from error

    if duration <= 0:
        raise VideoValidationError("The uploaded video has no playable content.")
    if duration > MAX_DURATION_SECONDS:
        raise VideoValidationError("Each video must be five minutes or shorter.")

    video_streams = [s for s in metadata.get("streams", []) if s.get("codec_type") == "video"]
    if not video_streams:
        raise VideoValidationError("The uploaded file does not contain a video stream.")
