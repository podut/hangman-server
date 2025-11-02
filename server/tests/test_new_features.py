"""Tests for new features: WebSocket, /metrics, idempotency, OpenAPI export."""

import pytest
import asyncio
import json
from fastapi.testclient import TestClient
from websockets import connect as ws_connect, ConnectionClosedError
import httpx

# Import the app
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.main import app
from src.config import settings


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    """Get authentication headers for testing."""
    # Register a test user
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "test_features@example.com",
            "password": "Test123!",
            "nickname": "TestFeatures"
        }
    )
    
    if register_response.status_code == 201:
        # Login to get token
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test_features@example.com",
                "password": "Test123!"
            }
        )
        token = login_response.json()["access_token"]
    else:
        # User already exists, just login
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test_features@example.com",
                "password": "Test123!"
            }
        )
        token = login_response.json()["access_token"]
    
    return {"Authorization": f"Bearer {token}"}


# ============= WEBSOCKET TESTS =============

@pytest.mark.asyncio
async def test_websocket_connection_without_token():
    """Test WebSocket connection fails without authentication token."""
    try:
        async with ws_connect(f"ws://localhost:{settings.server_port}/ws") as websocket:
            # Should not reach here
            assert False, "WebSocket should reject connection without token"
    except ConnectionClosedError as e:
        # Expected: connection should be closed with auth error
        assert e.code == 1008  # Policy violation
        assert "Authentication required" in str(e.reason) or e.reason is None


@pytest.mark.asyncio
async def test_websocket_connection_with_invalid_token():
    """Test WebSocket connection fails with invalid token."""
    try:
        async with ws_connect(f"ws://localhost:{settings.server_port}/ws?token=invalid_token") as websocket:
            # Should not reach here
            assert False, "WebSocket should reject invalid token"
    except ConnectionClosedError as e:
        # Expected: connection should be closed
        assert e.code == 1008  # Policy violation


@pytest.mark.asyncio
async def test_websocket_connection_with_valid_token(client, auth_headers):
    """Test WebSocket connection succeeds with valid token."""
    token = auth_headers["Authorization"].split()[1]
    
    try:
        async with ws_connect(f"ws://localhost:{settings.server_port}/ws?token={token}") as websocket:
            # Should receive welcome message
            message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            data = json.loads(message)
            
            assert data["type"] == "connected"
            assert "user_id" in data["data"]
            assert data["data"]["message"] == "WebSocket connection established"
            
    except asyncio.TimeoutError:
        pytest.fail("Did not receive welcome message within timeout")
    except Exception as e:
        pytest.fail(f"WebSocket connection failed: {e}")


@pytest.mark.asyncio
async def test_websocket_ping_pong(client, auth_headers):
    """Test WebSocket ping/pong mechanism."""
    token = auth_headers["Authorization"].split()[1]
    
    async with ws_connect(f"ws://localhost:{settings.server_port}/ws?token={token}") as websocket:
        # Skip welcome message
        await websocket.recv()
        
        # Send ping
        await websocket.send(json.dumps({"type": "ping", "data": {}}))
        
        # Receive pong
        message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
        data = json.loads(message)
        
        assert data["type"] == "pong"
        assert "timestamp" in data["data"]


@pytest.mark.asyncio
async def test_websocket_subscribe(client, auth_headers):
    """Test WebSocket subscribe mechanism."""
    token = auth_headers["Authorization"].split()[1]
    
    async with ws_connect(f"ws://localhost:{settings.server_port}/ws?token={token}") as websocket:
        # Skip welcome message
        await websocket.recv()
        
        # Subscribe to channel
        await websocket.send(json.dumps({
            "type": "subscribe",
            "data": {"channel": "games"}
        }))
        
        # Receive subscription confirmation
        message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
        data = json.loads(message)
        
        assert data["type"] == "subscribed"
        assert data["data"]["channel"] == "games"


# ============= PROMETHEUS /METRICS TESTS =============

def test_metrics_endpoint_exists(client):
    """Test that /metrics endpoint exists and returns data."""
    response = client.get("/metrics")
    
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    
    # Check for Prometheus metrics format
    content = response.text
    assert "# HELP" in content or "# TYPE" in content or "http_" in content
    
    # Check for common metrics
    # Note: Some metrics may not appear until after requests are made
    # So we just check the endpoint works


def test_metrics_after_requests(client, auth_headers):
    """Test that /metrics includes data after making requests."""
    # Make some requests to generate metrics
    client.get("/healthz")
    client.get("/version")
    client.get("/api/v1/sessions", headers=auth_headers)
    
    # Get metrics
    response = client.get("/metrics")
    
    assert response.status_code == 200
    content = response.text
    
    # Check for HTTP request metrics (these should exist after instrumentator is set up)
    # The exact metric names depend on prometheus-fastapi-instrumentator version
    assert len(content) > 100  # Should have substantial content


def test_metrics_not_rate_limited(client):
    """Test that /metrics endpoint is not rate-limited."""
    # Make many requests to /metrics
    for _ in range(150):  # More than rate limit (60 req/min)
        response = client.get("/metrics")
        assert response.status_code == 200
    
    # Should not be rate limited
    final_response = client.get("/metrics")
    assert final_response.status_code == 200


# ============= IDEMPOTENCY TESTS =============

def test_create_session_without_idempotency_key(client, auth_headers):
    """Test creating session without idempotency key creates multiple sessions."""
    session_data = {
        "num_games": 1,
        "dictionary_id": "dict_ro_basic",
        "difficulty": "easy"
    }
    
    # Create first session
    response1 = client.post("/api/v1/sessions", json=session_data, headers=auth_headers)
    assert response1.status_code == 201
    session1_id = response1.json()["session_id"]
    
    # Create second session (should create new one)
    response2 = client.post("/api/v1/sessions", json=session_data, headers=auth_headers)
    assert response2.status_code == 201
    session2_id = response2.json()["session_id"]
    
    # Should be different sessions
    assert session1_id != session2_id


def test_create_session_with_idempotency_key(client, auth_headers):
    """Test creating session with idempotency key returns same session."""
    session_data = {
        "num_games": 1,
        "dictionary_id": "dict_ro_basic",
        "difficulty": "easy"
    }
    
    headers_with_idem = {
        **auth_headers,
        "Idempotency-Key": "test-session-123"
    }
    
    # Create first session
    response1 = client.post("/api/v1/sessions", json=session_data, headers=headers_with_idem)
    assert response1.status_code == 201
    session1_id = response1.json()["session_id"]
    
    # Create second session with same idempotency key (should return first)
    response2 = client.post("/api/v1/sessions", json=session_data, headers=headers_with_idem)
    assert response2.status_code == 201
    session2_id = response2.json()["session_id"]
    
    # Should be same session (idempotency replayed)
    assert session1_id == session2_id


def test_create_game_with_idempotency_key(client, auth_headers):
    """Test creating game with idempotency key returns same game."""
    # First create a session
    session_response = client.post(
        "/api/v1/sessions",
        json={"num_games": 5, "dictionary_id": "dict_ro_basic", "difficulty": "easy"},
        headers=auth_headers
    )
    session_id = session_response.json()["session_id"]
    
    headers_with_idem = {
        **auth_headers,
        "Idempotency-Key": "test-game-456"
    }
    
    # Create first game
    response1 = client.post(
        f"/api/v1/sessions/{session_id}/games",
        headers=headers_with_idem
    )
    assert response1.status_code == 201
    game1_id = response1.json()["game_id"]
    
    # Create second game with same idempotency key (should return first)
    response2 = client.post(
        f"/api/v1/sessions/{session_id}/games",
        headers=headers_with_idem
    )
    assert response2.status_code == 201
    game2_id = response2.json()["game_id"]
    
    # Should be same game
    assert game1_id == game2_id


def test_idempotency_different_users(client):
    """Test that idempotency keys are scoped per user."""
    # Register two users
    client.post("/api/v1/auth/register", json={
        "email": "user1_idem@example.com",
        "password": "Test123!",
        "nickname": "User1Idem"
    })
    
    client.post("/api/v1/auth/register", json={
        "email": "user2_idem@example.com",
        "password": "Test123!",
        "nickname": "User2Idem"
    })
    
    # Get tokens for both users
    token1 = client.post("/api/v1/auth/login", json={
        "email": "user1_idem@example.com",
        "password": "Test123!"
    }).json()["access_token"]
    
    token2 = client.post("/api/v1/auth/login", json={
        "email": "user2_idem@example.com",
        "password": "Test123!"
    }).json()["access_token"]
    
    # Use same idempotency key for both users
    idem_key = "shared-key-789"
    
    headers1 = {"Authorization": f"Bearer {token1}", "Idempotency-Key": idem_key}
    headers2 = {"Authorization": f"Bearer {token2}", "Idempotency-Key": idem_key}
    
    session_data = {"num_games": 1, "dictionary_id": "dict_ro_basic", "difficulty": "easy"}
    
    # Create session for user1
    response1 = client.post("/api/v1/sessions", json=session_data, headers=headers1)
    session1_id = response1.json()["session_id"]
    
    # Create session for user2 (should create different session despite same key)
    response2 = client.post("/api/v1/sessions", json=session_data, headers=headers2)
    session2_id = response2.json()["session_id"]
    
    # Should be different sessions (keys are scoped per user)
    assert session1_id != session2_id


# ============= OPENAPI EXPORT TESTS =============

def test_openapi_json_endpoint(client):
    """Test that OpenAPI JSON is available at /openapi.json."""
    response = client.get("/openapi.json")
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    
    data = response.json()
    assert "openapi" in data
    assert "info" in data
    assert "paths" in data
    assert data["info"]["title"] == "Hangman Server API"


def test_openapi_docs_endpoint(client):
    """Test that Swagger UI is available at /docs."""
    response = client.get("/docs")
    
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert b"Swagger UI" in response.content or b"swagger" in response.content.lower()


def test_export_openapi_script():
    """Test that export_openapi.py script can be imported and run."""
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from export_openapi import export_openapi_spec
        
        # Run export (will create files in docs/)
        export_openapi_spec()
        
        # Check that files were created
        docs_dir = Path(__file__).parent.parent.parent / "docs"
        assert (docs_dir / "openapi.json").exists()
        
        # Check if YAML was created (depends on PyYAML)
        yaml_file = docs_dir / "openapi.yaml"
        if yaml_file.exists():
            # Verify it's valid YAML
            import yaml
            with open(yaml_file, "r") as f:
                yaml_data = yaml.safe_load(f)
            assert "openapi" in yaml_data
            assert "paths" in yaml_data
        
    except ImportError as e:
        pytest.skip(f"Could not import export script: {e}")


# ============= TLS CONFIGURATION TESTS =============

def test_tls_config_disabled_by_default():
    """Test that TLS is disabled by default."""
    from src.config import settings
    
    assert settings.ssl_enabled == False
    assert settings.ssl_keyfile == ""
    assert settings.ssl_certfile == ""


def test_tls_config_can_be_enabled():
    """Test that TLS configuration can be set."""
    from src.config import Settings
    
    # Create settings with TLS enabled
    tls_settings = Settings(
        ssl_enabled=True,
        ssl_keyfile="certs/key.pem",
        ssl_certfile="certs/cert.pem"
    )
    
    assert tls_settings.ssl_enabled == True
    assert tls_settings.ssl_keyfile == "certs/key.pem"
    assert tls_settings.ssl_certfile == "certs/cert.pem"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
