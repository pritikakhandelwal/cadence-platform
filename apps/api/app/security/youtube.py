"""YouTube reference-video ingestion.

Lets a user paste a YouTube link for the professional reference video
instead of uploading a file. Downloading third-party YouTube content
server-side to compare against a user's own dance sits in a real
copyright/ToS gray area -- YouTube's ToS generally restricts
downloading outside their own offline feature. Built anyway (many
"practice against a reference" apps operate in this same space for
personal use), but scoped deliberately narrow to reduce the exposure
and to avoid this becoming a general-purpose URL-fetching endpoint (a
classic SSRF vector): only youtube.com/youtu.be hosts are accepted --
never an arbitrary URL -- and the same duration/size limits as a
direct upload apply. See docs/decisions.md.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

MAX_DURATION_SECONDS = 5 * 60  # matches video_validation.MAX_DURATION_SECONDS
MAX_BYTES = 250 * 1024 * 1024  # matches video_validation.MAX_UPLOAD_BYTES

_ALLOWED_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "www.youtu.be"}


class YouTubeDownloadError(ValueError):
    """Raised when a YouTube URL can't be safely accepted or downloaded."""


def _validate_host(url: str) -> None:
    try:
        parsed = urlparse(url)
    except ValueError as error:
        raise YouTubeDownloadError("That doesn't look like a valid URL.") from error

    # urlparse extracts a hostname regardless of scheme, so
    # "ftp://youtube.com/..." has hostname "youtube.com" too -- the
    # host allowlist alone isn't enough. Found by a test that used a
    # real youtube.com URL and didn't mock the downloader: the scheme
    # check was missing, but https was assumed throughout, so it went
    # unnoticed until a non-http(s) scheme was actually tried.
    if parsed.scheme not in ("http", "https"):
        raise YouTubeDownloadError("Only http/https YouTube links are supported.")

    host = (parsed.hostname or "").lower()
    if host not in _ALLOWED_HOSTS:
        raise YouTubeDownloadError("Only youtube.com / youtu.be links are supported.")


def download_youtube_video(url: str, destination: Path) -> None:
    """Downloads `url` to `destination` (should end in .mp4), rejecting
    anything not from YouTube and anything over the platform's normal
    duration/size limits *before* downloading the whole thing. Raises
    YouTubeDownloadError with a human-readable reason on any failure.
    """

    _validate_host(url)

    import yt_dlp

    ydl_opts = {
        "format": "mp4/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]",
        "outtmpl": str(destination),
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "max_filesize": MAX_BYTES,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            duration = info.get("duration")
            if duration is not None and duration > MAX_DURATION_SECONDS:
                raise YouTubeDownloadError(
                    f"That video is about {int(duration // 60)} minutes long; "
                    f"please use one under {MAX_DURATION_SECONDS // 60} minutes."
                )
            ydl.download([url])
    except YouTubeDownloadError:
        raise
    except yt_dlp.utils.DownloadError as error:
        raise YouTubeDownloadError(
            "Could not download that YouTube video. Check the link and try again."
        ) from error

    if not destination.is_file():
        raise YouTubeDownloadError("Could not download that YouTube video. Check the link and try again.")
