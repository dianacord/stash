import pytest
import os
import sqlite3
from backend.services.database import DatabaseService

@pytest.fixture
def test_db():
    """Create a temporary test database with users table"""
    test_db_path = "test_stash.db"
    
    # Create fresh database for tests
    db_service = DatabaseService(db_path=test_db_path)
    
    # ADD: Create users table (migration)
    conn = sqlite3.connect(test_db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Also add user_id column to saved_videos
    try:
        cursor.execute('ALTER TABLE saved_videos ADD COLUMN user_id INTEGER')
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    conn.commit()
    conn.close()
    
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