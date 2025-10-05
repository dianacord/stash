import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.database import DatabaseService
import os
import sqlite3

client = TestClient(app)

# Test user credentials
TEST_USER = "testuser_auth"
TEST_PASSWORD = "testpass123"


def test_signup_success():
    """Test successful user signup"""
    response = client.post(
        "/api/auth/signup",
        json={"username": TEST_USER, "password": TEST_PASSWORD}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "token_type" in data
    assert data["token_type"] == "bearer"
    assert data["username"] == TEST_USER


def test_signup_duplicate_username():
    """Test signup with existing username fails"""
    # First signup
    client.post(
        "/api/auth/signup",
        json={"username": "duplicate_user", "password": "pass123"}
    )
    
    # Try to signup again with same username
    response = client.post(
        "/api/auth/signup",
        json={"username": "duplicate_user", "password": "pass123"}
    )
    
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"].lower()


def test_signup_missing_fields():
    """Test signup with missing fields"""
    response = client.post(
        "/api/auth/signup",
        json={"username": "onlyusername"}
    )
    assert response.status_code == 422  # Validation error


def test_login_success():
    """Test successful login"""
    # First create user
    signup_response = client.post(
        "/api/auth/signup",
        json={"username": "logintest", "password": "pass123"}
    )
    assert signup_response.status_code == 200
    
    # Now login
    response = client.post(
        "/api/auth/login",
        json={"username": "logintest", "password": "pass123"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["username"] == "logintest"


def test_login_wrong_password():
    """Test login with incorrect password"""
    # Create user
    client.post(
        "/api/auth/signup",
        json={"username": "wrongpass", "password": "correct123"}
    )
    
    # Try to login with wrong password
    response = client.post(
        "/api/auth/login",
        json={"username": "wrongpass", "password": "wrong123"}
    )
    
    assert response.status_code == 401
    assert "Invalid username or password" in response.json()["detail"]


def test_login_nonexistent_user():
    """Test login with user that doesn't exist"""
    response = client.post(
        "/api/auth/login",
        json={"username": "doesnotexist", "password": "pass123"}
    )
    
    assert response.status_code == 401
    assert "Invalid username or password" in response.json()["detail"]


def test_get_current_user_with_valid_token():
    """Test /api/auth/me with valid token"""
    # Signup to get token
    signup_response = client.post(
        "/api/auth/signup",
        json={"username": "metest", "password": "pass123"}
    )
    token = signup_response.json()["access_token"]
    
    # Get current user info
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert data["data"]["username"] == "metest"


def test_get_current_user_without_token():
    """Test /api/auth/me without token fails"""
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert "Not authenticated" in response.json()["detail"]


def test_get_current_user_with_invalid_token():
    """Test /api/auth/me with invalid token"""
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer invalid_token_here"}
    )
    assert response.status_code == 401


def test_protected_video_endpoint_without_auth():
    """Test accessing videos without authentication fails"""
    response = client.get("/api/videos")
    assert response.status_code == 401


def test_protected_video_endpoint_with_auth():
    """Test accessing videos with authentication succeeds"""
    # Signup to get token
    signup_response = client.post(
        "/api/auth/signup",
        json={"username": "videotest", "password": "pass123"}
    )
    token = signup_response.json()["access_token"]
    
    # Get videos with auth
    response = client.get(
        "/api/videos",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "success" in data
    assert "data" in data


def test_save_video_without_auth():
    """Test saving video without authentication fails"""
    response = client.post(
        "/api/videos",
        json={"url": "https://www.youtube.com/watch?v=test"}
    )
    assert response.status_code == 401


def test_token_in_invalid_format():
    """Test token without Bearer prefix"""
    response = client.get(
        "/api/videos",
        headers={"Authorization": "just_the_token"}
    )
    assert response.status_code == 401


def test_empty_authorization_header():
    """Test empty authorization header"""
    response = client.get(
        "/api/videos",
        headers={"Authorization": ""}
    )
    assert response.status_code == 401