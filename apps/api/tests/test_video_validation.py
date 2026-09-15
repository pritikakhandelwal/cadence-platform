from __future__ import annotations

import io

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

from app.security.video_validation import (
    VideoValidationError,
    validate_saved_video,
    validate_uploaded_video,
)


def _upload(filename: str, content: bytes) -> UploadFile:
    return UploadFile(filename=filename, file=io.BytesIO(content), headers=Headers({}))


@pytest.mark.anyio
async def test_rejects_non_mp4_extension():
    upload = _upload("clip.mov", b"whatever")
    with pytest.raises(VideoValidationError, match="Upload an MP4"):
        await validate_uploaded_video(upload)


@pytest.mark.anyio
async def test_rejects_empty_file():
    upload = _upload("clip.mp4", b"")
    with pytest.raises(VideoValidationError, match="empty"):
        await validate_uploaded_video(upload)


@pytest.mark.anyio
async def test_rejects_file_missing_mp4_magic_bytes():
    upload = _upload("clip.mp4", b"not-actually-an-mp4-file-but-has-some-bytes")
    with pytest.raises(VideoValidationError, match="does not appear to be a valid MP4"):
        await validate_uploaded_video(upload)


@pytest.mark.anyio
async def test_accepts_a_real_tiny_mp4(tiny_mp4_bytes):
    upload = _upload("clip.mp4", tiny_mp4_bytes)
    await validate_uploaded_video(upload)  # should not raise


def test_validate_saved_video_rejects_missing_file(tmp_path):
    with pytest.raises(VideoValidationError, match="could not be saved"):
        validate_saved_video(tmp_path / "does-not-exist.mp4")


def test_validate_saved_video_accepts_real_file(tmp_path, tiny_mp4_bytes):
    path = tmp_path / "clip.mp4"
    path.write_bytes(tiny_mp4_bytes)
    validate_saved_video(path)  # should not raise


@pytest.fixture
def anyio_backend():
    return "asyncio"
