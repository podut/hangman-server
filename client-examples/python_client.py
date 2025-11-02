#!/usr/bin/env python3
import requests
import json
from typing import Optional

BASE_URL = "http://localhost:8000/api/v1"

class HangmanClient:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.token: Optional[str] = None
    
    def register(self, email: str, password: str, nickname: str = None):
        resp = requests.post(f"{self.base_url}/auth/register", json={
            "email": email,
            "password": password,
            "nickname": nickname
        })
        resp.raise_for_status()
        return resp.json()
    
    def login(self, email: str, password: str):
        resp = requests.post(f"{self.base_url}/auth/login", json={
            "email": email,
            "password": password
        })
        resp.raise_for_status()
        data = resp.json()
        self.token = data["access_token"]
        return data
    
    def _headers(self):
        return {"Authorization": f"Bearer {self.token}"}
    
    def create_session(self, num_games: int = 1, **kwargs):
        resp = requests.post(f"{self.base_url}/sessions", 
            headers=self._headers(),
            json={"num_games": num_games, **kwargs})
        resp.raise_for_status()
        return resp.json()
    
    def create_game(self, session_id: str):
        resp = requests.post(f"{self.base_url}/sessions/{session_id}/games",
            headers=self._headers())
        resp.raise_for_status()
        return resp.json()
    
    def get_game_state(self, session_id: str, game_id: str):
        resp = requests.get(f"{self.base_url}/sessions/{session_id}/games/{game_id}/state",
            headers=self._headers())
        resp.raise_for_status()
        return resp.json()
    
    def guess_letter(self, session_id: str, game_id: str, letter: str):
        resp = requests.post(f"{self.base_url}/sessions/{session_id}/games/{game_id}/guess",
            headers=self._headers(),
            json={"letter": letter})
        resp.raise_for_status()
        return resp.json()
    
    def guess_word(self, session_id: str, game_id: str, word: str):
        resp = requests.post(f"{self.base_url}/sessions/{session_id}/games/{game_id}/guess",
            headers=self._headers(),
            json={"word": word})
        resp.raise_for_status()
        return resp.json()
    
    def get_session_stats(self, session_id: str):
        resp = requests.get(f"{self.base_url}/sessions/{session_id}/stats",
            headers=self._headers())
        resp.raise_for_status()
        return resp.json()
    
    def get_leaderboard(self, metric: str = "win_rate", period: str = "all", limit: int = 10):
        resp = requests.get(f"{self.base_url}/leaderboard",
            params={"metric": metric, "period": period, "limit": limit})
        resp.raise_for_status()
        return resp.json()
    
    def get_session(self, session_id: str):
        resp = requests.get(f"{self.base_url}/sessions/{session_id}",
            headers=self._headers())
        resp.raise_for_status()
        return resp.json()
    
    def list_session_games(self, session_id: str, page: int = 1, page_size: int = 50):
        resp = requests.get(f"{self.base_url}/sessions/{session_id}/games",
            headers=self._headers(),
            params={"page": page, "page_size": page_size})
        resp.raise_for_status()
        return resp.json()
    
    def abort_session(self, session_id: str):
        resp = requests.post(f"{self.base_url}/sessions/{session_id}/abort",
            headers=self._headers())
        resp.raise_for_status()
        return resp.json()
    
    def abort_game(self, session_id: str, game_id: str):
        resp = requests.post(f"{self.base_url}/sessions/{session_id}/games/{game_id}/abort",
            headers=self._headers())
        resp.raise_for_status()
        return resp.json()
    
    def get_user_stats(self, user_id: str, period: str = "all"):
        resp = requests.get(f"{self.base_url}/users/{user_id}/stats",
            headers=self._headers(),
            params={"period": period})
        resp.raise_for_status()
        return resp.json()
    
    def get_global_stats(self, period: str = "all"):
        resp = requests.get(f"{self.base_url}/stats/global",
            params={"period": period})
        resp.raise_for_status()
        return resp.json()
    
    # Admin functions
    def list_dictionaries(self):
        resp = requests.get(f"{self.base_url}/admin/dictionaries",
            headers=self._headers())
        resp.raise_for_status()
        return resp.json()
    
    def create_dictionary(self, dictionary_id: str, name: str, language: str, 
                         difficulty: str, words_text: str):
        resp = requests.post(f"{self.base_url}/admin/dictionaries",
            headers=self._headers(),
            json={
                "dictionary_id": dictionary_id,
                "name": name,
                "language": language,
                "difficulty": difficulty,
                "words_text": words_text
            })
        resp.raise_for_status()
        return resp.json()
    
    def update_dictionary(self, dictionary_id: str, name: str = None, active: bool = None):
        data = {}
        if name is not None:
            data["name"] = name
        if active is not None:
            data["active"] = active
        resp = requests.patch(f"{self.base_url}/admin/dictionaries/{dictionary_id}",
            headers=self._headers(),
            json=data)
        resp.raise_for_status()
        return resp.json()
    
    def get_dictionary_words(self, dictionary_id: str, sample: int = 0):
        resp = requests.get(f"{self.base_url}/admin/dictionaries/{dictionary_id}/words",
            headers=self._headers(),
            params={"sample": sample} if sample > 0 else {})
        resp.raise_for_status()
        return resp.json()

def demo():
    import random
    client = HangmanClient()
    
    # Register and login with unique email
    email = f"player{random.randint(1000, 9999)}@test.com"
    password = "Password123"
    
    print("=== Registering user ===")
    try:
        reg_result = client.register(email, password, "TestPlayer")
        print(f"Registered: {reg_result.get('user_id')}, Is Admin: {reg_result.get('is_admin')}")
    except:
        print("User already exists")
    
    print("\n=== Logging in ===")
    login_data = client.login(email, password)
    print(f"Logged in successfully")
    
    # Create session with 1 game
    print("\n=== Creating session ===")
    session = client.create_session(num_games=1)
    session_id = session["session_id"]
    print(f"Session ID: {session_id}")
    
    # Create game
    print("\n=== Creating game ===")
    game = client.create_game(session_id)
    game_id = game["game_id"]
    print(f"Game ID: {game_id}")
    print(f"Pattern: {game['pattern']}")
    print(f"Length: {game['length']}")
    
    # Play game
    print("\n=== Playing game ===")
    while True:
        state = client.get_game_state(session_id, game_id)
        print(f"\nPattern: {state['pattern']}")
        print(f"Wrong letters: {state['wrong_letters']}")
        print(f"Remaining misses: {state['remaining_misses']}")
        print(f"Total guesses: {state['total_guesses']}")
        
        if state['status'] != 'IN_PROGRESS':
            print(f"\n=== Game finished: {state['status']} ===")
            if state.get('result'):
                print(f"Secret word: {state['result']['secret']}")
                if state.get('composite_score'):
                    print(f"Score: {state['composite_score']:.2f}")
                if state.get('time_seconds'):
                    print(f"Time: {state['time_seconds']:.2f}s")
            break
        
        letter = input("Guess a letter (or 'quit' to abort): ").strip().lower()
        if letter == 'quit':
            print("Aborting game...")
            client.abort_game(session_id, game_id)
            break
        
        if len(letter) > 1:
            # Try word guess
            try:
                result = client.guess_word(session_id, game_id, letter)
                print(f"✓ Word guess: {result['status']}")
            except requests.HTTPError as e:
                print(f"✗ Error: {e.response.json()}")
        else:
            try:
                result = client.guess_letter(session_id, game_id, letter)
                print(f"✓ New pattern: {result['pattern']}")
            except requests.HTTPError as e:
                print(f"✗ Error: {e.response.json()}")
    
    # Get stats
    print("\n=== Session stats ===")
    stats = client.get_session_stats(session_id)
    print(json.dumps(stats, indent=2))
    
    # Get user stats
    print("\n=== User stats (all time) ===")
    try:
        # Get user_id from login data or session
        session_detail = client.get_session(session_id)
        user_id = session_detail["user_id"]
        user_stats = client.get_user_stats(user_id)
        print(json.dumps(user_stats, indent=2))
    except Exception as e:
        print(f"Could not get user stats: {e}")
    
    # Get global stats
    print("\n=== Global stats ===")
    try:
        global_stats = client.get_global_stats()
        print(json.dumps(global_stats, indent=2))
    except Exception as e:
        print(f"Could not get global stats: {e}")
    
    # Get leaderboard
    print("\n=== Leaderboard (by composite score) ===")
    try:
        leaderboard = client.get_leaderboard(metric="composite_score", limit=5)
        for i, entry in enumerate(leaderboard.get("leaderboard", []), 1):
            print(f"{i}. {entry['nickname']}: {entry.get('avg_composite_score', 0):.2f} points "
                  f"(Win rate: {entry['win_rate']*100:.1f}%)")
    except Exception as e:
        print(f"Could not get leaderboard: {e}")

if __name__ == "__main__":
    demo()
