"""Integration tests for Link header pagination (RFC 5988)."""

import pytest
import uuid
from fastapi.testclient import TestClient
from src.main import app


client = TestClient(app)


@pytest.fixture
def registered_user_with_session():
    """Register a user, create a session with games."""
    email = f"pagination_{uuid.uuid4().hex[:8]}@example.com"
    password = "Pagination1234"
    
    # Register
    client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password
    })
    
    # Login
    login_response = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password
    })
    token = login_response.json()["access_token"]
    
    # Create session
    session_response = client.post(
        "/api/v1/sessions",
        json={"difficulty": "normal", "max_misses": 6, "dict_id": "dict_ro_basic"},
        headers={"Authorization": f"Bearer {token}"}
    )
    session_id = session_response.json()["session_id"]
    
    # Create multiple games for pagination testing
    game_ids = []
    for _ in range(15):  # Create 15 games
        game_response = client.post(
            f"/api/v1/sessions/{session_id}/games",
            headers={"Authorization": f"Bearer {token}"}
        )
        if game_response.status_code == 201:
            game_ids.append(game_response.json()["game_id"])
    
    return {
        "token": token,
        "session_id": session_id,
        "game_ids": game_ids
    }


class TestLinkHeaderPagination:
    """Test suite for RFC 5988 Link headers in paginated endpoints."""
    
    def test_session_games_has_link_header(self, registered_user_with_session):
        """Test that GET /sessions/{id}/games includes Link header."""
        token = registered_user_with_session["token"]
        session_id = registered_user_with_session["session_id"]
        
        response = client.get(
            f"/api/v1/sessions/{session_id}/games?page=1&page_size=5",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        assert "Link" in response.headers
        
        link_header = response.headers["Link"]
        assert "rel=\"first\"" in link_header
        assert "rel=\"last\"" in link_header
        assert "rel=\"next\"" in link_header
        # No 'prev' on first page
        assert "rel=\"prev\"" not in link_header
    
    def test_session_games_link_header_structure(self, registered_user_with_session):
        """Test Link header has correct structure."""
        token = registered_user_with_session["token"]
        session_id = registered_user_with_session["session_id"]
        
        response = client.get(
            f"/api/v1/sessions/{session_id}/games?page=2&page_size=5",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        link_header = response.headers["Link"]
        
        # Should have all 4 links on middle page
        assert "rel=\"first\"" in link_header
        assert "rel=\"last\"" in link_header
        assert "rel=\"next\"" in link_header
        assert "rel=\"prev\"" in link_header
        
        # Check URL format
        assert f"/api/v1/sessions/{session_id}/games" in link_header
        assert "page=1" in link_header  # first page
        assert "page=3" in link_header  # next page
        assert "page_size=5" in link_header
    
    def test_session_games_last_page_no_next(self, registered_user_with_session):
        """Test that last page has no 'next' link."""
        token = registered_user_with_session["token"]
        session_id = registered_user_with_session["session_id"]
        
        # Request last page (15 games / 5 per page = 3 pages)
        response = client.get(
            f"/api/v1/sessions/{session_id}/games?page=3&page_size=5",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        link_header = response.headers["Link"]
        
        assert "rel=\"first\"" in link_header
        assert "rel=\"last\"" in link_header
        assert "rel=\"prev\"" in link_header
        # No 'next' on last page
        assert "rel=\"next\"" not in link_header
    
    def test_leaderboard_has_link_header(self):
        """Test that GET /leaderboard includes Link header."""
        response = client.get("/api/v1/leaderboard?page=1&limit=5")
        
        assert response.status_code == 200
        assert "Link" in response.headers
        
        link_header = response.headers["Link"]
        assert "rel=\"first\"" in link_header
        assert "rel=\"last\"" in link_header
        # Leaderboard should include query params in links
        assert "metric=composite_score" in link_header or "metric" in link_header
    
    def test_leaderboard_preserves_query_params(self):
        """Test that Link header preserves custom query parameters."""
        response = client.get("/api/v1/leaderboard?metric=win_rate&period=30d&page=1&limit=5")
        
        assert response.status_code == 200
        link_header = response.headers["Link"]
        
        # Check that custom params are preserved
        assert "metric=win_rate" in link_header
        assert "period=30d" in link_header
    
    def test_pagination_with_different_page_sizes(self, registered_user_with_session):
        """Test pagination with different page sizes."""
        token = registered_user_with_session["token"]
        session_id = registered_user_with_session["session_id"]
        
        # Test with page_size=10
        response = client.get(
            f"/api/v1/sessions/{session_id}/games?page=1&page_size=10",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        link_header = response.headers["Link"]
        assert "page_size=10" in link_header
    
    def test_link_header_urls_are_valid(self, registered_user_with_session):
        """Test that URLs in Link header are valid and accessible."""
        token = registered_user_with_session["token"]
        session_id = registered_user_with_session["session_id"]
        
        # Get first page
        response = client.get(
            f"/api/v1/sessions/{session_id}/games?page=1&page_size=5",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        link_header = response.headers["Link"]
        
        # Extract next link
        links = link_header.split(", ")
        next_link = None
        for link in links:
            if 'rel="next"' in link:
                # Extract URL between < and >
                next_link = link.split('>')[0].strip('<')
                break
        
        assert next_link is not None
        
        # Test that next link works
        # Extract path from full URL
        next_path = next_link.split("/api/v1/")[1] if "/api/v1/" in next_link else next_link
        next_response = client.get(
            f"/api/v1/{next_path}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert next_response.status_code == 200
    
    def test_link_header_format_rfc_5988(self, registered_user_with_session):
        """Test that Link header follows RFC 5988 format."""
        token = registered_user_with_session["token"]
        session_id = registered_user_with_session["session_id"]
        
        response = client.get(
            f"/api/v1/sessions/{session_id}/games?page=2&page_size=5",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        link_header = response.headers["Link"]
        
        # RFC 5988 format: <URL>; rel="relation"
        links = link_header.split(", ")
        for link in links:
            # Should start with '<'
            assert link.strip().startswith('<')
            # Should contain '>;'
            assert '>; rel=' in link
            # Should have quoted rel value
            assert 'rel="' in link
    
    def test_pagination_response_includes_metadata(self, registered_user_with_session):
        """Test that paginated responses include pagination metadata."""
        token = registered_user_with_session["token"]
        session_id = registered_user_with_session["session_id"]
        
        response = client.get(
            f"/api/v1/sessions/{session_id}/games?page=1&page_size=5",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check for pagination metadata
        assert "page" in data or "pagination" in data
        if "pagination" in data:
            assert "page" in data["pagination"]
            assert "page_size" in data["pagination"]
            assert "total" in data["pagination"] or "total_items" in data["pagination"]
