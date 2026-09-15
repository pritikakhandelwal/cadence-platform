from __future__ import annotations

import subprocess

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.main import app


@pytest.fixture()
def db_engine(tmp_path):
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


@pytest.fixture()
def client(db_session, tmp_path, monkeypatch):
    from app.rate_limit import login_rate_limit, register_rate_limit

    login_rate_limit._hits.clear()
    register_rate_limit._hits.clear()

    monkeypatch.setenv("CADENCE_RUNTIME_DIR", str(tmp_path / "runtime"))
    with TestClient(app) as test_client:
        yield test_client


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
