import pytest
import os
import sqlite3
from backend.services.database import DatabaseService

@pytest.fixture(autouse=True)
def setup_test_db():
    """
    Global test database fixture - automatically runs for ALL tests.
    Creates fresh test database with users and saved_videos tables.
    """
    test_db_path = "test_global.db"
    
    # Create test database
    conn = sqlite3.connect(test_db_path)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create saved_videos table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS saved_videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            video_id TEXT NOT NULL UNIQUE,
            platform TEXT DEFAULT 'youtube',
            title TEXT,
            raw_transcript TEXT,
            ai_summary TEXT,
            language TEXT,
            is_generated BOOLEAN,
            segments_count INTEGER,
            user_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    
    # Make all tests use this test database
    from backend import main
    main.db_service = DatabaseService(db_path=test_db_path)
    
    yield main.db_service
    
    # Cleanup after all tests
    if os.path.exists(test_db_path):
        os.remove(test_db_path)


@pytest.fixture
def test_db(setup_test_db):
    """Alias for tests that explicitly request test_db"""
    return setup_test_db


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