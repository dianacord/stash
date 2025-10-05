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

def test_save_video(test_db, sample_video_data):
    """Test saving a video to database with user_id"""
    # Create a test user first
    user_result = test_db.create_user("videoowner", "pass123")
    user_id = user_result['data']['id']
    
    result = test_db.save_video(sample_video_data, user_id)
    
    assert result['success'] == True
    assert result['data']['video_id'] == 'test123'
    assert result['data']['user_id'] == user_id

def test_save_duplicate_video(test_db, sample_video_data):
    """Test saving duplicate video fails"""
    user_result = test_db.create_user("dupuser", "pass123")
    user_id = user_result['data']['id']
    
    test_db.save_video(sample_video_data, user_id)
    result = test_db.save_video(sample_video_data, user_id)
    
    assert result['success'] == False
    assert 'already exists' in result['error'].lower()

def test_get_video_by_id(test_db, sample_video_data):
    """Test retrieving video by ID"""
    user_result = test_db.create_user("getuser", "pass123")
    user_id = user_result['data']['id']
    
    test_db.save_video(sample_video_data, user_id)
    video = test_db.get_video_by_id('test123')
    
    assert video is not None
    assert video['video_id'] == 'test123'
    assert video['raw_transcript'] == 'This is a test transcript'

def test_get_all_videos(test_db, sample_video_data):
    """Test retrieving all videos for a user"""
    user_result = test_db.create_user("allvidsuser", "pass123")
    user_id = user_result['data']['id']
    
    test_db.save_video(sample_video_data, user_id)
    
    sample_video_data['video_id'] = 'test456'
    sample_video_data['url'] = 'https://www.youtube.com/watch?v=test456'
    test_db.save_video(sample_video_data, user_id)
    
    videos = test_db.get_user_videos(user_id)
    assert len(videos) == 2

def test_save_video_missing_required_field(test_db):
    """Test saving video with missing required field"""
    user_result = test_db.create_user("missingfield", "pass123")
    user_id = user_result['data']['id']
    
    incomplete_data = {
        'url': 'https://www.youtube.com/watch?v=test',
        # Missing video_id
        'raw_transcript': 'test'
    }
    result = test_db.save_video(incomplete_data, user_id)
    assert result['success'] == False

def test_save_video_database_error(test_db):
    """Test handling of database errors"""
    user_result = test_db.create_user("erroruser", "pass123")
    user_id = user_result['data']['id']
    
    invalid_data = {
        'url': 'test',
        'video_id': 'test',
        'raw_transcript': None,
        'segments_count': 'not_a_number'
    }
    result = test_db.save_video(invalid_data, user_id)
    assert 'success' in result

# User-specific tests
def test_create_user(test_db):
    """Test creating a new user"""
    result = test_db.create_user("newuser", "hashedpassword123")
    
    assert result['success'] == True
    assert result['data']['username'] == "newuser"
    assert 'id' in result['data']

def test_create_duplicate_user(test_db):
    """Test creating duplicate user fails"""
    test_db.create_user("duplicate", "pass123")
    result = test_db.create_user("duplicate", "pass456")
    
    assert result['success'] == False
    assert 'already exists' in result['error'].lower()

def test_get_user_by_username(test_db):
    """Test retrieving user by username"""
    test_db.create_user("findme", "hashedpass")
    user = test_db.get_user_by_username("findme")
    
    assert user is not None
    assert user['username'] == "findme"
    assert 'hashed_password' in user

def test_get_user_by_username_not_found(test_db):
    """Test retrieving non-existent user"""
    user = test_db.get_user_by_username("doesnotexist")
    assert user is None

def test_get_user_by_id(test_db):
    """Test retrieving user by ID"""
    result = test_db.create_user("idtest", "pass123")
    user_id = result['data']['id']
    
    user = test_db.get_user_by_id(user_id)
    assert user is not None
    assert user['username'] == "idtest"

def test_get_user_videos(test_db, sample_video_data):
    """Test getting videos for specific user"""
    user_result = test_db.create_user("videouser", "pass123")
    user_id = user_result['data']['id']
    
    test_db.save_video(sample_video_data, user_id)
    
    videos = test_db.get_user_videos(user_id)
    assert len(videos) == 1
    assert videos[0]['user_id'] == user_id

def test_get_user_videos_empty(test_db):
    """Test getting videos for user with no videos"""
    user_result = test_db.create_user("novids", "pass123")
    user_id = user_result['data']['id']
    
    videos = test_db.get_user_videos(user_id)
    assert videos == []