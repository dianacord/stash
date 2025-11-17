from unittest.mock import Mock, patch

from backend.services.user_service import AuthService


def test_signup_success_with_mocks():
    repo = Mock()
    repo.get_user_by_username.return_value = None
    repo.create_user.return_value = {"success": True, "data": {"id": 123, "username": "alice"}}

    with patch("backend.services.user_service.get_password_hash", return_value="hashed_pwd"):
        with patch("backend.services.user_service.create_access_token", return_value="token123"):
            service = AuthService(repo)
            result = service.signup("alice", "password")

    assert result["success"] is True
    assert result["access_token"] == "token123"
    assert result["token_type"] == "bearer"
    assert result["username"] == "alice"
    repo.get_user_by_username.assert_called_once_with("alice")
    repo.create_user.assert_called_once()


def test_signup_duplicate_username():
    repo = Mock()
    repo.get_user_by_username.return_value = {"id": 1, "username": "taken"}

    service = AuthService(repo)
    result = service.signup("taken", "password")

    assert result["success"] is False
    assert "already exists" in result["error"].lower()


def test_login_success_with_mocks():
    repo = Mock()
    repo.get_user_by_username.return_value = {
        "id": 1,
        "username": "bob",
        "hashed_password": "hashed_pwd",
    }

    with patch("backend.services.user_service.verify_password", return_value=True):
        with patch("backend.services.user_service.create_access_token", return_value="tok"):
            service = AuthService(repo)
            result = service.login("bob", "password")

    assert result["success"] is True
    assert result["access_token"] == "tok"
    assert result["username"] == "bob"
    repo.get_user_by_username.assert_called_once_with("bob")


def test_login_wrong_password():
    repo = Mock()
    repo.get_user_by_username.return_value = {
        "id": 1,
        "username": "bob",
        "hashed_password": "hashed_pwd",
    }

    with patch("backend.services.user_service.verify_password", return_value=False):
        service = AuthService(repo)
        result = service.login("bob", "wrong")

    assert result["success"] is False
    assert "invalid" in result["error"].lower()


def test_get_user_info_delegates_to_repo():
    repo = Mock()
    repo.get_user_by_id.return_value = {"id": 9, "username": "x"}

    service = AuthService(repo)
    out = service.get_user_info(9)

    assert out == {"id": 9, "username": "x"}
    repo.get_user_by_id.assert_called_once_with(9)
