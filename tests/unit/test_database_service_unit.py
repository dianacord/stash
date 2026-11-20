import psycopg
import pytest

from backend.services.database import DatabaseService


def test_get_user_videos_handles_exception(monkeypatch):
    # Avoid DB init touching disk
    monkeypatch.setattr(DatabaseService, "_init_database", lambda self: None)

    # Create instance with no-op init
    db = DatabaseService(dsn="postgresql://unused")

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
            raise psycopg.errors.UniqueViolation("duplicate")

    class DummyConn:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, *args, **kwargs):
            return DummyCursor().execute(*args, **kwargs)

    monkeypatch.setattr(DatabaseService, "_connect", lambda self: DummyConn())

    db = DatabaseService(dsn="postgresql://unused")

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


def test_ping_returns_false_when_database_is_down(monkeypatch):
    monkeypatch.setattr(DatabaseService, "_init_database", lambda self: None)
    db = DatabaseService(dsn="postgresql://unused")

    def raise_connect(self):
        raise psycopg.OperationalError("connection refused")

    monkeypatch.setattr(DatabaseService, "_connect", raise_connect)

    assert db.ping() is False


def test_missing_database_url_fails_loudly(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        DatabaseService()
