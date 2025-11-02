"""
Unit tests for Hangman game logic.
"""
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from main import normalize, update_pattern, calculate_score


def test_normalize():
    """Test Romanian diacritics normalization."""
    assert normalize("ă") == "a", f"Expected 'a', got '{normalize('ă')}'"
    assert normalize("â") == "a", f"Expected 'a', got '{normalize('â')}'"
    assert normalize("î") == "i", f"Expected 'i', got '{normalize('î')}'"
    assert normalize("ș") == "s", f"Expected 's', got '{normalize('ș')}'"
    assert normalize("ț") == "t", f"Expected 't', got '{normalize('ț')}'"
    # ĂÂÎȘȚ = A + Â + Î + Ș + Ț => a + a + i + s + t = aaist (NOT aaiist - there's no double i)
    assert normalize("ĂÂÎȘȚ") == "aaist", f"Expected 'aaist', got '{normalize('ĂÂÎȘȚ')}'"
    assert normalize("student") == "student", f"Expected 'student', got '{normalize('student')}'"
    assert normalize("STUDENT") == "student", f"Expected 'student', got '{normalize('STUDENT')}'"
    assert normalize("Programare") == "programare", f"Expected 'programare', got '{normalize('Programare')}'"
    print("✓ test_normalize passed")


def test_update_pattern_single_letter():
    """Test pattern update with single occurrence."""
    secret = "python"
    pattern = "******"
    result = update_pattern(secret, pattern, "p")
    assert result == "p*****", f"Expected 'p*****', got '{result}'"
    
    result = update_pattern(secret, pattern, "y")
    assert result == "*y****", f"Expected '*y****', got '{result}'"
    print("✓ test_update_pattern_single_letter passed")


def test_update_pattern_multiple_occurrences():
    """Test pattern update with multiple occurrences of same letter."""
    secret = "programming"
    pattern = "***********"
    result = update_pattern(secret, pattern, "g")
    # Should reveal both 'g' positions (index 3 and 10)
    assert result == "***g******g", f"Expected '***g******g', got '{result}'"
    
    result = update_pattern(secret, pattern, "m")
    # Should reveal both 'm' positions (index 6 and 7)
    assert result == "******mm***", f"Expected '******mm***', got '{result}'"
    print("✓ test_update_pattern_multiple_occurrences passed")


def test_update_pattern_diacritics():
    """Test pattern update with Romanian diacritics."""
    # Use a word with both 's' and 'ș'
    secret = "școală"  # ș at position 0, no regular 's'
    pattern = "******"
    
    # Searching for 's' should match 'ș' (both normalize to 's')
    result = update_pattern(secret, pattern, "s")
    assert result == "ș*****", f"Expected 'ș*****', got '{result}'"
    
    # Searching for 'ș' should also work with the same secret and pattern
    result = update_pattern(secret, pattern, "ș")
    assert result == "ș*****", f"Expected 'ș*****', got '{result}'"
    
    # Test with 'ț'
    secret2 = "țară"
    pattern2 = "****"
    result = update_pattern(secret2, pattern2, "t")
    assert result == "ț***", f"Expected 'ț***', got '{result}'"
    print("✓ test_update_pattern_diacritics passed")


def test_update_pattern_case_insensitive():
    """Test pattern update is case-insensitive."""
    secret = "Python"
    pattern = "******"
    
    result = update_pattern(secret, pattern, "p")
    assert result == "P*****", f"Expected 'P*****', got '{result}'"
    
    result = update_pattern(secret, pattern, "P")
    assert result == "P*****", f"Expected 'P*****', got '{result}'"
    print("✓ test_update_pattern_case_insensitive passed")


def test_calculate_score_win():
    """Test score calculation for winning game."""
    score = calculate_score(
        won=True,
        total_guesses=5,
        wrong_letters=1,
        wrong_word_guesses=0,
        time_sec=10.0,
        length=7
    )
    # 1000*1 - 10*5 - 5*1 - 40*0 - 0.2*10 + 2*7 = 1000 - 50 - 5 - 0 - 2 + 14 = 957
    expected = 957.0
    assert score == expected, f"Expected {expected}, got {score}"
    print("✓ test_calculate_score_win passed")


def test_calculate_score_loss():
    """Test score calculation for losing game."""
    score = calculate_score(
        won=False,
        total_guesses=10,
        wrong_letters=6,
        wrong_word_guesses=1,
        time_sec=30.0,
        length=8
    )
    # 1000*0 - 10*10 - 5*6 - 40*1 - 0.2*30 + 2*8 = 0 - 100 - 30 - 40 - 6 + 16 = -160
    expected = -160.0
    assert score == expected, f"Expected {expected}, got {score}"
    print("✓ test_calculate_score_loss passed")


def test_calculate_score_perfect_game():
    """Test score calculation for perfect game (no mistakes)."""
    score = calculate_score(
        won=True,
        total_guesses=7,
        wrong_letters=0,
        wrong_word_guesses=0,
        time_sec=5.0,
        length=7
    )
    # 1000*1 - 10*7 - 5*0 - 40*0 - 0.2*5 + 2*7 = 1000 - 70 - 0 - 0 - 1 + 14 = 943
    expected = 943.0
    assert score == expected, f"Expected {expected}, got {score}"
    print("✓ test_calculate_score_perfect_game passed")


def test_calculate_score_word_guess_penalty():
    """Test score calculation with wrong word guess penalty."""
    score = calculate_score(
        won=False,
        total_guesses=3,
        wrong_letters=0,
        wrong_word_guesses=2,
        time_sec=15.0,
        length=10
    )
    # 1000*0 - 10*3 - 5*0 - 40*2 - 0.2*15 + 2*10 = 0 - 30 - 0 - 80 - 3 + 20 = -93
    expected = -93.0
    assert score == expected, f"Expected {expected}, got {score}"
    print("✓ test_calculate_score_word_guess_penalty passed")


def run_all_tests():
    """Run all test functions."""
    print("\n=== Running Hangman Game Logic Tests ===\n")
    
    tests = [
        test_normalize,
        test_update_pattern_single_letter,
        test_update_pattern_multiple_occurrences,
        test_update_pattern_diacritics,
        test_update_pattern_case_insensitive,
        test_calculate_score_win,
        test_calculate_score_loss,
        test_calculate_score_perfect_game,
        test_calculate_score_word_guess_penalty
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__} FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} ERROR: {e}")
            failed += 1
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {passed}/{len(tests)}")
    print(f"Failed: {failed}/{len(tests)}")
    
    if failed == 0:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n❌ {failed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit(run_all_tests())
