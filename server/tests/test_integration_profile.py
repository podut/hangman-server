"""Integration tests for user profile update endpoint."""

import pytest
from fastapi.testclient import TestClient
from server.src.main import app
from server.src.repositories import UserRepository


client = TestClient(app)


@pytest.fixture
def user_repo():
    """Get user repository instance."""
    from server.src.main import user_repo
    return user_repo


@pytest.fixture
def registered_user(user_repo):
    """Register a test user and return credentials."""
    import uuid
    # Use unique email for each test
    unique_id = uuid.uuid4().hex[:8]
    email = f"profile_test_{unique_id}@example.com"
    password = "Test1234"
    
    # Register user
    response = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "nickname": "OriginalNick"
    })
    assert response.status_code == 201
    
    # Login to get token
    login_response = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password
    })
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    user_id = login_response.json()["user_id"]
    
    return {
        "email": email,
        "password": password,
        "token": token,
        "user_id": user_id,
        "nickname": "OriginalNick"
    }


@pytest.fixture
def another_user(user_repo):
    """Register another test user (for email conflict tests)."""
    import uuid
    # Use unique email for each test
    unique_id = uuid.uuid4().hex[:8]
    email = f"another_user_{unique_id}@example.com"
    password = "Another1234"
    
    response = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password
    })
    assert response.status_code == 201
    return {"email": email}


class TestProfileUpdate:
    """Test suite for PATCH /api/v1/users/me endpoint."""
    
    def test_update_nickname_success(self, registered_user):
        """Test updating only nickname."""
        token = registered_user["token"]
        
        response = client.patch(
            "/api/v1/users/me",
            json={"nickname": "NewNickname"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["nickname"] == "NewNickname"
        assert data["email"] == registered_user["email"]
        assert data["user_id"] == registered_user["user_id"]
        assert "password" not in data
    
    def test_update_email_success(self, registered_user):
        """Test updating only email."""
        token = registered_user["token"]
        
        response = client.patch(
            "/api/v1/users/me",
            json={"email": "newemail@example.com"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "newemail@example.com"
        assert data["nickname"] == registered_user["nickname"]
        assert data["user_id"] == registered_user["user_id"]
    
    def test_update_both_fields_success(self, registered_user):
        """Test updating both email and nickname."""
        token = registered_user["token"]
        
        response = client.patch(
            "/api/v1/users/me",
            json={
                "email": "updated@example.com",
                "nickname": "UpdatedNick"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "updated@example.com"
        assert data["nickname"] == "UpdatedNick"
    
    def test_update_no_fields_fails(self, registered_user):
        """Test that request with no fields returns 400."""
        token = registered_user["token"]
        
        response = client.patch(
            "/api/v1/users/me",
            json={},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 400
        detail = response.json().get("detail", "")
        if detail:
            assert "at least one field" in detail.lower()
    
    def test_update_email_conflict(self, registered_user, another_user):
        """Test that updating to an existing email returns 409."""
        token = registered_user["token"]
        existing_email = another_user["email"]
        
        response = client.patch(
            "/api/v1/users/me",
            json={"email": existing_email},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 409
        detail = response.json()["detail"].lower()
        # Accept either "already exists" or "choose a different username" (from error handler)
        assert ("already exists" in detail or "choose a different" in detail)
    
    def test_update_same_email_allowed(self, registered_user):
        """Test that updating to the same email is allowed (no-op)."""
        token = registered_user["token"]
        same_email = registered_user["email"]
        
        response = client.patch(
            "/api/v1/users/me",
            json={"email": same_email, "nickname": "ChangedNick"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == same_email
        assert data["nickname"] == "ChangedNick"
    
    def test_update_without_token_fails(self, registered_user):
        """Test that update without authentication returns 401."""
        response = client.patch(
            "/api/v1/users/me",
            json={"nickname": "Hacker"}
        )
        
        assert response.status_code == 401
    
    def test_update_with_invalid_token_fails(self, registered_user):
        """Test that update with invalid token returns 401."""
        response = client.patch(
            "/api/v1/users/me",
            json={"nickname": "Hacker"},
            headers={"Authorization": "Bearer invalid_token_12345"}
        )
        
        assert response.status_code == 401
    
    def test_update_email_validation(self, registered_user):
        """Test that invalid email format is rejected."""
        token = registered_user["token"]
        
        response = client.patch(
            "/api/v1/users/me",
            json={"email": "not-an-email"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_profile_persists_after_update(self, registered_user):
        """Test that profile updates are persisted."""
        token = registered_user["token"]
        
        # Update profile
        update_response = client.patch(
            "/api/v1/users/me",
            json={"nickname": "PersistentNick"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert update_response.status_code == 200
        
        # Get profile to verify persistence
        get_response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["nickname"] == "PersistentNick"
    
    def test_update_empty_nickname(self, registered_user):
        """Test that empty nickname is allowed (sets to empty string)."""
        token = registered_user["token"]
        
        response = client.patch(
            "/api/v1/users/me",
            json={"nickname": ""},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["nickname"] == ""
    
    def test_multiple_updates_in_sequence(self, registered_user):
        """Test multiple profile updates work correctly."""
        token = registered_user["token"]
        
        # First update - change nickname
        response1 = client.patch(
            "/api/v1/users/me",
            json={"nickname": "First"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response1.status_code == 200
        assert response1.json()["nickname"] == "First"
        
        # Second update - change email
        response2 = client.patch(
            "/api/v1/users/me",
            json={"email": "second@example.com"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response2.status_code == 200
        assert response2.json()["email"] == "second@example.com"
        assert response2.json()["nickname"] == "First"  # Nickname unchanged
        
        # Third update - change both
        response3 = client.patch(
            "/api/v1/users/me",
            json={"email": "third@example.com", "nickname": "Third"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response3.status_code == 200
        assert response3.json()["email"] == "third@example.com"
        assert response3.json()["nickname"] == "Third"
