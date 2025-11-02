"""
Pytest fixtures for Hangman server tests.
Provides reusable test setup including mock repositories, services, and FastAPI test client.
"""

import pytest
import sys
import os
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
from fastapi.testclient import TestClient

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set DEBUG mode for tests to bypass validation
os.environ["DEBUG"] = "true"

from src.main import app
from src.config import settings


@pytest.fixture(autouse=True)
def disable_rate_limiting():
    """Disable rate limiting for all tests."""
    original_value = settings.disable_rate_limiting
    settings.disable_rate_limiting = True
    yield
    settings.disable_rate_limiting = original_value
from src.repositories.user_repository import UserRepository
from src.repositories.session_repository import SessionRepository
from src.repositories.game_repository import GameRepository
from src.repositories.dictionary_repository import DictionaryRepository
from src.services.auth_service import AuthService
from src.services.session_service import SessionService
from src.services.game_service import GameService
from src.services.stats_service import StatsService
from src.services.dictionary_service import DictionaryService
from src.utils.auth_utils import create_access_token


class MockUserRepository(UserRepository):
    """Mock user repository for testing."""
    
    def __init__(self):
        self.users: Dict[str, Dict[str, Any]] = {}
        self.next_id = 1
    
    def create(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        self.users[user_data["user_id"]] = user_data
        return user_data
    
    def get_by_id(self, user_id: str) -> Dict[str, Any] | None:
        return self.users.get(user_id)
    
    def get_by_email(self, email: str) -> Dict[str, Any] | None:
        for user in self.users.values():
            if user["email"] == email:
                return user
        return None
    
    def get_all(self) -> List[Dict[str, Any]]:
        return list(self.users.values())
    
    def update(self, user_id: str, user_data: Dict[str, Any]) -> Dict[str, Any] | None:
        if user_id in self.users:
            self.users[user_id].update(user_data)
            return self.users[user_id]
        return None
    
    def delete(self, user_id: str) -> bool:
        if user_id in self.users:
            del self.users[user_id]
            return True
        return False
    
    def count(self) -> int:
        return len(self.users)


class MockSessionRepository(SessionRepository):
    """Mock session repository for testing."""
    
    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.next_id = 1
    
    def create(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        self.sessions[session_data["session_id"]] = session_data
        return session_data
    
    def get_by_id(self, session_id: str) -> Dict[str, Any] | None:
        return self.sessions.get(session_id)
    
    def get_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        return [s for s in self.sessions.values() if s["user_id"] == user_id]
    
    def get_all(self) -> List[Dict[str, Any]]:
        return list(self.sessions.values())
    
    def update(self, session_id: str, session_data: Dict[str, Any]) -> Dict[str, Any] | None:
        if session_id in self.sessions:
            self.sessions[session_id].update(session_data)
            return self.sessions[session_id]
        return None
    
    def delete(self, session_id: str) -> bool:
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
    
    def count(self) -> int:
        return len(self.sessions)


class MockGameRepository(GameRepository):
    """Mock game repository for testing."""
    
    def __init__(self):
        self.games: Dict[str, Dict[str, Any]] = {}
        self._guesses: Dict[str, List[Dict[str, Any]]] = {}
        self.next_id = 1
    
    def create(self, game_data: Dict[str, Any]) -> Dict[str, Any]:
        self.games[game_data["game_id"]] = game_data
        return game_data
    
    def get_by_id(self, game_id: str) -> Dict[str, Any] | None:
        return self.games.get(game_id)
    
    def get_by_session(self, session_id: str) -> List[Dict[str, Any]]:
        return [g for g in self.games.values() if g["session_id"] == session_id]
    
    def get_all(self) -> List[Dict[str, Any]]:
        return list(self.games.values())
    
    def update(self, game_id: str, game_data: Dict[str, Any]) -> Dict[str, Any] | None:
        if game_id in self.games:
            self.games[game_id].update(game_data)
            return self.games[game_id]
        return None
    
    def delete(self, game_id: str) -> bool:
        if game_id in self.games:
            del self.games[game_id]
            return True
        return False
    
    def count(self) -> int:
        return len(self.games)


class MockDictionaryRepository(DictionaryRepository):
    """Mock dictionary repository for testing."""
    
    def __init__(self):
        self.dictionaries: Dict[str, Dict[str, Any]] = {
            "dict_ro_basic": {
                "dictionary_id": "dict_ro_basic",
                "name": "Romanian Basic",
                "language": "ro",
                "words": ["python", "testing", "programming", "computer", "keyboard"],
                "active": True,
                "created_at": datetime.utcnow().isoformat() + "Z"
            }
        }
        self.next_id = 2
    
    def create(self, dict_data: Dict[str, Any]) -> Dict[str, Any]:
        self.dictionaries[dict_data["dictionary_id"]] = dict_data
        return dict_data
    
    def get_by_id(self, dictionary_id: str) -> Dict[str, Any] | None:
        return self.dictionaries.get(dictionary_id)
    
    def get_all(self, active_only: bool = False) -> List[Dict[str, Any]]:
        dicts = list(self.dictionaries.values())
        if active_only:
            return [d for d in dicts if d.get("active", True)]
        return dicts
    
    def update(self, dictionary_id: str, updates: Dict[str, Any]) -> Dict[str, Any] | None:
        if dictionary_id in self.dictionaries:
            self.dictionaries[dictionary_id].update(updates)
            return self.dictionaries[dictionary_id]
        return None
    
    def delete(self, dictionary_id: str) -> bool:
        if dictionary_id in self.dictionaries:
            del self.dictionaries[dictionary_id]
            return True
        return False
    
    def count(self) -> int:
        return len(self.dictionaries)


@pytest.fixture
def mock_user_repo():
    """Provide a mock user repository."""
    return MockUserRepository()


@pytest.fixture
def mock_session_repo():
    """Provide a mock session repository."""
    return MockSessionRepository()


@pytest.fixture
def mock_game_repo():
    """Provide a mock game repository."""
    return MockGameRepository()


@pytest.fixture
def mock_dict_repo():
    """Provide a mock dictionary repository."""
    return MockDictionaryRepository()


@pytest.fixture
def auth_service(mock_user_repo):
    """Provide an AuthService with mock repository."""
    return AuthService(mock_user_repo)


@pytest.fixture
def session_service(mock_session_repo, mock_user_repo):
    """Provide a SessionService with mock repositories."""
    return SessionService(mock_session_repo, mock_user_repo)


@pytest.fixture
def game_service(mock_game_repo, mock_session_repo, mock_dict_repo):
    """Provide a GameService with mock repositories."""
    return GameService(mock_game_repo, mock_session_repo, mock_dict_repo)


@pytest.fixture
def stats_service(mock_user_repo, mock_session_repo, mock_game_repo):
    """Provide a StatsService with mock repositories."""
    return StatsService(mock_user_repo, mock_session_repo, mock_game_repo)


@pytest.fixture
def dict_service(mock_dict_repo):
    """Provide a DictionaryService with mock repository."""
    return DictionaryService(mock_dict_repo)


@pytest.fixture
def test_user_data():
    """Provide test user data."""
    return {
        "email": "test@example.com",
        "password": "Test123!",
        "nickname": "TestUser"
    }


@pytest.fixture
def test_admin_data():
    """Provide test admin user data."""
    return {
        "email": "admin@example.com",
        "password": "Admin123!",
        "nickname": "AdminUser"
    }


@pytest.fixture
def sample_session_params():
    """Provide sample session parameters."""
    return {
        "max_misses": 6,
        "max_time_sec": 300,
        "dictionary_id": "dict_ro_basic",
        "seed": 12345
    }


@pytest.fixture
def client():
    """Provide a FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def auth_token(client, test_user_data):
    """Provide an authentication token for a regular user."""
    # Register user
    response = client.post("/api/auth/register", json=test_user_data)
    assert response.status_code == 201
    
    # Login
    response = client.post("/api/auth/login", json={
        "email": test_user_data["email"],
        "password": test_user_data["password"]
    })
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def admin_token(client, test_admin_data):
    """Provide an authentication token for an admin user."""
    # First user is always admin
    response = client.post("/api/auth/register", json=test_admin_data)
    assert response.status_code == 201
    
    # Login
    response = client.post("/api/auth/login", json={
        "email": test_admin_data["email"],
        "password": test_admin_data["password"]
    })
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def test_user(client, request):
    """Provide a registered test user (via API) with unique email per test."""
    # Use test name to generate unique email
    test_name = request.node.name
    email = f"testuser_{test_name}@example.com"
    
    # Register a test user via the API
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "TestPassword123",
            "nickname": "TestUser"
        }
    )
    assert register_response.status_code == 201
    user_data = register_response.json()
    user_data["email"] = email  # Ensure email is in returned data
    user_data["password"] = "TestPassword123"  # Add password for tests
    return user_data


@pytest.fixture
def created_user(auth_service, test_user_data):
    """Provide a created user for testing."""
    return auth_service.register_user(
        email=test_user_data["email"],
        password=test_user_data["password"],
        nickname=test_user_data.get("nickname")
    )


@pytest.fixture
def created_session(session_service, created_user, sample_session_params):
    """Provide a created session for testing."""
    return session_service.create_session(
        user_id=created_user["user_id"],
        num_games=5,
        dictionary_id=sample_session_params.get("dictionary_id", "dict_ro_basic"),
        difficulty=sample_session_params.get("difficulty", "medium"),
        language=sample_session_params.get("language", "ro"),
        max_misses=sample_session_params.get("max_misses", 6),
        allow_word_guess=sample_session_params.get("allow_word_guess", True),
        seed=sample_session_params.get("seed")
    )


@pytest.fixture
def created_game(game_service, created_session, created_user, mock_game_repo):
    """Provide a created game for testing."""
    result = game_service.create_game(
        session_id=created_session["session_id"],
        user_id=created_user["user_id"]
    )
    # Fetch full game including secret from repo and return a copy
    # to avoid mutation issues when tests update the game
    full_game = mock_game_repo.get_by_id(result["game_id"])
    return dict(full_game)
