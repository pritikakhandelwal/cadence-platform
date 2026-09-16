from __future__ import annotations

import pytest
from cadence_db import Analysis, Base, LoginSecurity, User, UserSession
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture()
def db_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


def test_user_round_trips(db_session):
    user = User(name="Ada", email="ada@example.com", password_hash="hash")
    db_session.add(user)
    db_session.commit()

    fetched = db_session.get(User, user.id)
    assert fetched.email == "ada@example.com"


def test_analysis_defaults_to_queued_with_no_result(db_session):
    user = User(name="Ada", email="ada@example.com", password_hash="hash")
    db_session.add(user)
    db_session.commit()

    analysis = Analysis(user_id=user.id, workspace_id="ws1")
    db_session.add(analysis)
    db_session.commit()

    fetched = db_session.get(Analysis, analysis.id)
    assert fetched.status == "queued"
    assert fetched.result is None
    assert fetched.pending_lock_data is None


def test_analysis_can_store_a_result_and_pending_lock_data(db_session):
    user = User(name="Ada", email="ada@example.com", password_hash="hash")
    db_session.add(user)
    db_session.commit()

    analysis = Analysis(
        user_id=user.id,
        workspace_id="ws1",
        status="needs_dancer_pick",
        pending_lock_data={"detections": [{"frame_idx": 0}], "fps": 30.0, "total_frames": 100},
    )
    db_session.add(analysis)
    db_session.commit()

    fetched = db_session.get(Analysis, analysis.id)
    assert fetched.pending_lock_data["fps"] == 30.0


def test_login_security_and_session_tables_exist(db_session):
    db_session.add(LoginSecurity(email="ada@example.com", failed_attempts=1))
    db_session.commit()

    row = db_session.get(LoginSecurity, "ada@example.com")
    assert row.failed_attempts == 1
