"""
Unit tests for AuthService.
Tests user registration, login, token management, and error handling.
"""

import pytest
from server.src.exceptions import (
    UserAlreadyExistsException,
    InvalidCredentialsException,
    UserNotFoundException
)


@pytest.mark.unit
class TestAuthServiceRegister:
    """Test user registration functionality."""
    
    def test_register_user_success(self, auth_service, test_user_data):
        """Test successful user registration."""
        result = auth_service.register_user(
            email=test_user_data["email"],
            password=test_user_data["password"],
            nickname=test_user_data["nickname"]
        )
        
        assert result["email"] == test_user_data["email"]
        assert result["nickname"] == test_user_data["nickname"]
        assert "user_id" in result
        assert result["user_id"].startswith("u_")
        assert "password" not in result
        assert "created_at" in result
        
    def test_register_first_user_is_admin(self, auth_service, test_user_data):
        """Test that first registered user becomes admin."""
        result = auth_service.register_user(
            email=test_user_data["email"],
            password=test_user_data["password"]
        )
        
        assert result["is_admin"] is True
        
    def test_register_second_user_not_admin(self, auth_service, test_user_data):
        """Test that second user is not admin."""
        # Register first user (admin)
        auth_service.register_user(
            email="first@example.com",
            password="FirstPass123!"
        )
        
        # Register second user
        result = auth_service.register_user(
            email=test_user_data["email"],
            password=test_user_data["password"]
        )
        
        assert result["is_admin"] is False
        
    def test_register_without_nickname_uses_email_prefix(self, auth_service):
        """Test registration without nickname uses email prefix."""
        result = auth_service.register_user(
            email="johndoe@example.com",
            password="Pass123!"
        )
        
        assert result["nickname"] == "johndoe"
        
    def test_register_duplicate_email_raises_exception(self, auth_service, test_user_data):
        """Test that registering duplicate email raises exception."""
        # Register first time
        auth_service.register_user(
            email=test_user_data["email"],
            password=test_user_data["password"]
        )
        
        # Try to register again with same email
        with pytest.raises(UserAlreadyExistsException) as exc_info:
            auth_service.register_user(
                email=test_user_data["email"],
                password="DifferentPass123!"
            )
        
        assert test_user_data["email"] in str(exc_info.value)


@pytest.mark.unit
class TestAuthServiceLogin:
    """Test user login functionality."""
    
    def test_login_success(self, auth_service, test_user_data):
        """Test successful login."""
        # Register user
        auth_service.register_user(
            email=test_user_data["email"],
            password=test_user_data["password"]
        )
        
        # Login
        result = auth_service.login_user(
            email=test_user_data["email"],
            password=test_user_data["password"]
        )
        
        assert "access_token" in result
        assert "refresh_token" in result
        assert result["expires_in"] == 3600
        assert "user_id" in result
        assert result["user_id"].startswith("u_")
        
    def test_login_invalid_email(self, auth_service):
        """Test login with non-existent email."""
        with pytest.raises(InvalidCredentialsException):
            auth_service.login_user(
                email="nonexistent@example.com",
                password="Pass123!"
            )
            
    def test_login_invalid_password(self, auth_service, test_user_data):
        """Test login with wrong password."""
        # Register user
        auth_service.register_user(
            email=test_user_data["email"],
            password=test_user_data["password"]
        )
        
        # Try login with wrong password
        with pytest.raises(InvalidCredentialsException):
            auth_service.login_user(
                email=test_user_data["email"],
                password="WrongPassword123!"
            )


@pytest.mark.unit
class TestAuthServiceTokenManagement:
    """Test token refresh and user retrieval."""
    
    def test_refresh_token(self, auth_service, created_user):
        """Test token refresh."""
        result = auth_service.refresh_token(created_user["user_id"])
        
        assert "access_token" in result
        assert result["expires_in"] == 3600
        
    def test_get_user_by_id_success(self, auth_service, created_user):
        """Test getting user by ID."""
        result = auth_service.get_user_by_id(created_user["user_id"])
        
        assert result["user_id"] == created_user["user_id"]
        assert result["email"] == created_user["email"]
        
    def test_get_user_by_id_not_found(self, auth_service):
        """Test getting non-existent user."""
        with pytest.raises(UserNotFoundException):
            auth_service.get_user_by_id("u_nonexistent")
