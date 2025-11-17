"""Business logic layer for video operations.

Separates business logic from HTTP handling, following Single Responsibility Principle.
"""

from backend.protocols import Summarizer, VideoFetcher, VideoRepository


class VideoService:
    """Service for handling video-related business logic."""

    def __init__(
        self,
        fetcher: VideoFetcher,
        repository: VideoRepository,
        summarizer: Summarizer | None = None,
    ):
        """
        Initialize video service with dependencies.

        Args:
            fetcher: Video transcript fetcher (e.g., YouTubeFetcher)
            repository: Video data storage (e.g., DatabaseService)
            summarizer: Optional AI summarizer (e.g., GroqSummarizer)
        """
        self.fetcher = fetcher
        self.repository = repository
        self.summarizer = summarizer

    def save_video(self, url: str, user_id: int) -> dict:
        """
        Save a video transcript with optional AI summary.

        Args:
            url: Video URL
            user_id: ID of the user saving the video

        Returns:
            dict with success status and data/error
        """
        # Extract video ID and check if already exists
        video_id = self.fetcher.extract_video_id(url)
        existing = self.repository.get_video_by_id(video_id)

        if existing:
            return {"success": True, "message": "Video already exists", "data": existing}

        # Fetch transcript
        transcript_result = self.fetcher.get_transcript(url)

        if not transcript_result["success"]:
            return {
                "success": False,
                "error": transcript_result["error"],
                "error_type": transcript_result.get("error_type"),
            }

        # Generate AI summary if summarizer available
        ai_summary = None
        if self.summarizer:
            summary_result = self.summarizer.summarize(transcript_result["transcript"])
            if summary_result["success"]:
                ai_summary = summary_result["summary"]
            else:
                # Log but don't fail - summary is optional
                print(f"Warning: Failed to generate summary - {summary_result.get('error')}")

        # Prepare video data
        video_data = {
            "url": url,
            "video_id": transcript_result["video_id"],
            "raw_transcript": transcript_result["transcript"],
            "ai_summary": ai_summary,
            "language": transcript_result.get("language"),
            "is_generated": transcript_result.get("is_generated"),
            "segments_count": transcript_result["segments_count"],
            "platform": "youtube",
        }

        # Save to repository
        return self.repository.save_video(video_data, user_id)

    def get_user_videos(self, user_id: int) -> list[dict]:
        """Get all videos for a specific user."""
        return self.repository.get_user_videos(user_id)

    def get_video(self, video_id: str, user_id: int) -> dict | None:
        """
        Get video by ID, ensuring it belongs to the user.

        Args:
            video_id: Video ID to retrieve
            user_id: ID of requesting user

        Returns:
            Video dict if found and belongs to user, None otherwise
        """
        video = self.repository.get_video_by_id(video_id)
        if video and video.get("user_id") == user_id:
            return video
        return None

    def delete_video(self, video_id: str, user_id: int) -> dict:
        """
        Delete video, ensuring it belongs to the user.

        Args:
            video_id: Video ID to delete
            user_id: ID of requesting user

        Returns:
            dict with success status and error if applicable
        """
        video = self.repository.get_video_by_id(video_id)
        if not video:
            return {"success": False, "error": "Video not found"}

        if video.get("user_id") != user_id:
            return {"success": False, "error": "Access denied"}

        return self.repository.delete_video(video_id)

    def update_video(self, video_id: str, user_id: int, updates: dict) -> dict:
        """
        Update video, ensuring it belongs to the user.

        Args:
            video_id: Video ID to update
            user_id: ID of requesting user
            updates: Fields to update

        Returns:
            dict with success status and updated data or error
        """
        video = self.repository.get_video_by_id(video_id)
        if not video:
            return {"success": False, "error": "Video not found"}

        if video.get("user_id") != user_id:
            return {"success": False, "error": "Access denied"}

        return self.repository.update_video(video_id, updates)
