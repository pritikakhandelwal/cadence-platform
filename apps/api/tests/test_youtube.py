from __future__ import annotations

import pytest

from app.security.youtube import YouTubeDownloadError, _validate_host


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=fake-test-id",
        "https://youtube.com/watch?v=fake-test-id",
        "https://m.youtube.com/watch?v=fake-test-id",
        "https://youtu.be/fake-test-id",
        "http://www.youtu.be/fake-test-id",
    ],
)
def test_accepts_real_youtube_hosts(url):
    _validate_host(url)  # should not raise


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/video.mp4",
        "https://vimeo.com/12345",
        "https://youtube.com.evil.example/watch?v=x",  # lookalike host, not youtube.com
        "https://notyoutube.com/watch?v=x",
        "ftp://youtube.com/video",
        "file:///etc/passwd",
        "http://169.254.169.254/latest/meta-data/",  # SSRF-style internal address
        "not a url at all",
        "",
    ],
)
def test_rejects_everything_else(url):
    with pytest.raises(YouTubeDownloadError):
        _validate_host(url)
