import os

import psycopg
import pytest

from backend.dependencies import ServiceContainer
from backend.services.database import DatabaseService

# Tests sign their own tokens; production must set a real SECRET_KEY.
os.environ.setdefault("SECRET_KEY", "test-secret-key")

# Tests need a real Postgres (CI starts one as a service container). Locally:
#   docker run -d --name stash-test-db -e POSTGRES_USER=stash -e POSTGRES_PASSWORD=stash \
#     -e POSTGRES_DB=stash_test -p 5433:5432 pgvector/pgvector:pg17
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL", "postgresql://stash:stash@localhost:5433/stash_test"
)


@pytest.fixture(scope="session")
def _test_db_service():
    """Connect once per test session; this also creates the tables."""
    return DatabaseService(dsn=TEST_DATABASE_URL)


@pytest.fixture(autouse=True)
def setup_test_db(_test_db_service):
    """
    Global test database fixture - automatically runs for ALL tests.
    Empties every table so each test starts from a clean database.
    """
    with psycopg.connect(TEST_DATABASE_URL) as conn:
        conn.execute("TRUNCATE saved_videos, users RESTART IDENTITY CASCADE")

    test_db_service = _test_db_service

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
