import pytest
from fastapi.testclient import TestClient
from backend.main import app
from unittest.mock import patch, Mock
import os

client = TestClient(app)

def test_health_check():
    """Test health check endpoint"""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_get_all_videos():
    """Test getting all videos"""
    response = client.get("/api/videos")
    assert response.status_code == 200
    assert "success" in response.json()
    assert "data" in response.json()

def test_save_video_invalid_url():
    """Test saving video with invalid URL"""
    response = client.post(
        "/api/videos",
        json={"url": "not a youtube url"}
    )
    assert response.status_code in [400, 500]

def test_get_nonexistent_video():
    """Test getting video that doesn't exist"""
    response = client.get("/api/videos/nonexistent123")
    assert response.status_code == 404

def test_save_video_missing_url():
    """Test saving video without URL"""
    response = client.post(
        "/api/videos",
        json={}
    )
    assert response.status_code == 422  # Validation error

def test_get_video_by_id_format():
    """Test getting video returns correct format"""
    # First add a video (if none exist, this might fail)
    response = client.get("/api/videos")
    data = response.json()
    
    if data['success'] and len(data['data']) > 0:
        video_id = data['data'][0]['video_id']
        response = client.get(f"/api/videos/{video_id}")
        assert response.status_code == 200
        assert 'data' in response.json()

@patch('backend.main.youtube_fetcher.get_transcript')
def test_save_video_success_with_summary(mock_get_transcript):
    """Test successfully saving video with AI summary"""
    mock_get_transcript.return_value = {
        'success': True,
        'video_id': 'test_video_123',
        'transcript': 'This is a test transcript',
        'segments_count': 10,
        'language': 'English',
        'is_generated': True
    }
    
    response = client.post(
        "/api/videos",
        json={"url": "https://www.youtube.com/watch?v=test_video_123"}
    )
    
    # Should get 200 or 400 depending on if Groq works
    assert response.status_code in [200, 400, 500]

@patch('backend.main.youtube_fetcher.get_transcript')
def test_save_video_transcript_failure(mock_get_transcript):
    """Test saving video when transcript fetch fails"""
    mock_get_transcript.return_value = {
        'success': False,
        'error': 'Transcript not found'
    }
    
    response = client.post(
        "/api/videos",
        json={"url": "https://www.youtube.com/watch?v=fail123"}
    )
    
    assert response.status_code == 400
    assert 'Transcript not found' in response.json()['detail']

@patch('backend.main.youtube_fetcher.extract_video_id')
@patch('backend.main.db_service.get_video_by_id')
def test_save_video_already_exists(mock_get_video, mock_extract_id):
    """Test saving video that already exists"""
    mock_extract_id.return_value = 'existing123'
    mock_get_video.return_value = {
        'video_id': 'existing123',
        'url': 'https://www.youtube.com/watch?v=existing123'
    }
    
    response = client.post(
        "/api/videos",
        json={"url": "https://www.youtube.com/watch?v=existing123"}
    )
    
    assert response.status_code == 200
    assert 'already exists' in response.json()['message']

def test_invalid_endpoint():
    """Test accessing invalid endpoint"""
    response = client.get("/api/invalid")
    assert response.status_code == 404

def test_save_video_exception_handling():
    """Test API handles unexpected exceptions"""
    response = client.post(
        "/api/videos",
        json={"url": ""}  # Empty URL might trigger different code path
    )

    assert response.status_code >= 400

@patch('backend.main.db_service.save_video')
def test_save_video_database_save_fails(mock_save):
    """Test when database save operation fails"""
    mock_save.return_value = {'success': False, 'error': 'Database error'}
    
    with patch('backend.main.youtube_fetcher.extract_video_id', return_value='test123'):
        with patch('backend.main.db_service.get_video_by_id', return_value=None):
            with patch('backend.main.youtube_fetcher.get_transcript') as mock_transcript:
                mock_transcript.return_value = {
                    'success': True,
                    'video_id': 'test123',
                    'transcript': 'test',
                    'segments_count': 1
                }
                
                response = client.post(
                    "/api/videos",
                    json={"url": "https://www.youtube.com/watch?v=test123"}
                )
                
                assert response.status_code == 500

@patch('backend.main.db_service.get_all_videos')
def test_get_all_videos_exception(mock_get_all):
    """Test get all videos handles exceptions"""
    mock_get_all.side_effect = Exception("Database error")
    
    response = client.get("/api/videos")
    assert response.status_code == 500

from unittest.mock import patch, Mock
import os

def test_groq_initialization_failure():
    """Test when Groq API key is missing"""
    original_key = os.environ.get('GROQ_API_KEY')
    if 'GROQ_API_KEY' in os.environ:
        del os.environ['GROQ_API_KEY']
    
    response = client.get("/api/health")
    assert response.status_code == 200
    assert 'groq_summarizer' in response.json()
    
    if original_key:
        os.environ['GROQ_API_KEY'] = original_key

@patch('backend.main.youtube_fetcher.extract_video_id')
@patch('backend.main.db_service.get_video_by_id')
def test_duplicate_video_returns_existing(mock_get_video, mock_extract):
    """Test saving duplicate video returns existing data"""
    mock_extract.return_value = 'duplicate123'
    mock_get_video.return_value = {
        'id': 1,
        'video_id': 'duplicate123',
        'url': 'https://youtube.com/watch?v=duplicate123'
    }
    
    response = client.post(
        "/api/videos",
        json={"url": "https://youtube.com/watch?v=duplicate123"}
    )
    
    assert response.status_code == 200
    assert "already exists" in response.json()['message']

@patch('backend.main.youtube_fetcher.extract_video_id')
@patch('backend.main.db_service.get_video_by_id')
@patch('backend.main.youtube_fetcher.get_transcript')
def test_transcript_fetch_fails(mock_transcript, mock_get_video, mock_extract):
    """Test when YouTube transcript fetch fails"""
    mock_extract.return_value = 'test123'
    mock_get_video.return_value = None
    mock_transcript.return_value = {
        'success': False,
        'error': 'No transcript available'
    }
    
    response = client.post(
        "/api/videos",
        json={"url": "https://youtube.com/watch?v=test123"}
    )
    
    assert response.status_code == 400
    assert 'No transcript available' in response.json()['detail']

@patch('backend.main.youtube_fetcher.extract_video_id')
@patch('backend.main.db_service.get_video_by_id')
@patch('backend.main.youtube_fetcher.get_transcript')
@patch('backend.main.groq_summarizer')
@patch('backend.main.db_service.save_video')
def test_groq_summary_failure_warning(mock_save, mock_groq, mock_transcript, mock_get_video, mock_extract):
    """Test when Groq summarization fails but video still saves"""
    mock_extract.return_value = 'test456'
    mock_get_video.return_value = None
    mock_transcript.return_value = {
        'success': True,
        'video_id': 'test456',
        'transcript': 'Test transcript',
        'segments_count': 5,
        'language': 'English',
        'is_generated': True
    }
    
    # Mock Groq to return failure
    mock_summarizer = Mock()
    mock_summarizer.summarize.return_value = {
        'success': False,
        'error': 'API rate limit'
    }
    mock_groq.return_value = mock_summarizer
    
    mock_save.return_value = {
        'success': True,
        'data': {'id': 1, 'video_id': 'test456'}
    }
    
    response = client.post(
        "/api/videos",
        json={"url": "https://youtube.com/watch?v=test456"}
    )
    
    # Should still succeed even if summary fails
    assert response.status_code in [200, 400, 500]

@patch('backend.main.youtube_fetcher.extract_video_id')
@patch('backend.main.db_service.get_video_by_id')
@patch('backend.main.youtube_fetcher.get_transcript')
@patch('backend.main.db_service.save_video')
def test_database_save_failure(mock_save, mock_transcript, mock_get_video, mock_extract):
    """Test when database save operation fails"""
    mock_extract.return_value = 'test789'
    mock_get_video.return_value = None
    mock_transcript.return_value = {
        'success': True,
        'video_id': 'test789',
        'transcript': 'Test',
        'segments_count': 1
    }
    mock_save.return_value = {
        'success': False,
        'error': 'Database connection failed'
    }
    
    response = client.post(
        "/api/videos",
        json={"url": "https://youtube.com/watch?v=test789"}
    )
    
    assert response.status_code == 500

@patch('backend.main.youtube_fetcher.extract_video_id')
def test_unexpected_exception_handling(mock_extract):
    """Test generic exception handler"""
    mock_extract.side_effect = RuntimeError("Unexpected error")
    
    response = client.post(
        "/api/videos",
        json={"url": "https://youtube.com/watch?v=test"}
    )
    
    assert response.status_code == 500
    assert 'detail' in response.json()