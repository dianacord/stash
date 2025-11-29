import os
import sqlite3

import pytest

from backend.dependencies import ServiceContainer
from backend.services.database import DatabaseService


@pytest.fixture(autouse=True)
def setup_test_db():
    """
    Global test database fixture - automatically runs for ALL tests.
    Creates fresh test database with users and saved_videos tables.
    """
    test_db_path = "test_global.db"

    # Create test database
    conn = sqlite3.connect(test_db_path)
    cursor = conn.cursor()

    # Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create saved_videos table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS saved_videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            video_id TEXT NOT NULL UNIQUE,
            platform TEXT DEFAULT 'youtube',
            title TEXT,
            raw_transcript TEXT,
            ai_summary TEXT,
            language TEXT,
            is_generated BOOLEAN,
            segments_count INTEGER,
            user_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()

    # Create test service container with test database
    test_db_service = DatabaseService(db_path=test_db_path)

    # Replace global container with test container
    from backend import dependencies

    original_container = dependencies._container

    # Create test container
    test_container = ServiceContainer.__new__(ServiceContainer)
    test_container._db_service = test_db_service

    # Initialize other services
    from backend.services.youtube_fetcher import YouTubeFetcher

    test_container._youtube_fetcher = YouTubeFetcher()

    try:
        from backend.services.groq_summarizer import GroqSummarizer

        test_container._groq_summarizer = GroqSummarizer()
    except Exception:
        test_container._groq_summarizer = None

    # Initialize service layer
    from backend.services.user_service import AuthService
    from backend.services.video_service import VideoService

    test_container._video_service = VideoService(
        fetcher=test_container._youtube_fetcher,
        repository=test_container._db_service,
        summarizer=test_container._groq_summarizer,
    )

    test_container._auth_service = AuthService(user_repository=test_container._db_service)

    # Initialize monitoring layer
    from backend.metrics import MetricsService

    test_container._metrics_service = MetricsService()

    # Replace global container
    dependencies._container = test_container

    yield test_db_service

    # Restore original container
    dependencies._container = original_container

    # Cleanup after all tests
    if os.path.exists(test_db_path):
        os.remove(test_db_path)


@pytest.fixture
def test_db(setup_test_db):
    """Alias for tests that explicitly request test_db"""
    return setup_test_db


@pytest.fixture
def sample_video_data():
    """Sample video data for testing"""
    return {
        "url": "https://www.youtube.com/watch?v=test123",
        "video_id": "test123",
        "raw_transcript": "This is a test transcript",
        "language": "English",
        "is_generated": True,
        "segments_count": 10,
        "platform": "youtube",
        "ai_summary": "Test summary",
    }
