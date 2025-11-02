"""Integration tests for user data export endpoint (GDPR compliance)."""

import pytest
from fastapi.testclient import TestClient
from server.src.main import app


client = TestClient(app)


@pytest.fixture
def registered_user():
    """Register a user and return credentials."""
    import uuid
    email = f"export_{uuid.uuid4().hex[:8]}@example.com"
    password = "Export1234"
    
    response = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "nickname": "ExportTestUser"
    })
    assert response.status_code == 201
    
    login_response = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password
    })
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    user_id = login_response.json()["user_id"]
    
    return {"email": email, "token": token, "user_id": user_id}


@pytest.fixture
def user_with_data(registered_user):
    """Create a user with sessions and games."""
    token = registered_user["token"]
    
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
    game_id = game_response.json()["game_id"]
    
    return {
        **registered_user,
        "session_id": session_id,
        "game_id": game_id
    }


class TestUserDataExport:
    """Test suite for GET /api/v1/users/me/export endpoint."""
    
    def test_export_requires_auth(self):
        """Test that export requires authentication."""
        response = client.get("/api/v1/users/me/export")
        assert response.status_code == 401
    
    def test_export_with_invalid_token(self):
        """Test that export rejects invalid tokens."""
        response = client.get(
            "/api/v1/users/me/export",
            headers={"Authorization": "Bearer invalid_token_here"}
        )
        assert response.status_code == 401
    
    def test_export_empty_user(self, registered_user):
        """Test export for user with no sessions or games."""
        token = registered_user["token"]
        user_id = registered_user["user_id"]
        
        response = client.get(
            "/api/v1/users/me/export",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check structure
        assert "export_date" in data
        assert "user_id" in data
        assert "profile" in data
        assert "sessions" in data
        assert "games" in data
        assert "statistics" in data
        assert "metadata" in data
        
        # Check user_id
        assert data["user_id"] == user_id
        
        # Check empty collections
        assert isinstance(data["sessions"], list)
        assert len(data["sessions"]) == 0
        assert isinstance(data["games"], list)
        assert len(data["games"]) == 0
    
    def test_export_with_data(self, user_with_data):
        """Test export for user with sessions and games."""
        token = user_with_data["token"]
        user_id = user_with_data["user_id"]
        session_id = user_with_data["session_id"]
        game_id = user_with_data["game_id"]
        
        response = client.get(
            "/api/v1/users/me/export",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check user_id
        assert data["user_id"] == user_id
        
        # Check sessions
        assert len(data["sessions"]) >= 1
        session_ids = [s["session_id"] for s in data["sessions"]]
        assert session_id in session_ids
        
        # Check games
        assert len(data["games"]) >= 1
        game_ids = [g["game_id"] for g in data["games"]]
        assert game_id in game_ids
    
    def test_export_profile_no_password(self, registered_user):
        """Test that export does not include password."""
        token = registered_user["token"]
        
        response = client.get(
            "/api/v1/users/me/export",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check profile exists
        assert "profile" in data
        profile = data["profile"]
        
        # Check profile has expected fields
        assert "email" in profile
        assert "nickname" in profile
        assert "user_id" in profile
        
        # Check password is NOT included
        assert "password" not in profile
    
    def test_export_includes_statistics(self, user_with_data):
        """Test that export includes user statistics."""
        token = user_with_data["token"]
        
        response = client.get(
            "/api/v1/users/me/export",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check statistics structure
        assert "statistics" in data
        stats = data["statistics"]
        
        # Stats should have basic structure
        assert "total_games" in stats
        assert "games_won" in stats
        assert "games_lost" in stats
        assert isinstance(stats["total_games"], int)
    
    def test_export_metadata_includes_gdpr_reference(self, registered_user):
        """Test that export metadata references GDPR compliance."""
        token = registered_user["token"]
        
        response = client.get(
            "/api/v1/users/me/export",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check metadata
        assert "metadata" in data
        metadata = data["metadata"]
        
        assert "total_sessions" in metadata
        assert "total_games" in metadata
        assert "data_format" in metadata
        assert "gdpr_compliance" in metadata
        
        # Check GDPR reference
        assert "Article 20" in metadata["gdpr_compliance"]
        assert metadata["data_format"] == "JSON"
    
    def test_export_includes_all_sessions(self, registered_user):
        """Test that export includes all user sessions."""
        token = registered_user["token"]
        
        # Create multiple sessions
        session_ids = []
        for i in range(3):
            session_response = client.post(
                "/api/v1/sessions",
                json={"difficulty": "easy", "max_misses": 6, "dict_id": "dict_ro_basic"},
                headers={"Authorization": f"Bearer {token}"}
            )
            assert session_response.status_code == 201
            session_ids.append(session_response.json()["session_id"])
        
        # Export data
        response = client.get(
            "/api/v1/users/me/export",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check all sessions are included
        exported_session_ids = [s["session_id"] for s in data["sessions"]]
        for sid in session_ids:
            assert sid in exported_session_ids
        
        # Check metadata count
        assert data["metadata"]["total_sessions"] >= 3
    
    def test_export_includes_all_games(self, registered_user):
        """Test that export includes all user games across all sessions."""
        token = registered_user["token"]
        
        # Create session
        session_response = client.post(
            "/api/v1/sessions",
            json={"difficulty": "normal", "max_misses": 6, "dict_id": "dict_ro_basic"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert session_response.status_code == 201
        session_id = session_response.json()["session_id"]
        
        # Create multiple games
        game_ids = []
        for i in range(3):
            game_response = client.post(
                f"/api/v1/sessions/{session_id}/games",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert game_response.status_code == 201
            game_ids.append(game_response.json()["game_id"])
        
        # Export data
        response = client.get(
            "/api/v1/users/me/export",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check all games are included
        exported_game_ids = [g["game_id"] for g in data["games"]]
        for gid in game_ids:
            assert gid in exported_game_ids
        
        # Check metadata count
        assert data["metadata"]["total_games"] >= 3
    
    def test_export_data_format_is_json_serializable(self, user_with_data):
        """Test that exported data is valid JSON."""
        token = user_with_data["token"]
        
        response = client.get(
            "/api/v1/users/me/export",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check that all top-level keys are present and serializable
        assert isinstance(data["export_date"], str)
        assert isinstance(data["user_id"], str)
        assert isinstance(data["profile"], dict)
        assert isinstance(data["sessions"], list)
        assert isinstance(data["games"], list)
        assert isinstance(data["statistics"], dict)
        assert isinstance(data["metadata"], dict)
    
    def test_export_only_own_data(self, registered_user):
        """Test that users can only export their own data."""
        # Create first user with data
        token1 = registered_user["token"]
        user_id1 = registered_user["user_id"]
        
        # Create a session for first user
        session_response = client.post(
            "/api/v1/sessions",
            json={"difficulty": "normal", "max_misses": 6, "dict_id": "dict_ro_basic"},
            headers={"Authorization": f"Bearer {token1}"}
        )
        assert session_response.status_code == 201
        session_id1 = session_response.json()["session_id"]
        
        # Create second user
        import uuid
        email2 = f"export2_{uuid.uuid4().hex[:8]}@example.com"
        client.post("/api/v1/auth/register", json={
            "email": email2,
            "password": "Export1234"
        })
        login_response2 = client.post("/api/v1/auth/login", json={
            "email": email2,
            "password": "Export1234"
        })
        token2 = login_response2.json()["access_token"]
        user_id2 = login_response2.json()["user_id"]
        
        # Export data for second user
        response = client.get(
            "/api/v1/users/me/export",
            headers={"Authorization": f"Bearer {token2}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check that only second user's data is exported
        assert data["user_id"] == user_id2
        assert data["user_id"] != user_id1
        
        # Second user should have no sessions (first user's session should not appear)
        session_ids = [s["session_id"] for s in data["sessions"]]
        assert session_id1 not in session_ids
