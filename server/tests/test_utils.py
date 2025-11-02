"""
Unit tests for utility functions.
Tests game_utils (normalize, update_pattern, calculate_score) and auth_utils.
"""

import pytest
from server.src.utils.game_utils import normalize, update_pattern, calculate_score
from server.src.utils.auth_utils import hash_password, verify_password, create_access_token, decode_token


@pytest.mark.unit
class TestNormalize:
    """Test Romanian diacritics normalization."""
    
    def test_normalize_lowercase_diacritics(self):
        """Test normalization of lowercase Romanian diacritics."""
        assert normalize("ă") == "a"
        assert normalize("â") == "a"
        assert normalize("î") == "i"
        assert normalize("ș") == "s"
        assert normalize("ț") == "t"
        
    def test_normalize_uppercase_diacritics(self):
        """Test normalization of uppercase Romanian diacritics."""
        assert normalize("Ă") == "a"
        assert normalize("Â") == "a"
        assert normalize("Î") == "i"
        assert normalize("Ș") == "s"
        assert normalize("Ț") == "t"
        
    def test_normalize_mixed_string(self):
        """Test normalization of strings with mixed characters."""
        assert normalize("școală") == "scoala"
        assert normalize("ĂÂÎȘȚ") == "aaist"
        assert normalize("Programare") == "programare"
        
    def test_normalize_no_diacritics(self):
        """Test that strings without diacritics remain unchanged."""
        assert normalize("python") == "python"
        assert normalize("STUDENT") == "student"


@pytest.mark.unit
class TestUpdatePattern:
    """Test pattern update functionality."""
    
    def test_update_pattern_single_occurrence(self):
        """Test updating pattern with single letter occurrence."""
        result = update_pattern("python", "******", "p")
        assert result == "p*****"
        
        result = update_pattern("python", "******", "y")
        assert result == "*y****"
        
    def test_update_pattern_multiple_occurrences(self):
        """Test updating pattern with multiple occurrences."""
        result = update_pattern("programming", "***********", "g")
        assert result == "***g******g"
        
        result = update_pattern("programming", "***********", "m")
        assert result == "******mm***"
        
    def test_update_pattern_no_match(self):
        """Test pattern update when letter is not in word."""
        result = update_pattern("python", "******", "z")
        assert result == "******"  # Pattern should remain unchanged
        
    def test_update_pattern_case_insensitive(self):
        """Test that pattern update is case-insensitive."""
        result = update_pattern("Python", "******", "p")
        assert result == "P*****"
        
        result = update_pattern("Python", "******", "P")
        assert result == "P*****"
        
    def test_update_pattern_with_diacritics(self):
        """Test pattern update with Romanian diacritics."""
        result = update_pattern("școală", "******", "s")
        assert result == "ș*****"
        
        result = update_pattern("școală", "******", "ș")
        assert result == "ș*****"
        
    def test_update_pattern_partial_revealed(self):
        """Test updating already partially revealed pattern."""
        result = update_pattern("python", "p***on", "t")
        assert result == "p*t*on"  # Pattern reveals t in position 2


@pytest.mark.unit
class TestCalculateScore:
    """Test score calculation functionality."""
    
    def test_calculate_score_perfect_win(self):
        """Test score for perfect game (won with no mistakes)."""
        score = calculate_score(
            won=True,
            total_guesses=5,
            wrong_letters=0,
            wrong_word_guesses=0,
            time_sec=10.0,
            length=7
        )
        # 1000 - 10*5 - 5*0 - 40*0 - 0.2*10 + 2*7 = 1000 - 50 - 2 + 14 = 962
        assert score == 962.0
        
    def test_calculate_score_win_with_mistakes(self):
        """Test score for win with some mistakes."""
        score = calculate_score(
            won=True,
            total_guesses=10,
            wrong_letters=3,
            wrong_word_guesses=1,
            time_sec=30.0,
            length=8
        )
        # 1000 - 10*10 - 5*3 - 40*1 - 0.2*30 + 2*8 = 1000 - 100 - 15 - 40 - 6 + 16 = 855
        assert score == 855.0
        
    def test_calculate_score_loss(self):
        """Test score for losing game."""
        score = calculate_score(
            won=False,
            total_guesses=10,
            wrong_letters=6,
            wrong_word_guesses=1,
            time_sec=30.0,
            length=8
        )
        # 0 - 10*10 - 5*6 - 40*1 - 0.2*30 + 2*8 = -100 - 30 - 40 - 6 + 16 = -160
        assert score == -160.0
        
    def test_calculate_score_long_word_bonus(self):
        """Test that longer words give higher bonus."""
        score_short = calculate_score(
            won=True, total_guesses=5, wrong_letters=0,
            wrong_word_guesses=0, time_sec=10.0, length=5
        )
        score_long = calculate_score(
            won=True, total_guesses=5, wrong_letters=0,
            wrong_word_guesses=0, time_sec=10.0, length=15
        )
        # Longer word should give higher score due to length bonus
        assert score_long > score_short
        
    def test_calculate_score_time_penalty(self):
        """Test that more time results in lower score."""
        score_fast = calculate_score(
            won=True, total_guesses=5, wrong_letters=0,
            wrong_word_guesses=0, time_sec=5.0, length=7
        )
        score_slow = calculate_score(
            won=True, total_guesses=5, wrong_letters=0,
            wrong_word_guesses=0, time_sec=50.0, length=7
        )
        # Faster completion should give higher score
        assert score_fast > score_slow


@pytest.mark.unit
class TestAuthUtils:
    """Test authentication utility functions."""
    
    def test_hash_password(self):
        """Test password hashing."""
        password = "MySecure123!"
        hashed = hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 0
        assert hashed.startswith("$2b$")  # bcrypt hash prefix
        
    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "MySecure123!"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
        
    def test_verify_password_incorrect(self):
        """Test password verification with wrong password."""
        password = "MySecure123!"
        hashed = hash_password(password)
        
        assert verify_password("WrongPass", hashed) is False
        
    def test_hash_password_different_hashes(self):
        """Test that same password produces different hashes (salt)."""
        password = "MySecure123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        assert hash1 != hash2
        # But both should verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True
        
    def test_create_access_token(self):
        """Test JWT token creation."""
        payload = {"sub": "u_123", "role": "user"}
        token = create_access_token(payload)
        
        assert isinstance(token, str)
        assert len(token) > 0
        assert token.count(".") == 2  # JWT format: header.payload.signature
        
    def test_decode_token(self):
        """Test JWT token decoding."""
        payload = {"sub": "u_123", "role": "user"}
        token = create_access_token(payload)
        
        decoded = decode_token(token)
        
        assert decoded["sub"] == "u_123"
        assert decoded["role"] == "user"
        
    def test_decode_invalid_token(self):
        """Test decoding invalid JWT token."""
        with pytest.raises(Exception):  # Should raise JWTError or similar
            decode_token("invalid.token.here")
