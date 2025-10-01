import pytest
from fastapi.testclient import TestClient
from backend.main import app
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