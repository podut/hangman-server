"""
Integration tests for Dictionary Admin endpoints.
Tests the full HTTP request/response cycle for dictionary management by admins.
"""

import pytest
from fastapi.testclient import TestClient
from src.main import app


@pytest.fixture
def client():
    """Provide a test client."""
    return TestClient(app)


@pytest.fixture
def admin_headers(client):
    """Provide authentication headers for admin user.
    
    First registered user becomes admin automatically.
    """
    # Register first user (becomes admin)
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "admin@example.com",
            "password": "Admin123!"
        }
    )
    
    # Login to get token
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@example.com",
            "password": "Admin123!"
        }
    )
    
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def regular_user_headers(client, admin_headers):
    """Provide authentication headers for regular (non-admin) user.
    
    Registers after admin, so won't have admin privileges.
    Depends on admin_headers to ensure admin is registered first.
    """
    # Register second user (not admin)
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "regular@example.com",
            "password": "Regular123!"
        }
    )
    
    # Login to get token
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "regular@example.com",
            "password": "Regular123!"
        }
    )
    
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.integration
class TestDictionaryAdminEndpoints:
    """Test dictionary admin endpoints (authorization and CRUD operations)."""
    
    def test_list_dictionaries_no_auth(self, client):
        """Test listing dictionaries without authentication."""
        response = client.get("/api/v1/admin/dictionaries")
        
        # Should require authentication
        assert response.status_code in [401, 403]
        
    def test_list_dictionaries_as_regular_user(self, client, regular_user_headers):
        """Test listing dictionaries as non-admin user (should be forbidden)."""
        response = client.get(
            "/api/v1/admin/dictionaries",
            headers=regular_user_headers
        )
        
        # Should require admin role
        assert response.status_code == 403
        data = response.json()
        assert "error" in data or "detail" in data
        
    def test_list_dictionaries_as_admin(self, client, admin_headers):
        """Test listing dictionaries as admin (should succeed)."""
        response = client.get(
            "/api/v1/admin/dictionaries",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "dictionaries" in data
        assert isinstance(data["dictionaries"], list)
        # Should have at least the default dictionary
        assert len(data["dictionaries"]) >= 1
        
    def test_get_dictionary_words_as_admin(self, client, admin_headers):
        """Test getting dictionary words as admin."""
        response = client.get(
            "/api/v1/admin/dictionaries/dict_ro_basic/words",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "words" in data
        assert isinstance(data["words"], list)
        assert len(data["words"]) > 0
        
    def test_get_dictionary_words_with_sample(self, client, admin_headers):
        """Test getting a sample of dictionary words."""
        response = client.get(
            "/api/v1/admin/dictionaries/dict_ro_basic/words?sample=5",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "words" in data
        assert isinstance(data["words"], list)
        assert len(data["words"]) <= 5
        
    def test_get_dictionary_words_not_found(self, client, admin_headers):
        """Test getting words from non-existent dictionary."""
        response = client.get(
            "/api/v1/admin/dictionaries/nonexistent/words",
            headers=admin_headers
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "error" in data or "detail" in data
        
    def test_create_dictionary_as_admin(self, client, admin_headers):
        """Test creating a new dictionary as admin."""
        response = client.post(
            "/api/v1/admin/dictionaries",
            headers=admin_headers,
            params={
                "name": "test_dict_create",
                "description": "Test dictionary for creation",
                "language": "ro",
                "difficulty": "medium"
            },
            json=["test", "word", "list", "create"]
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "test_dict_create"
        assert data["language"] == "ro"
        assert data["word_count"] == 4
        assert "dict_id" in data or "dictionary_id" in data
        
    def test_create_dictionary_duplicate(self, client, admin_headers):
        """Test creating dictionary with duplicate name."""
        # Create first dictionary
        client.post(
            "/api/v1/admin/dictionaries",
            headers=admin_headers,
            params={"name": "duplicate_test"},
            json=["word1", "word2"]
        )
        
        # Try to create with same name (will have same dict_id)
        response = client.post(
            "/api/v1/admin/dictionaries",
            headers=admin_headers,
            params={"name": "duplicate_test"},
            json=["word3", "word4"]
        )
        
        # Should fail with 400 or 409 (either is acceptable for duplicate)
        assert response.status_code in [400, 409]
        data = response.json()
        assert "error" in data or "detail" in data
        
    def test_create_dictionary_empty_words(self, client, admin_headers):
        """Test creating dictionary with no words (should fail)."""
        response = client.post(
            "/api/v1/admin/dictionaries",
            headers=admin_headers,
            params={"name": "empty_dict"},
            json=[]
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data or "detail" in data
        
    def test_create_dictionary_as_regular_user(self, client, regular_user_headers):
        """Test creating dictionary as non-admin (should be forbidden)."""
        response = client.post(
            "/api/v1/admin/dictionaries",
            headers=regular_user_headers,
            params={"name": "unauthorized_dict"},
            json=["test", "words"]
        )
        
        assert response.status_code == 403
        data = response.json()
        assert "error" in data or "detail" in data
        
    def test_update_dictionary_as_admin(self, client, admin_headers):
        """Test updating an existing dictionary."""
        # First create a dictionary
        create_response = client.post(
            "/api/v1/admin/dictionaries",
            headers=admin_headers,
            params={"name": "update_test"},
            json=["original", "words"]
        )
        assert create_response.status_code == 201
        # Get dict_id or dictionary_id from response
        created_data = create_response.json()
        dict_id = created_data.get("dict_id") or created_data.get("dictionary_id")
        
        # Update it
        response = client.patch(
            f"/api/v1/admin/dictionaries/{dict_id}",
            headers=admin_headers,
            params={
                "name": "updated_name",
                "description": "Updated description",
                "active": True
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "updated_name"
        assert data["description"] == "Updated description"
        
    def test_update_dictionary_deactivate(self, client, admin_headers):
        """Test deactivating a dictionary."""
        # First create a dictionary
        create_response = client.post(
            "/api/v1/admin/dictionaries",
            headers=admin_headers,
            params={"name": "deactivate_test"},
            json=["test", "words"]
        )
        assert create_response.status_code == 201
        # Get dict_id or dictionary_id from response
        created_data = create_response.json()
        dict_id = created_data.get("dict_id") or created_data.get("dictionary_id")
        
        # Deactivate it
        response = client.patch(
            f"/api/v1/admin/dictionaries/{dict_id}",
            headers=admin_headers,
            params={"active": False}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["active"] == False
        
    def test_update_dictionary_not_found(self, client, admin_headers):
        """Test updating non-existent dictionary (should return 404)."""
        response = client.patch(
            "/api/v1/admin/dictionaries/nonexistent_dict_id",
            headers=admin_headers,
            params={"name": "updated_name"}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "error" in data or "detail" in data
        
    def test_update_dictionary_as_regular_user(self, client, regular_user_headers):
        """Test updating dictionary as non-admin (should be forbidden)."""
        response = client.patch(
            "/api/v1/admin/dictionaries/dict_ro_basic",
            headers=regular_user_headers,
            params={"name": "hacked_name"}
        )
        
        assert response.status_code == 403
        data = response.json()
        assert "error" in data or "detail" in data
