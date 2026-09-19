from __future__ import annotations

import os
import subprocess

import pytest
from cadence_db import Base, get_db
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.queue import get_queue


@pytest.fixture()
def db_engine(tmp_path):
    """SQLite by default. Set CADENCE_TEST_DATABASE_URL (e.g.
    postgresql+psycopg2://user:pass@localhost/dbname) to run the whole suite
    against another database -- the models are meant to be dialect-agnostic,
    and this is how that claim gets checked against a real Postgres. The
    schema is dropped and recreated around every test, so point it at a
    database you don't care about."""

    url = os.getenv("CADENCE_TEST_DATABASE_URL")
    if url:
        engine = create_engine(url)
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        yield engine
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
        return

    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(db_engine):
    TestingSessionLocal = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    session = TestingSessionLocal()

    def override_get_db():
        s = TestingSessionLocal()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override_get_db
    yield session
    session.close()
    app.dependency_overrides.clear()


class FakeQueue:
    """Stands in for the real arq pool -- this repo has no live Redis to
    test against (no Docker in this dev environment). Records what
    would have been enqueued so tests can assert on it; see
    STATUS.md's Phase 2 section for what "actually enqueued through a
    real queue" would still need to be verified."""

    def __init__(self) -> None:
        self.enqueued: list[dict] = []

    async def enqueue_job(self, function: str, *args, **kwargs) -> None:
        self.enqueued.append({"function": function, "args": args, "kwargs": kwargs})


@pytest.fixture()
def fake_queue():
    return FakeQueue()


@pytest.fixture()
def client(db_session, fake_queue, tmp_path, monkeypatch):
    from app.rate_limit import login_rate_limit, register_rate_limit

    login_rate_limit._hits.clear()
    register_rate_limit._hits.clear()

    async def override_get_queue():
        yield fake_queue

    app.dependency_overrides[get_queue] = override_get_queue

    monkeypatch.setenv("CADENCE_RUNTIME_DIR", str(tmp_path / "runtime"))
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def _no_real_youtube_downloads(monkeypatch):
    """Safety net: makes any test that reaches the real YouTube
    downloader fail loudly and fast instead of silently making a real
    network call. Added after a test-logic bug (not a bug in the
    endpoint itself) let a request that should have been rejected
    reach download_youtube_video for real -- it downloaded an actual
    229MB video from a real youtube.com URL during a supposedly
    offline test run. Tests that want the success path (or a specific
    failure) still explicitly monkeypatch this again inside the test
    body, which simply overrides this default within that test."""

    import app.routers.analyses as analyses_module

    def _fail(url: str, destination) -> None:
        raise AssertionError(
            "A test reached the real download_youtube_video without mocking it -- "
            "this would have made a real network call to YouTube. Monkeypatch "
            "app.routers.analyses.download_youtube_video in this test."
        )

    monkeypatch.setattr(analyses_module, "download_youtube_video", _fail)


@pytest.fixture(scope="session")
def tiny_mp4_bytes(tmp_path_factory) -> bytes:
    """A ~1-second, tiny, valid MP4 generated with ffmpeg -- avoids
    checking real video fixtures into the repo just to test upload
    validation."""

    out_path = tmp_path_factory.mktemp("fixtures") / "tiny.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=32x32:d=1:r=5",
            "-pix_fmt", "yuv420p", str(out_path),
        ],
        capture_output=True,
        check=True,
    )
    return out_path.read_bytes()
