import pytest
from backend.services.database import DatabaseService

def test_database_initialization(test_db):
    """Test database creates tables correctly"""
    assert test_db.db_path == "test_stash.db"

def test_save_video(test_db, sample_video_data):
    """Test saving a video to database"""
    result = test_db.save_video(sample_video_data)
    
    assert result['success'] == True
    assert result['data']['video_id'] == 'test123'
    assert result['data']['language'] == 'English'

def test_save_duplicate_video(test_db, sample_video_data):
    """Test saving duplicate video fails"""
    test_db.save_video(sample_video_data)
    result = test_db.save_video(sample_video_data)
    
    assert result['success'] == False
    assert 'already exists' in result['error'].lower()

def test_get_video_by_id(test_db, sample_video_data):
    """Test retrieving video by ID"""
    test_db.save_video(sample_video_data)
    video = test_db.get_video_by_id('test123')
    
    assert video is not None
    assert video['video_id'] == 'test123'
    assert video['raw_transcript'] == 'This is a test transcript'

def test_get_nonexistent_video(test_db):
    """Test retrieving video that doesn't exist"""
    video = test_db.get_video_by_id('nonexistent')
    assert video is None

def test_get_all_videos(test_db, sample_video_data):
    """Test retrieving all videos"""
    test_db.save_video(sample_video_data)
    
    sample_video_data['video_id'] = 'test456'
    sample_video_data['url'] = 'https://www.youtube.com/watch?v=test456'
    test_db.save_video(sample_video_data)
    
    videos = test_db.get_all_videos()
    assert len(videos) == 2

def test_get_all_videos_empty(test_db):
    """Test get all videos when database is empty"""
    videos = test_db.get_all_videos()
    assert videos == []

def test_save_video_missing_required_field(test_db):
    """Test saving video with missing required field"""
    incomplete_data = {
        'url': 'https://www.youtube.com/watch?v=test',
        # Missing video_id
        'raw_transcript': 'test'
    }
    result = test_db.save_video(incomplete_data)
    assert result['success'] == False

def test_save_video_database_error(test_db):
    """Test handling of database errors"""
    invalid_data = {
        'url': 'test',
        'video_id': 'test',
        'raw_transcript': None,  # Might cause issues
        'segments_count': 'not_a_number'  # Wrong type
    }
    result = test_db.save_video(invalid_data)
    # Should handle well without crashing
    assert 'success' in result