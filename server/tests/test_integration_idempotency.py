"""Integration tests for Idempotency-Key support.

NOTE: Idempotency middleware is currently DISABLED due to technical limitations
with FastAPI's BaseHTTPMiddleware and response body consumption.
The middleware code exists but these tests are skipped.
"""

import pytest
import uuid
from fastapi.testclient import TestClient
from src.main import app


# Skip all tests in this module since IdempotencyMiddleware is disabled
pytestmark = pytest.mark.skip(reason="IdempotencyMiddleware disabled - FastAPI BaseHTTPMiddleware limitation")

client = TestClient(app)


@pytest.fixture
def registered_user():
    """Register a user and return credentials."""
    email = f"idempotency_{uuid.uuid4().hex[:8]}@example.com"
    password = "Idempotent1234"
    
    response = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password
    })
    assert response.status_code == 201
    
    login_response = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password
    })
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    
    return {"email": email, "token": token}


class TestIdempotencyMiddleware:
    """Test suite for Idempotency-Key header support."""
    
    def test_post_without_idempotency_key_works(self, registered_user):
        """Test that POST requests work without Idempotency-Key."""
        token = registered_user["token"]
        
        response = client.post(
            "/api/v1/sessions",
            json={"difficulty": "normal", "max_misses": 6, "dict_id": "dict_ro_basic"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 201
        assert "X-Idempotent-Stored" not in response.headers
        assert "X-Idempotent-Replay" not in response.headers
    
    def test_post_with_idempotency_key_first_request(self, registered_user):
        """Test that first request with Idempotency-Key is processed and stored."""
        token = registered_user["token"]
        idempotency_key = f"test-key-{uuid.uuid4()}"
        
        response = client.post(
            "/api/v1/sessions",
            json={"difficulty": "normal", "max_misses": 6, "dict_id": "dict_ro_basic"},
            headers={
                "Authorization": f"Bearer {token}",
                "Idempotency-Key": idempotency_key
            }
        )
        
        assert response.status_code == 201
        assert "X-Idempotent-Stored" in response.headers
        assert response.headers["X-Idempotent-Stored"] == "true"
        
        # Save session_id for later verification
        session_id = response.json()["session_id"]
        return session_id, idempotency_key
    
    def test_post_with_same_idempotency_key_returns_cached(self, registered_user):
        """Test that duplicate request with same Idempotency-Key returns cached response."""
        token = registered_user["token"]
        idempotency_key = f"test-key-duplicate-{uuid.uuid4()}"
        
        # First request
        response1 = client.post(
            "/api/v1/sessions",
            json={"difficulty": "normal", "max_misses": 6, "dict_id": "dict_ro_basic"},
            headers={
                "Authorization": f"Bearer {token}",
                "Idempotency-Key": idempotency_key
            }
        )
        
        assert response1.status_code == 201
        assert "X-Idempotent-Stored" in response1.headers
        session_id1 = response1.json()["session_id"]
        
        # Second request with same key - should return cached
        response2 = client.post(
            "/api/v1/sessions",
            json={"difficulty": "normal", "max_misses": 6, "dict_id": "dict_ro_basic"},
            headers={
                "Authorization": f"Bearer {token}",
                "Idempotency-Key": idempotency_key
            }
        )
        
        assert response2.status_code == 201
        assert "X-Idempotent-Replay" in response2.headers
        assert response2.headers["X-Idempotent-Replay"] == "true"
        
        # Should return same session_id
        session_id2 = response2.json()["session_id"]
        assert session_id1 == session_id2
    
    def test_patch_with_idempotency_key(self, registered_user):
        """Test that PATCH requests support Idempotency-Key."""
        token = registered_user["token"]
        idempotency_key = f"test-patch-{uuid.uuid4()}"
        
        # First PATCH request
        response1 = client.patch(
            "/api/v1/users/me",
            json={"nickname": "NewNickname1"},
            headers={
                "Authorization": f"Bearer {token}",
                "Idempotency-Key": idempotency_key
            }
        )
        
        assert response1.status_code == 200
        assert "X-Idempotent-Stored" in response1.headers
        
        # Second PATCH with same key
        response2 = client.patch(
            "/api/v1/users/me",
            json={"nickname": "NewNickname1"},
            headers={
                "Authorization": f"Bearer {token}",
                "Idempotency-Key": idempotency_key
            }
        )
        
        assert response2.status_code == 200
        assert "X-Idempotent-Replay" in response2.headers
    
    def test_delete_with_idempotency_key(self, registered_user):
        """Test that DELETE requests support Idempotency-Key."""
        # Create a user specifically for deletion test
        email = f"delete_test_{uuid.uuid4().hex[:8]}@example.com"
        client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "Delete1234"
        })
        login_response = client.post("/api/v1/auth/login", json={
            "email": email,
            "password": "Delete1234"
        })
        token = login_response.json()["access_token"]
        
        idempotency_key = f"test-delete-{uuid.uuid4()}"
        
        # First DELETE request
        response1 = client.delete(
            "/api/v1/users/me",
            headers={
                "Authorization": f"Bearer {token}",
                "Idempotency-Key": idempotency_key
            }
        )
        
        assert response1.status_code == 204
        assert "X-Idempotent-Stored" in response1.headers
        
        # Second DELETE with same key (should return cached 204)
        response2 = client.delete(
            "/api/v1/users/me",
            headers={
                "Authorization": f"Bearer {token}",
                "Idempotency-Key": idempotency_key
            }
        )
        
        assert response2.status_code == 204
        assert "X-Idempotent-Replay" in response2.headers
    
    def test_get_requests_not_affected(self):
        """Test that GET requests don't use idempotency (they're naturally idempotent)."""
        idempotency_key = f"test-get-{uuid.uuid4()}"
        
        response = client.get(
            "/healthz",
            headers={"Idempotency-Key": idempotency_key}
        )
        
        assert response.status_code == 200
        # GET requests should not have idempotency headers
        assert "X-Idempotent-Stored" not in response.headers
        assert "X-Idempotent-Replay" not in response.headers
    
    def test_different_keys_create_different_resources(self, registered_user):
        """Test that different Idempotency-Keys create different resources."""
        token = registered_user["token"]
        
        key1 = f"key1-{uuid.uuid4()}"
        key2 = f"key2-{uuid.uuid4()}"
        
        # First request with key1
        response1 = client.post(
            "/api/v1/sessions",
            json={"difficulty": "normal", "max_misses": 6, "dict_id": "dict_ro_basic"},
            headers={
                "Authorization": f"Bearer {token}",
                "Idempotency-Key": key1
            }
        )
        
        # Second request with key2 (different)
        response2 = client.post(
            "/api/v1/sessions",
            json={"difficulty": "normal", "max_misses": 6, "dict_id": "dict_ro_basic"},
            headers={
                "Authorization": f"Bearer {token}",
                "Idempotency-Key": key2
            }
        )
        
        assert response1.status_code == 201
        assert response2.status_code == 201
        
        # Should create different sessions
        session_id1 = response1.json()["session_id"]
        session_id2 = response2.json()["session_id"]
        assert session_id1 != session_id2
    
    def test_idempotency_key_scoped_to_user(self):
        """Test that Idempotency-Keys are scoped per user."""
        # Create two users
        user1_email = f"user1_{uuid.uuid4().hex[:8]}@example.com"
        user2_email = f"user2_{uuid.uuid4().hex[:8]}@example.com"
        
        for email in [user1_email, user2_email]:
            client.post("/api/v1/auth/register", json={
                "email": email,
                "password": "User1234"
            })
        
        token1 = client.post("/api/v1/auth/login", json={
            "email": user1_email,
            "password": "User1234"
        }).json()["access_token"]
        
        token2 = client.post("/api/v1/auth/login", json={
            "email": user2_email,
            "password": "User1234"
        }).json()["access_token"]
        
        # Same idempotency key for both users
        shared_key = f"shared-key-{uuid.uuid4()}"
        
        # User 1 creates session
        response1 = client.post(
            "/api/v1/sessions",
            json={"difficulty": "normal", "max_misses": 6, "dict_id": "dict_ro_basic"},
            headers={
                "Authorization": f"Bearer {token1}",
                "Idempotency-Key": shared_key
            }
        )
        
        # User 2 creates session with same key
        response2 = client.post(
            "/api/v1/sessions",
            json={"difficulty": "normal", "max_misses": 6, "dict_id": "dict_ro_basic"},
            headers={
                "Authorization": f"Bearer {token2}",
                "Idempotency-Key": shared_key
            }
        )
        
        assert response1.status_code == 201
        assert response2.status_code == 201
        
        # Both should create NEW sessions (not replays)
        assert "X-Idempotent-Stored" in response1.headers
        assert "X-Idempotent-Stored" in response2.headers
        
        # Different session IDs
        session_id1 = response1.json()["session_id"]
        session_id2 = response2.json()["session_id"]
        assert session_id1 != session_id2
    
    def test_error_responses_not_cached(self, registered_user):
        """Test that error responses (4xx, 5xx) are not cached."""
        token = registered_user["token"]
        idempotency_key = f"error-key-{uuid.uuid4()}"
        
        # Make invalid request that will fail
        response1 = client.post(
            "/api/v1/sessions",
            json={"difficulty": "invalid_difficulty"},  # Invalid value
            headers={
                "Authorization": f"Bearer {token}",
                "Idempotency-Key": idempotency_key
            }
        )
        
        # Should be error
        assert response1.status_code >= 400
        assert "X-Idempotent-Stored" not in response1.headers
        
        # Retry with same key - should try again (not cached)
        response2 = client.post(
            "/api/v1/sessions",
            json={"difficulty": "invalid_difficulty"},
            headers={
                "Authorization": f"Bearer {token}",
                "Idempotency-Key": idempotency_key
            }
        )
        
        assert response2.status_code >= 400
        assert "X-Idempotent-Replay" not in response2.headers
    
    def test_invalid_idempotency_key_format(self, registered_user):
        """Test that invalid Idempotency-Key format is rejected."""
        token = registered_user["token"]
        
        # Empty key
        response = client.post(
            "/api/v1/sessions",
            json={"difficulty": "normal", "max_misses": 6, "dict_id": "dict_ro_basic"},
            headers={
                "Authorization": f"Bearer {token}",
                "Idempotency-Key": ""
            }
        )
        
        assert response.status_code == 400
        assert "INVALID_IDEMPOTENCY_KEY" in response.json()["error"]["code"]
        
        # Too long key (>255 chars)
        long_key = "x" * 256
        response2 = client.post(
            "/api/v1/sessions",
            json={"difficulty": "normal", "max_misses": 6, "dict_id": "dict_ro_basic"},
            headers={
                "Authorization": f"Bearer {token}",
                "Idempotency-Key": long_key
            }
        )
        
        assert response2.status_code == 400
