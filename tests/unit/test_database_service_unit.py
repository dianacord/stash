import sqlite3

import pytest

from backend.services.database import DatabaseService


def test_get_user_videos_handles_exception(monkeypatch):
    # Avoid DB init touching disk
    monkeypatch.setattr(DatabaseService, "_init_database", lambda self: None)

    # Create instance with no-op init
    db = DatabaseService(db_path=":memory:")

    # Force _connect to raise to simulate DB outage
    def raise_connect(self):  # pragma: no cover - tiny utility
        raise Exception("DB down")

    monkeypatch.setattr(DatabaseService, "_connect", raise_connect)

    out = db.get_user_videos(user_id=1)
    assert out == []


def test_save_video_integrity_error_is_mapped(monkeypatch):
    # Avoid DB init
    monkeypatch.setattr(DatabaseService, "_init_database", lambda self: None)

    class DummyCursor:
        def execute(self, *args, **kwargs):
            raise sqlite3.IntegrityError("duplicate")

        @property
        def lastrowid(self):
            return 1

    class DummyConn:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def cursor(self):
            return DummyCursor()

    monkeypatch.setattr(DatabaseService, "_connect", lambda self: DummyConn())

    db = DatabaseService(db_path=":memory:")

    res = db.save_video(
        {
            "url": "u",
            "video_id": "vid",
            "raw_transcript": "rt",
            "segments_count": 1,
        },
        user_id=1,
    )

    assert res["success"] is False
    assert "already exists" in res["error"].lower()
