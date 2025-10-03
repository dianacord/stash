import pytest
import os
import sqlite3
from backend.services.database import DatabaseService

@pytest.fixture
def test_db():
    """Create a temporary test database"""
    test_db_path = "test_stash.db"
    
    # Create fresh database for tests
    db_service = DatabaseService(db_path=test_db_path)
    
    yield db_service
    
    # Cleanup after tests
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

@pytest.fixture
def sample_video_data():
    """Sample video data for testing"""
    return {
        'url': 'https://www.youtube.com/watch?v=test123',
        'video_id': 'test123',
        'raw_transcript': 'This is a test transcript',
        'language': 'English',
        'is_generated': True,
        'segments_count': 10,
        'platform': 'youtube',
        'ai_summary': 'Test summary'
    }