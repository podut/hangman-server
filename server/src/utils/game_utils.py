"""Game logic utilities: pattern matching, scoring."""


def normalize(s: str) -> str:
    """Normalize Romanian diacritics for case-insensitive comparison.
    
    Converts: ă→a, â→a, î→i, ș→s, ț→t
    """
    return s.lower().replace('ă', 'a').replace('â', 'a').replace('î', 'i').replace('ș', 's').replace('ț', 't')


def update_pattern(secret: str, pattern: str, letter: str) -> str:
    """Update the pattern by revealing positions where the letter appears in the secret word.
    
    Args:
        secret: The secret word
        pattern: Current pattern (e.g., "***d***")
        letter: Letter to reveal
        
    Returns:
        Updated pattern with revealed letter positions
    """
    letter_norm = normalize(letter)
    result = list(pattern)
    for i, c in enumerate(secret):
        if normalize(c) == letter_norm:
            result[i] = secret[i]
    return ''.join(result)


def calculate_score(
    won: bool,
    total_guesses: int,
    wrong_letters: int,
    wrong_word_guesses: int,
    time_sec: float,
    length: int
) -> float:
    """Calculate composite game score.
    
    Formula: 1000*won - 10*guesses - 5*wrong - 40*wrong_words - 0.2*time + 2*length
    
    Args:
        won: True if game was won
        total_guesses: Total number of guesses made
        wrong_letters: Number of wrong letter guesses
        wrong_word_guesses: Number of wrong word guesses
        time_sec: Time taken in seconds
        length: Length of the word
        
    Returns:
        Calculated score (can be negative)
    """
    return (
        1000 * int(won)
        - 10 * total_guesses
        - 5 * wrong_letters
        - 40 * wrong_word_guesses
        - 0.2 * time_sec
        + 2 * length
    )
