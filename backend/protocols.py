"""Protocol definitions for dependency inversion.

These define the contracts that implementations must follow,
enabling easy swapping of implementations and better testability.
"""

from typing import Protocol


class VideoFetcher(Protocol):
    """Protocol for fetching video transcripts from various platforms."""

    def extract_video_id(self, url: str) -> str:
        """Extract video ID from URL."""
        ...

    def get_transcript(self, url: str) -> dict:
        """
        Fetch transcript for the given URL.

        Returns dict with:
        - success: bool
        - video_id: str | None
        - transcript: str (on success)
        - segments_count: int (on success)
        - language: str | None
        - is_generated: bool | None
        - error, error_type (on failure)
        """
        ...

    def can_handle(self, url: str) -> bool:
        """Check if this fetcher can handle the given URL."""
        ...


class TranscriptClient(Protocol):
    """Protocol for a YouTube transcript client.

    Abstracts the underlying `youtube-transcript-api` to enable
    dependency inversion and easier testing/mocking.
    """

    def fetch(self, video_id: str, languages: list[str]) -> object:
        """Return a transcript payload for the given video id.

        Implementations may return a library-specific object or a list of
        dicts; the service will normalize the shape.
        """
        ...


class Summarizer(Protocol):
    """Protocol for AI-powered text summarization."""

    def summarize(self, transcript: str, max_length: int = 12000) -> dict:
        """
        Generate summary from transcript.

        Returns dict with:
        - success: bool
        - summary: str (on success)
        - error: str (on failure)
        """
        ...


class VideoRepository(Protocol):
    """Protocol for video data persistence."""

    def save_video(self, video_data: dict, user_id: int) -> dict:
        """Save video to storage."""
        ...

    def get_video_by_id(self, video_id: str) -> dict | None:
        """Retrieve video by ID."""
        ...

    def get_user_videos(self, user_id: int) -> list[dict]:
        """Get all videos for a user."""
        ...

    def delete_video(self, video_id: str) -> dict:
        """Delete video by ID."""
        ...

    def update_video(self, video_id: str, updates: dict) -> dict:
        """Update video fields."""
        ...


class UserRepository(Protocol):
    """Protocol for user data persistence."""

    def create_user(self, username: str, hashed_password: str) -> dict:
        """Create a new user."""
        ...

    def get_user_by_username(self, username: str) -> dict | None:
        """Get user by username."""
        ...

    def get_user_by_id(self, user_id: int) -> dict | None:
        """Get user by ID."""
        ...
