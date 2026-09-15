"""Tests for modules.video_validation — including magic-bytes check."""

import unittest

import pytest
from modules.video_validation import VideoValidationError, validate_uploaded_video


class _FakeUpload:
    """Minimal stand-in for a Streamlit UploadedFile."""

    def __init__(self, name: str, data: bytes):
        self.name = name
        self._data = data
        self.size = len(data)

    def getbuffer(self):
        return memoryview(self._data)


def _mp4_header(ftyp_brand: bytes = b"isom") -> bytes:
    """Return a minimal valid ISO Base Media File Format header."""
    # box size (4 bytes) | 'ftyp' (4 bytes) | major_brand (4 bytes) | ...
    box = b"\x00\x00\x00\x18" + b"ftyp" + ftyp_brand + b"\x00\x00\x00\x00" + b"isom" + b"iso2"
    # Pad to a few hundred bytes so size > 0 check passes
    return box + b"\x00" * 200


class MagicBytesTests(unittest.TestCase):

    def test_valid_mp4_magic_bytes_accepted(self):
        upload = _FakeUpload("dance.mp4", _mp4_header())
        # Should not raise
        validate_uploaded_video(upload)

    def test_renamed_non_mp4_rejected_by_magic_bytes(self):
        # A ZIP file renamed to .mp4 — starts with PK\x03\x04
        zip_data = b"PK\x03\x04" + b"\x00" * 200
        upload = _FakeUpload("dance.mp4", zip_data)
        with self.assertRaises(VideoValidationError):
            validate_uploaded_video(upload)

    def test_wrong_extension_rejected(self):
        upload = _FakeUpload("dance.avi", _mp4_header())
        with self.assertRaises(VideoValidationError):
            validate_uploaded_video(upload)

    def test_empty_file_rejected(self):
        upload = _FakeUpload("dance.mp4", b"")
        with self.assertRaises(VideoValidationError):
            validate_uploaded_video(upload)

    def test_oversized_file_rejected(self):
        big = _mp4_header() + b"\x00" * (251 * 1024 * 1024)
        upload = _FakeUpload("dance.mp4", big)
        with self.assertRaises(VideoValidationError):
            validate_uploaded_video(upload)
