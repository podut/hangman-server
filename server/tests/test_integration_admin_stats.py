"""Integration tests for admin stats endpoint."""

import pytest
from fastapi.testclient import TestClient
from src.main import app


client = TestClient(app)


@pytest.fixture(scope="module")
def admin_user():
    """Create a user with admin privileges."""
    import uuid
    from src.main import user_repo
    
    email = f"admin_{uuid.uuid4().hex[:8]}@example.com"
    password = "Admin1234"
    
    # Register user
    response = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password
    })
    assert response.status_code == 201
    user_id = response.json()["user_id"]
    
    # Manually set admin flag (tests may create other users first)
    user = user_repo.get_by_id(user_id)
    user["is_admin"] = True
    user_repo.update(user_id, user)
    
    # Login to get token
    login_response = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password
    })
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    
    return {"email": email, "token": token, "user_id": user_id, "is_admin": True}


@pytest.fixture
def regular_user(admin_user):
    """Register a regular (non-admin) user. Depends on admin_user to ensure it's not the first user."""
    import uuid
    unique_id = uuid.uuid4().hex[:8]
    email = f"user_{unique_id}@example.com"
    password = "User1234"
    
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


@pytest.fixture
def populated_data(admin_user):
    """Create some test data for statistics."""
    token = admin_user["token"]
    
    # Create a session
    session_response = client.post(
        "/api/v1/sessions",
        json={"difficulty": "normal", "max_misses": 6, "dict_id": "dict_ro_basic"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert session_response.status_code == 201
    session_id = session_response.json()["session_id"]
    
    # Create a game
    game_response = client.post(
        f"/api/v1/sessions/{session_id}/games",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert game_response.status_code == 201
    
    return {"session_id": session_id}


class TestAdminStatsEndpoint:
    """Test suite for GET /api/v1/admin/stats endpoint."""
    
    def test_admin_stats_requires_auth(self):
        """Test that admin stats requires authentication."""
        response = client.get("/api/v1/admin/stats")
        assert response.status_code == 401
    
    def test_admin_stats_requires_admin_role(self, regular_user):
        """Test that admin stats requires admin role."""
        token = regular_user["token"]
        
        response = client.get(
            "/api/v1/admin/stats",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403
    
    def test_admin_stats_empty_system(self, admin_user):
        """Test admin stats when system is empty (only admin user exists)."""
        token = admin_user["token"]
        
        response = client.get(
            "/api/v1/admin/stats",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "users" in data
        assert "sessions" in data
        assert "games" in data
        assert "games_by_period" in data
        assert "performance" in data
        assert "most_active_users" in data
        
        # Verify user stats
        assert data["users"]["total"] >= 1  # At least admin
        assert data["users"]["admins"] >= 1
        
        # Verify stats structure exists (may have data from other tests)
        assert data["sessions"]["total"] >= 0  # May have sessions from other test modules
        assert data["games"]["total"] >= 0  # May have games from other test modules
    
    def test_admin_stats_with_data(self, admin_user, populated_data):
        """Test admin stats with some data."""
        token = admin_user["token"]
        
        response = client.get(
            "/api/v1/admin/stats",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have at least one user
        assert data["users"]["total"] >= 1
        
        # Should have at least one session
        assert data["sessions"]["total"] >= 1
        
        # Should have at least one game
        assert data["games"]["total"] >= 1
    
    def test_admin_stats_user_counts(self, admin_user, regular_user):
        """Test that admin stats correctly counts users."""
        token = admin_user["token"]
        
        response = client.get(
            "/api/v1/admin/stats",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have at least 2 users (admin + regular)
        assert data["users"]["total"] >= 2
        assert data["users"]["admins"] >= 1
        assert data["users"]["regular"] >= 1
        assert data["users"]["total"] == data["users"]["admins"] + data["users"]["regular"]
    
    def test_admin_stats_session_status(self, admin_user):
        """Test admin stats tracks session status correctly."""
        token = admin_user["token"]
        
        # Create an active session
        session_response = client.post(
            "/api/v1/sessions",
            json={"difficulty": "easy", "max_misses": 6, "dict_id": "dict_ro_basic"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert session_response.status_code == 201
        
        response = client.get(
            "/api/v1/admin/stats",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["sessions"]["total"] >= 1
        assert data["sessions"]["active"] >= 1
    
    def test_admin_stats_game_status(self, admin_user, populated_data):
        """Test admin stats tracks game status correctly."""
        token = admin_user["token"]
        
        response = client.get(
            "/api/v1/admin/stats",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify game status fields exist
        assert "won" in data["games"]
        assert "lost" in data["games"]
        assert "aborted" in data["games"]
        assert "in_progress" in data["games"]
        assert "win_rate" in data["games"]
        
        # Total games should match sum of statuses
        total_games = data["games"]["total"]
        sum_statuses = (
            data["games"]["won"] + 
            data["games"]["lost"] + 
            data["games"]["aborted"] + 
            data["games"]["in_progress"]
        )
        assert total_games == sum_statuses
    
    def test_admin_stats_games_by_period(self, admin_user, populated_data):
        """Test admin stats includes games by time period."""
        token = admin_user["token"]
        
        response = client.get(
            "/api/v1/admin/stats",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify period fields
        assert "today" in data["games_by_period"]
        assert "last_7_days" in data["games_by_period"]
        assert "last_30_days" in data["games_by_period"]
        
        # Games created today should be counted in all periods
        today = data["games_by_period"]["today"]
        week = data["games_by_period"]["last_7_days"]
        month = data["games_by_period"]["last_30_days"]
        
        # Today <= Week <= Month
        assert today <= week
        assert week <= month
    
    def test_admin_stats_performance_metrics(self, admin_user):
        """Test admin stats includes performance metrics."""
        token = admin_user["token"]
        
        response = client.get(
            "/api/v1/admin/stats",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "performance" in data
        assert "avg_game_duration_sec" in data["performance"]
        assert isinstance(data["performance"]["avg_game_duration_sec"], (int, float))
    
    def test_admin_stats_most_active_users(self, admin_user, populated_data):
        """Test admin stats includes most active users."""
        token = admin_user["token"]
        
        response = client.get(
            "/api/v1/admin/stats",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "most_active_users" in data
        assert isinstance(data["most_active_users"], list)
        
        # If there are active users, verify structure
        if data["most_active_users"]:
            user = data["most_active_users"][0]
            assert "user_id" in user
            assert "nickname" in user
            assert "game_count" in user
            assert isinstance(user["game_count"], int)
    
    def test_admin_stats_with_invalid_token(self):
        """Test admin stats with invalid token."""
        response = client.get(
            "/api/v1/admin/stats",
            headers={"Authorization": "Bearer invalid_token_12345"}
        )
        
        assert response.status_code == 401
    
    def test_admin_stats_comprehensive_structure(self, admin_user):
        """Test that admin stats returns comprehensive structure."""
        token = admin_user["token"]
        
        response = client.get(
            "/api/v1/admin/stats",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all top-level keys
        expected_keys = ["users", "sessions", "games", "games_by_period", "performance", "most_active_users"]
        for key in expected_keys:
            assert key in data, f"Missing key: {key}"
        
        # Verify users structure
        assert set(data["users"].keys()) == {"total", "admins", "regular"}
        
        # Verify sessions structure
        assert set(data["sessions"].keys()) == {"total", "active", "completed"}
        
        # Verify games structure
        assert "total" in data["games"]
        assert "won" in data["games"]
        assert "lost" in data["games"]
        assert "aborted" in data["games"]
        assert "in_progress" in data["games"]
        assert "win_rate" in data["games"]
        
        # Verify games_by_period structure
        assert set(data["games_by_period"].keys()) == {"today", "last_7_days", "last_30_days"}
        
        # Verify performance structure
        assert "avg_game_duration_sec" in data["performance"]
        
        # Verify most_active_users is a list
        assert isinstance(data["most_active_users"], list)
