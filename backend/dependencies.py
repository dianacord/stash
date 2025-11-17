"""Dependency injection container for the application.

Provides centralized service initialization and dependency management.
"""

from backend.services.database import DatabaseService
from backend.services.groq_summarizer import GroqSummarizer
from backend.services.user_service import AuthService
from backend.services.video_service import VideoService
from backend.services.youtube_fetcher import YouTubeFetcher


class ServiceContainer:
    """Container for managing application services and their dependencies."""

    def __init__(self):
        """Initialize services with proper dependency injection."""
        # Infrastructure layer
        self._db_service = DatabaseService()
        self._youtube_fetcher = YouTubeFetcher()

        # Optional services
        try:
            self._groq_summarizer = GroqSummarizer()
        except Exception as e:
            print(f"Warning: GroqSummarizer not available: {e}")
            self._groq_summarizer = None

        # Business logic layer
        self._video_service = VideoService(
            fetcher=self._youtube_fetcher,
            repository=self._db_service,
            summarizer=self._groq_summarizer,
        )

        self._auth_service = AuthService(user_repository=self._db_service)

    @property
    def video_service(self) -> VideoService:
        """Get video service instance."""
        return self._video_service

    @property
    def auth_service(self) -> AuthService:
        """Get auth service instance."""
        return self._auth_service

    @property
    def db_service(self) -> DatabaseService:
        """Get database service (for backward compatibility with tests)."""
        return self._db_service

    @property
    def summarizer_available(self) -> bool:
        """Check if summarizer is available."""
        return self._groq_summarizer is not None


# Global container instance
_container: ServiceContainer | None = None


def get_container() -> ServiceContainer:
    """Get or create the global service container."""
    global _container
    if _container is None:
        _container = ServiceContainer()
    return _container


def get_video_service() -> VideoService:
    """FastAPI dependency for video service."""
    return get_container().video_service


def get_auth_service() -> AuthService:
    """FastAPI dependency for auth service."""
    return get_container().auth_service
