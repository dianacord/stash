from unittest.mock import Mock, patch

from backend.services.youtube_fetcher import YouTubeFetcher


def test_get_transcript_success_with_mocked_api_list_payload():
    # Mock YouTubeTranscriptApi instance used in YouTubeFetcher.__init__
    with patch("backend.services.youtube_fetcher.YouTubeTranscriptApi") as mock_api_cls:
        mock_api = Mock()
        # Simulate fetch returning classic list-of-dicts payload
        mock_api.fetch.return_value = [{"text": "Hello"}, {"text": "world"}]
        mock_api_cls.return_value = mock_api

        fetcher = YouTubeFetcher()
        result = fetcher.get_transcript("https://www.youtube.com/watch?v=abc123")

        assert result["success"] is True
        assert result["video_id"] == "abc123"
        assert result["transcript"] == "Hello world"
        assert result["segments_count"] == 2


def test_get_transcript_success_with_mocked_snippets_object():
    class Snippet:
        def __init__(self, text):
            self.text = text

    class Payload:
        def __init__(self):
            self.snippets = [Snippet("One"), Snippet("two"), Snippet("three")]
            self.language = "en"
            self.is_generated = True

    with patch("backend.services.youtube_fetcher.YouTubeTranscriptApi") as mock_api_cls:
        mock_api = Mock()
        mock_api.fetch.return_value = Payload()
        mock_api_cls.return_value = mock_api

        fetcher = YouTubeFetcher()
        result = fetcher.get_transcript("https://www.youtube.com/watch?v=qwerty")

        assert result["success"] is True
        assert result["video_id"] == "qwerty"
        assert result["transcript"] == "One two three"
        assert result["segments_count"] == 3
        assert result["language"] == "en"
        assert result["is_generated"] is True
