"""Business logic layer for authentication operations.

Separates auth business logic from HTTP handling.
"""

from datetime import timedelta

from backend.protocols import UserRepository
from backend.services.auth_service import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    get_password_hash,
    verify_password,
)


class AuthService:
    """Service for handling authentication-related business logic."""

    def __init__(self, user_repository: UserRepository):
        """
        Initialize auth service with user repository.

        Args:
            user_repository: User data storage (e.g., DatabaseService)
        """
        self.user_repository = user_repository

    def signup(self, username: str, password: str) -> dict:
        """
        Register a new user.

        Args:
            username: Desired username
            password: Plain text password (will be hashed)

        Returns:
            dict with success, access_token, token_type, and username
            or success=False with error
        """
        # Check if username already taken
        existing_user = self.user_repository.get_user_by_username(username)
        if existing_user:
            return {"success": False, "error": "Username already exists"}

        # Hash password
        hashed_password = get_password_hash(password)

        # Create user
        result = self.user_repository.create_user(username, hashed_password)

        if not result["success"]:
            return result

        user = result["data"]

        # Generate JWT token
        access_token = create_access_token(
            data={"sub": user["username"], "user_id": user["id"]},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        )

        return {
            "success": True,
            "access_token": access_token,
            "token_type": "bearer",
            "username": user["username"],
        }

    def login(self, username: str, password: str) -> dict:
        """
        Authenticate user and generate token.

        Args:
            username: Username
            password: Plain text password

        Returns:
            dict with success, access_token, token_type, and username
            or success=False with error
        """
        # Get user from repository
        user = self.user_repository.get_user_by_username(username)

        if not user:
            return {"success": False, "error": "Invalid username or password"}

        # Verify password
        if not verify_password(password, user["hashed_password"]):
            return {"success": False, "error": "Invalid username or password"}

        # Generate JWT token
        access_token = create_access_token(
            data={"sub": user["username"], "user_id": user["id"]},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        )

        return {
            "success": True,
            "access_token": access_token,
            "token_type": "bearer",
            "username": user["username"],
        }

    def get_user_info(self, user_id: int) -> dict | None:
        """
        Get user information by ID.

        Args:
            user_id: User ID

        Returns:
            User dict or None if not found
        """
        return self.user_repository.get_user_by_id(user_id)
