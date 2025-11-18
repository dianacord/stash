import pytest

from backend.services.youtube_fetcher import YouTubeFetcher


def test_extract_video_id_standard_url():
    """Test extracting video ID from standard YouTube URL"""
    fetcher = YouTubeFetcher()
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    video_id = fetcher.extract_video_id(url)
    assert video_id == "dQw4w9WgXcQ"


def test_extract_video_id_short_url():
    """Test extracting video ID from youtu.be URL"""
    fetcher = YouTubeFetcher()
    url = "https://youtu.be/dQw4w9WgXcQ"
    video_id = fetcher.extract_video_id(url)
    assert video_id == "dQw4w9WgXcQ"


def test_extract_video_id_with_params():
    """Test extracting video ID from URL with parameters"""
    fetcher = YouTubeFetcher()
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=10s"
    video_id = fetcher.extract_video_id(url)
    assert video_id == "dQw4w9WgXcQ"


def test_extract_video_id_invalid_url():
    """Test extracting video ID from invalid URL raises error"""
    fetcher = YouTubeFetcher()
    with pytest.raises(ValueError):
        fetcher.extract_video_id("https://notayoutubeurl.com")


def test_can_handle_youtube_url():
    """Test can_handle returns True for YouTube URLs"""
    fetcher = YouTubeFetcher()
    assert fetcher.can_handle("https://www.youtube.com/watch?v=test") == True
    assert fetcher.can_handle("https://youtu.be/test") == True


def test_can_handle_non_youtube_url():
    """Test can_handle returns False for non-YouTube URLs"""
    fetcher = YouTubeFetcher()
    assert fetcher.can_handle("https://vimeo.com/test") == False


def test_get_transcript_error_handling():
    """Test get_transcript handles errors gracefully"""
    fetcher = YouTubeFetcher()
    # Use a video ID that will for sure fail
    result = fetcher.get_transcript("https://www.youtube.com/watch?v=invalidvideoid123")

    assert result["success"] == False
    assert "error" in result
    assert "error_type" in result


def test_extract_video_id_with_whitespace():
    """Test extracting video ID with whitespace"""
    fetcher = YouTubeFetcher()
    url = "  https://www.youtube.com/watch?v=test123  "
    video_id = fetcher.extract_video_id(url)
    assert video_id == "test123"
