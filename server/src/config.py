"""Application configuration with Pydantic settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import secrets


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Server Configuration
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    debug: bool = False
    
    # Security
    secret_key: str = secrets.token_urlsafe(32)  # Generate random key if not provided
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    
    # CORS Configuration
    cors_origins: str = "*"  # Comma-separated list
    cors_allow_credentials: bool = True
    
    # Application Settings
    max_sessions_per_user: int = 10
    max_games_per_session: int = 20
    default_max_wrong_guesses: int = 6
    
    # Admin Configuration
    admin_username: str = "admin"
    admin_password: str = "changeme123"  # Should be changed in production
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    # Testing
    disable_rate_limiting: bool = False
    
    # Brute-force Protection
    max_login_attempts: int = 5
    login_lockout_duration_minutes: int = 15
    login_attempt_window_minutes: int = 15
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # Ignore extra environment variables
    )
    
    def get_cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
    
    def validate_config(self) -> None:
        """Validate critical configuration at startup."""
        errors = []
        warnings = []
        
        # Check SECRET_KEY
        if len(self.secret_key) < 32:
            errors.append("SECRET_KEY must be at least 32 characters long")
        
        # Production-specific checks
        if not self.debug:
            # SECRET_KEY should not be auto-generated in production
            # Note: We can't reliably check for auto-generated keys, so just warn
            if self.secret_key == secrets.token_urlsafe(32):
                errors.append("SECRET_KEY must be explicitly set in production (not auto-generated)")
            
            # Check admin password in production
            if self.admin_password == "changeme123":
                errors.append("ADMIN_PASSWORD must be changed from default in production")
        else:
            # Debug mode warnings
            if self.admin_password == "changeme123":
                warnings.append("ADMIN_PASSWORD is using default value - OK for development only")
        
        # Validate numeric ranges
        if self.access_token_expire_minutes < 1:
            errors.append("ACCESS_TOKEN_EXPIRE_MINUTES must be at least 1")
        
        if self.max_sessions_per_user < 1:
            errors.append("MAX_SESSIONS_PER_USER must be at least 1")
        
        if self.max_games_per_session < 1:
            errors.append("MAX_GAMES_PER_SESSION must be at least 1")
        
        if self.default_max_wrong_guesses < 1:
            errors.append("DEFAULT_MAX_WRONG_GUESSES must be at least 1")
        
        if errors:
            raise ValueError(f"Configuration validation failed:\n- " + "\n- ".join(errors))


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings (for dependency injection)."""
    return settings
