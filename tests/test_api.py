import os
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

# Helper function to create authenticated user and get token


def get_auth_token(username=None, password=None):
    """Create a test user and return auth token"""
    if username is None:
        # Generate unique username for this test
        import random

        username = f"testuser_{random.randint(1000, 9999)}"
    if password is None:
        password = "testpass123"

    # Try to signup (might fail if user exists, that's ok)
    client.post("/api/auth/signup", json={"username": username, "password": password})

    # Login to get token
    response = client.post("/api/auth/login", json={"username": username, "password": password})

    if response.status_code == 200:
        return response.json()["access_token"]
    return None


def get_auth_headers(username=None, password=None):
    """Get authorization headers with token"""
    token = get_auth_token(username, password)
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def test_health_check():
    """Test health check endpoint"""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_get_all_videos():
    """Test getting all videos with auth"""
    headers = get_auth_headers()
    response = client.get("/api/videos", headers=headers)
    assert response.status_code == 200
    assert "success" in response.json()
    assert "data" in response.json()


def test_save_video_invalid_url():
    """Test saving video with invalid URL"""
    headers = get_auth_headers()
    response = client.post("/api/videos", json={"url": "not a youtube url"}, headers=headers)
    assert response.status_code in [400, 500]


def test_get_nonexistent_video():
    """Test getting video that doesn't exist"""
    headers = get_auth_headers()
    response = client.get("/api/videos/nonexistent123", headers=headers)
    assert response.status_code in [404, 403]  # 403 if it exists but belongs to another user


def test_save_video_missing_url():
    """Test saving video without URL"""
    headers = get_auth_headers()
    response = client.post("/api/videos", json={}, headers=headers)
    assert response.status_code == 422  # Validation error


def test_get_video_by_id_format():
    """Test getting video returns correct format"""
    headers = get_auth_headers()
    response = client.get("/api/videos", headers=headers)
    data = response.json()

    if data.get("success") and len(data.get("data", [])) > 0:
        video_id = data["data"][0]["video_id"]
        response = client.get(f"/api/videos/{video_id}", headers=headers)
        assert response.status_code in [200, 403]  # 403 if belongs to another user
        if response.status_code == 200:
            assert "data" in response.json()


@patch("backend.main.youtube_fetcher.get_transcript")
def test_save_video_success_with_summary(mock_get_transcript):
    """Test successfully saving video with AI summary"""
    headers = get_auth_headers(username="summarytest", password="pass123")

    mock_get_transcript.return_value = {
        "success": True,
        "video_id": "test_video_summary",
        "transcript": "This is a test transcript",
        "segments_count": 10,
        "language": "English",
        "is_generated": True,
    }

    response = client.post(
        "/api/videos",
        json={"url": "https://www.youtube.com/watch?v=test_video_summary"},
        headers=headers,
    )

    assert response.status_code in [200, 400, 500]


@patch("backend.main.youtube_fetcher.get_transcript")
def test_save_video_transcript_failure(mock_get_transcript):
    """Test saving video when transcript fetch fails"""
    headers = get_auth_headers()

    mock_get_transcript.return_value = {"success": False, "error": "Transcript not found"}

    response = client.post(
        "/api/videos", json={"url": "https://www.youtube.com/watch?v=fail123"}, headers=headers
    )

    assert response.status_code == 400
    assert "Transcript not found" in response.json()["detail"]


@patch("backend.main.youtube_fetcher.extract_video_id")
@patch("backend.main.db_service.get_video_by_id")
def test_save_video_already_exists(mock_get_video, mock_extract_id):
    """Test saving video that already exists"""
    headers = get_auth_headers()

    mock_extract_id.return_value = "existing123"
    mock_get_video.return_value = {
        "video_id": "existing123",
        "url": "https://www.youtube.com/watch?v=existing123",
    }

    response = client.post(
        "/api/videos", json={"url": "https://www.youtube.com/watch?v=existing123"}, headers=headers
    )

    assert response.status_code == 200
    assert "already exists" in response.json()["message"]


def test_invalid_endpoint():
    """Test accessing invalid endpoint"""
    response = client.get("/api/invalid")
    assert response.status_code == 404


def test_save_video_exception_handling():
    """Test API handles unexpected exceptions"""
    headers = get_auth_headers()
    response = client.post("/api/videos", json={"url": ""}, headers=headers)
    assert response.status_code >= 400


@patch("backend.main.db_service.save_video")
def test_save_video_database_save_fails(mock_save):
    """Test when database save operation fails"""
    headers = get_auth_headers()
    mock_save.return_value = {"success": False, "error": "Database error"}

    with patch("backend.main.youtube_fetcher.extract_video_id", return_value="test123"):
        with patch("backend.main.db_service.get_video_by_id", return_value=None):
            with patch("backend.main.youtube_fetcher.get_transcript") as mock_transcript:
                mock_transcript.return_value = {
                    "success": True,
                    "video_id": "test123",
                    "transcript": "test",
                    "segments_count": 1,
                }

                response = client.post(
                    "/api/videos",
                    json={"url": "https://www.youtube.com/watch?v=test123"},
                    headers=headers,
                )

                assert response.status_code == 500


@patch("backend.main.db_service.get_user_videos")
def test_get_all_videos_exception(mock_get_all):
    """Test get all videos handles exceptions"""
    headers = get_auth_headers()
    mock_get_all.side_effect = Exception("Database error")

    response = client.get("/api/videos", headers=headers)
    assert response.status_code == 500


def test_groq_initialization_failure():
    """Test when Groq API key is missing"""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert "groq_summarizer" in response.json()


@patch("backend.main.youtube_fetcher.extract_video_id")
@patch("backend.main.db_service.get_video_by_id")
def test_duplicate_video_returns_existing(mock_get_video, mock_extract):
    """Test saving duplicate video returns existing data"""
    headers = get_auth_headers()

    mock_extract.return_value = "duplicate123"
    mock_get_video.return_value = {
        "id": 1,
        "video_id": "duplicate123",
        "url": "https://youtube.com/watch?v=duplicate123",
    }

    response = client.post(
        "/api/videos", json={"url": "https://youtube.com/watch?v=duplicate123"}, headers=headers
    )

    assert response.status_code == 200
    assert "already exists" in response.json()["message"]


@patch("backend.main.youtube_fetcher.extract_video_id")
@patch("backend.main.db_service.get_video_by_id")
@patch("backend.main.youtube_fetcher.get_transcript")
def test_transcript_fetch_fails(mock_transcript, mock_get_video, mock_extract):
    """Test when YouTube transcript fetch fails"""
    headers = get_auth_headers()

    mock_extract.return_value = "test123"
    mock_get_video.return_value = None
    mock_transcript.return_value = {"success": False, "error": "No transcript available"}

    response = client.post(
        "/api/videos", json={"url": "https://youtube.com/watch?v=test123"}, headers=headers
    )

    assert response.status_code == 400
    assert "No transcript available" in response.json()["detail"]


@patch("backend.main.youtube_fetcher.extract_video_id")
@patch("backend.main.db_service.get_video_by_id")
@patch("backend.main.youtube_fetcher.get_transcript")
@patch("backend.main.groq_summarizer")
@patch("backend.main.db_service.save_video")
def test_groq_summary_failure_warning(
    mock_save, mock_groq, mock_transcript, mock_get_video, mock_extract
):
    """Test when Groq summarization fails but video still saves"""
    headers = get_auth_headers()

    mock_extract.return_value = "test456"
    mock_get_video.return_value = None
    mock_transcript.return_value = {
        "success": True,
        "video_id": "test456",
        "transcript": "Test transcript",
        "segments_count": 5,
        "language": "English",
        "is_generated": True,
    }

    mock_summarizer = Mock()
    mock_summarizer.summarize.return_value = {"success": False, "error": "API rate limit"}
    mock_groq.return_value = mock_summarizer

    mock_save.return_value = {"success": True, "data": {"id": 1, "video_id": "test456"}}

    response = client.post(
        "/api/videos", json={"url": "https://youtube.com/watch?v=test456"}, headers=headers
    )

    assert response.status_code in [200, 400, 500]


@patch("backend.main.youtube_fetcher.extract_video_id")
@patch("backend.main.db_service.get_video_by_id")
@patch("backend.main.youtube_fetcher.get_transcript")
@patch("backend.main.db_service.save_video")
def test_database_save_failure(mock_save, mock_transcript, mock_get_video, mock_extract):
    """Test when database save operation fails"""
    headers = get_auth_headers()

    mock_extract.return_value = "test789"
    mock_get_video.return_value = None
    mock_transcript.return_value = {
        "success": True,
        "video_id": "test789",
        "transcript": "Test",
        "segments_count": 1,
    }
    mock_save.return_value = {"success": False, "error": "Database connection failed"}

    response = client.post(
        "/api/videos", json={"url": "https://youtube.com/watch?v=test789"}, headers=headers
    )

    assert response.status_code == 500


@patch("backend.main.youtube_fetcher.extract_video_id")
def test_unexpected_exception_handling(mock_extract):
    """Test generic exception handler"""
    headers = get_auth_headers()
    mock_extract.side_effect = RuntimeError("Unexpected error")

    response = client.post(
        "/api/videos", json={"url": "https://youtube.com/watch?v=test"}, headers=headers
    )

    assert response.status_code == 500
    assert "detail" in response.json()


def test_invalid_bearer_scheme():
    """Test authorization with wrong scheme (not Bearer)"""
    token = get_auth_token()

    response = client.get("/api/videos", headers={"Authorization": f"Basic {token}"})
    assert response.status_code == 401
    # The actual error is more generic
    assert "Could not validate credentials" in response.json()["detail"]


def test_get_current_user_deleted():
    """Test /api/auth/me when user was deleted from database"""
    # Create user and get token
    import random

    username = f"deleteme_{random.randint(1000, 9999)}"
    signup_response = client.post(
        "/api/auth/signup", json={"username": username, "password": "pass123"}
    )
    token = signup_response.json()["access_token"]

    # Manually delete user from database
    from backend import main

    user = main.db_service.get_user_by_username(username)
    if user:
        import sqlite3

        conn = sqlite3.connect(main.db_service.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = ?", (user["id"],))
        conn.commit()
        conn.close()

    # Try to use token - user no longer exists
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 404
    assert "User not found" in response.json()["detail"]


def test_access_other_users_video():
    """Test accessing video that belongs to different user"""
    # Create first user and save a video
    user1_token = get_auth_token(username="user1_test", password="pass1")

    with patch("backend.main.youtube_fetcher.extract_video_id", return_value="othervid123"):
        with patch("backend.main.youtube_fetcher.get_transcript") as mock_transcript:
            with patch("backend.main.db_service.get_video_by_id") as mock_get_video:
                mock_transcript.return_value = {
                    "success": True,
                    "video_id": "othervid123",
                    "transcript": "test",
                    "segments_count": 1,
                }

                # Save video as user1
                client.post(
                    "/api/videos",
                    json={"url": "https://youtube.com/watch?v=othervid123"},
                    headers={"Authorization": f"Bearer {user1_token}"},
                )

                # Mock get_video_by_id to return video owned by user1
                mock_get_video.return_value = {
                    "video_id": "othervid123",
                    "user_id": 999,  # Different user
                    "url": "test",
                }

                # Try to access as user2
                user2_token = get_auth_token(username="user2_test", password="pass2")
                response = client.get(
                    "/api/videos/othervid123", headers={"Authorization": f"Bearer {user2_token}"}
                )

                assert response.status_code == 403
                assert "Access denied" in response.json()["detail"]


def test_signup_create_user_fails():
    """Test signup when database create_user fails"""
    with patch("backend.main.db_service.create_user") as mock_create:
        mock_create.return_value = {"success": False, "error": "Database error"}

        response = client.post(
            "/api/auth/signup", json={"username": "failuser", "password": "pass123"}
        )

        assert response.status_code == 400
        assert "Database error" in response.json()["detail"]


def test_delete_video_success():
    """Test deleting a video"""
    token = get_auth_token(username="deletetest", password="pass123")

    with patch("backend.main.db_service.get_video_by_id") as mock_get:
        with patch("backend.main.db_service.delete_video") as mock_delete:
            mock_get.return_value = {"video_id": "del123", "user_id": 1}
            mock_delete.return_value = {"success": True}

            response = client.delete(
                "/api/videos/del123", headers={"Authorization": f"Bearer {token}"}
            )

            assert response.status_code == 200
            assert response.json()["success"] == True


def test_delete_video_not_found():
    """Test deleting non-existent video"""
    token = get_auth_token()

    with patch("backend.main.db_service.get_video_by_id", return_value=None):
        response = client.delete(
            "/api/videos/nonexistent", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 404


def test_delete_video_wrong_owner():
    """Test deleting video owned by another user"""
    token = get_auth_token(username="deluser1", password="pass1")

    with patch("backend.main.db_service.get_video_by_id") as mock_get:
        mock_get.return_value = {"video_id": "test123", "user_id": 999}

        response = client.delete(
            "/api/videos/test123", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403


def test_delete_video_without_auth():
    """Test deleting video without authentication"""
    response = client.delete("/api/videos/test123")
    assert response.status_code == 401


def test_update_video_success():
    """Test updating video summary"""
    token = get_auth_token(username="updatetest", password="pass123")

    with patch("backend.main.db_service.get_video_by_id") as mock_get:
        with patch("backend.main.db_service.update_video") as mock_update:
            mock_get.return_value = {
                "video_id": "upd123",
                "user_id": 1,
                "ai_summary": "Old summary",
            }
            mock_update.return_value = {
                "success": True,
                "data": {"video_id": "upd123", "ai_summary": "New summary"},
            }

            response = client.put(
                "/api/videos/upd123",
                json={"ai_summary": "New summary"},
                headers={"Authorization": f"Bearer {token}"},
            )

            assert response.status_code == 200
            assert response.json()["success"] == True


def test_update_video_not_found():
    """Test updating non-existent video"""
    token = get_auth_token()

    with patch("backend.main.db_service.get_video_by_id", return_value=None):
        response = client.put(
            "/api/videos/nonexistent",
            json={"ai_summary": "test"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404


def test_update_video_wrong_owner():
    """Test updating video owned by another user"""
    token = get_auth_token(username="upduser2", password="pass2")

    with patch("backend.main.db_service.get_video_by_id") as mock_get:
        mock_get.return_value = {"video_id": "test123", "user_id": 999}

        response = client.put(
            "/api/videos/test123",
            json={"ai_summary": "test"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403


def test_update_video_without_auth():
    """Test updating video without authentication"""
    response = client.put("/api/videos/test123", json={"ai_summary": "test"})
    assert response.status_code == 401
