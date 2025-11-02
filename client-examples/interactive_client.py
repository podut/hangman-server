#!/usr/bin/env python3
"""Interactive Hangman Client - Meniu complet pentru testare manuală."""
import requests
import json
from typing import Optional

BASE_URL = "http://localhost:8000/api/v1"

class HangmanClient:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.current_session_id: Optional[str] = None
        self.current_game_id: Optional[str] = None
    
    def _headers(self):
        if not self.token:
            raise Exception("Not logged in! Use option 2 to login first.")
        return {"Authorization": f"Bearer {self.token}"}
    
    # AUTH
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
        self.user_id = data["user_id"]
        return data
    
    def delete_account(self):
        resp = requests.delete(f"{self.base_url}/auth/account", headers=self._headers())
        resp.raise_for_status()
        return resp.json()
    
    # SESSIONS
    def create_session(self, num_games: int = 1, difficulty: str = "medium", 
                      max_misses: int = 6, dictionary_id: str = None, seed: int = None):
        data = {"num_games": num_games, "difficulty": difficulty, "max_misses": max_misses}
        if dictionary_id:
            data["dictionary_id"] = dictionary_id
        if seed is not None:
            data["seed"] = seed
        resp = requests.post(f"{self.base_url}/sessions", 
            headers=self._headers(), json=data)
        resp.raise_for_status()
        return resp.json()
    
    def get_session(self, session_id: str):
        resp = requests.get(f"{self.base_url}/sessions/{session_id}",
            headers=self._headers())
        resp.raise_for_status()
        return resp.json()
    
    def list_user_sessions(self):
        resp = requests.get(f"{self.base_url}/sessions", headers=self._headers())
        resp.raise_for_status()
        return resp.json()
    
    def abort_session(self, session_id: str):
        resp = requests.post(f"{self.base_url}/sessions/{session_id}/abort",
            headers=self._headers())
        resp.raise_for_status()
        return resp.json()
    
    # GAMES
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
    
    def guess(self, session_id: str, game_id: str, guess: str):
        # Determine if it's a letter (single char) or word guess
        payload = {"letter": guess} if len(guess) == 1 else {"word": guess}
        resp = requests.post(f"{self.base_url}/sessions/{session_id}/games/{game_id}/guess",
            headers=self._headers(),
            json=payload)
        resp.raise_for_status()
        return resp.json()
    
    def abort_game(self, session_id: str, game_id: str):
        resp = requests.post(f"{self.base_url}/sessions/{session_id}/games/{game_id}/abort",
            headers=self._headers())
        resp.raise_for_status()
        return resp.json()
    
    def list_session_games(self, session_id: str):
        resp = requests.get(f"{self.base_url}/sessions/{session_id}/games",
            headers=self._headers())
        resp.raise_for_status()
        return resp.json()
    
    # STATS
    def get_session_stats(self, session_id: str):
        resp = requests.get(f"{self.base_url}/sessions/{session_id}/stats",
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
    
    def get_leaderboard(self, metric: str = "composite_score", period: str = "all", limit: int = 10):
        resp = requests.get(f"{self.base_url}/leaderboard",
            params={"metric": metric, "period": period, "limit": limit})
        resp.raise_for_status()
        return resp.json()

def print_menu():
    print("\n" + "="*60)
    print("🎮 HANGMAN CLIENT - MENIU PRINCIPAL")
    print("="*60)
    print("\n👤 AUTENTIFICARE:")
    print("  1. Înregistrare utilizator nou")
    print("  2. Login")
    print("  3. Șterge cont")
    print("\n🎯 SESIUNI:")
    print("  4. Creează sesiune nouă")
    print("  5. Vezi sesiunile mele")
    print("  6. Vezi detalii sesiune")
    print("  7. Abandonează sesiune")
    print("\n🎲 JOCURI:")
    print("  8. Creează joc nou")
    print("  9. Joacă joc curent")
    print(" 10. Vezi jocurile din sesiune")
    print(" 11. Abandonează joc")
    print("\n📊 STATISTICI:")
    print(" 12. Statistici sesiune")
    print(" 13. Statistici utilizator")
    print(" 14. Statistici globale")
    print(" 15. Leaderboard")
    print("\n 0. Ieșire")
    print("="*60)

def main():
    client = HangmanClient()
    
    print("\n🎮 Bun venit la Hangman Interactive Client!")
    print("Server: " + BASE_URL)
    
    while True:
        print_menu()
        
        # Status bar
        status = []
        if client.token:
            status.append(f"✓ Logat: {client.user_id}")
        if client.current_session_id:
            status.append(f"Sesiune: {client.current_session_id}")
        if client.current_game_id:
            status.append(f"Joc: {client.current_game_id}")
        if status:
            print(f"\n📌 Status: {' | '.join(status)}")
        
        choice = input("\n➤ Alege opțiunea: ").strip()
        
        try:
            if choice == "0":
                print("\n👋 La revedere!")
                break
            
            elif choice == "1":  # Register
                print("\n📝 ÎNREGISTRARE UTILIZATOR")
                email = input("Email: ").strip()
                password = input("Parolă: ").strip()
                nickname = input("Nickname (optional): ").strip() or None
                
                result = client.register(email, password, nickname)
                print(f"✅ Înregistrat cu succes!")
                print(f"   User ID: {result['user_id']}")
                print(f"   Admin: {'DA' if result.get('is_admin') else 'NU'}")
            
            elif choice == "2":  # Login
                print("\n🔐 LOGIN")
                email = input("Email: ").strip()
                password = input("Parolă: ").strip()
                
                result = client.login(email, password)
                print(f"✅ Login reușit!")
                print(f"   User ID: {client.user_id}")
            
            elif choice == "3":  # Delete account
                confirm = input("\n⚠️  Sigur vrei să ștergi contul? (da/nu): ").strip().lower()
                if confirm == "da":
                    result = client.delete_account()
                    print(f"✅ Cont șters: {result['message']}")
                    client.token = None
                    client.user_id = None
                else:
                    print("❌ Anulat")
            
            elif choice == "4":  # Create session
                print("\n🎯 CREEAZĂ SESIUNE NOUĂ")
                num_games = int(input("Număr jocuri (1-20) [1]: ").strip() or "1")
                difficulty = input("Dificultate (easy/medium/hard) [medium]: ").strip() or "medium"
                max_misses = int(input("Greșeli maxime [6]: ").strip() or "6")
                seed_input = input("Seed (pentru reproducere, opțional): ").strip()
                seed = int(seed_input) if seed_input else None
                
                result = client.create_session(num_games, difficulty, max_misses, seed=seed)
                client.current_session_id = result['session_id']
                print(f"✅ Sesiune creată: {client.current_session_id}")
                print(f"   Dificultate: {result['difficulty']}")
                print(f"   Jocuri permise: {result['num_games']}")
                if seed:
                    print(f"   Seed: {seed}")
            
            elif choice == "5":  # List sessions
                sessions = client.list_user_sessions()
                print(f"\n📋 SESIUNILE MELE ({len(sessions)} total)")
                for s in sessions:
                    status_emoji = "✅" if s['status'] == "COMPLETED" else "🎮" if s['status'] == "IN_PROGRESS" else "❌"
                    print(f"\n{status_emoji} {s['session_id']} - {s['status']}")
                    print(f"   Jocuri: {s['games_created']}/{s['num_games']}")
                    print(f"   Dificultate: {s['difficulty']}, Max greșeli: {s['max_misses']}")
            
            elif choice == "6":  # Get session details
                session_id = input("Session ID [curent]: ").strip() or client.current_session_id
                if not session_id:
                    print("❌ Nicio sesiune selectată!")
                    continue
                
                session = client.get_session(session_id)
                print(f"\n📊 DETALII SESIUNE: {session_id}")
                print(f"Status: {session['status']}")
                print(f"Dificultate: {session['difficulty']}")
                print(f"Jocuri: {session['games_created']}/{session['num_games']}")
                print(f"Creat: {session['created_at']}")
            
            elif choice == "7":  # Abort session
                session_id = input("Session ID [curent]: ").strip() or client.current_session_id
                if not session_id:
                    print("❌ Nicio sesiune selectată!")
                    continue
                
                result = client.abort_session(session_id)
                print(f"✅ Sesiune abandonată: {result['message']}")
                if session_id == client.current_session_id:
                    client.current_session_id = None
            
            elif choice == "8":  # Create game
                session_id = input("Session ID [curent]: ").strip() or client.current_session_id
                if not session_id:
                    print("❌ Nicio sesiune selectată!")
                    continue
                
                game = client.create_game(session_id)
                client.current_session_id = session_id
                client.current_game_id = game['game_id']
                print(f"\n✅ JOC CREAT: {game['game_id']}")
                print(f"Pattern: {game['pattern']}")
                print(f"Lungime: {game['length']} litere")
                print(f"Greșeli permise: {game['max_misses']}")
            
            elif choice == "9":  # Play game
                if not client.current_session_id or not client.current_game_id:
                    print("❌ Niciun joc activ! Folosește opțiunea 8 pentru a crea joc.")
                    continue
                
                print(f"\n🎲 JOACĂ JOCUL: {client.current_game_id}")
                print("Comenzi: literă/cuvânt pentru ghicit, 'quit' pentru abandon\n")
                
                while True:
                    state = client.get_game_state(client.current_session_id, client.current_game_id)
                    
                    print(f"\n{'='*50}")
                    print(f"Pattern: {state['pattern']}")
                    if state['wrong_letters']:
                        print(f"Greșeli: {', '.join(state['wrong_letters'])}")
                    print(f"Rămase: {state['remaining_misses']} greșeli | {state['total_guesses']} ghiciri")
                    print(f"{'='*50}")
                    
                    if state['status'] != 'IN_PROGRESS':
                        print(f"\n🏁 JOC TERMINAT: {state['status']}")
                        if state.get('result'):
                            print(f"Cuvânt: {state['result']['secret']}")
                            if state.get('composite_score'):
                                print(f"Scor: {state['composite_score']:.2f}")
                            if state.get('time_seconds'):
                                print(f"Timp: {state['time_seconds']:.2f}s")
                        client.current_game_id = None
                        break
                    
                    guess = input("\n➤ Ghicește: ").strip().lower()
                    
                    if guess == 'quit':
                        confirm = input("Sigur abandonezi? (da/nu): ").strip().lower()
                        if confirm == "da":
                            client.abort_game(client.current_session_id, client.current_game_id)
                            print("❌ Joc abandonat")
                            client.current_game_id = None
                            break
                        continue
                    
                    if not guess:
                        continue
                    
                    try:
                        result = client.guess(client.current_session_id, client.current_game_id, guess)
                        if len(guess) == 1:
                            print(f"✓ Pattern nou: {result['pattern']}")
                        else:
                            print(f"✓ Încercare cuvânt: {result['status']}")
                    except requests.HTTPError as e:
                        error = e.response.json()
                        print(f"✗ Eroare: {error.get('detail', 'Unknown error')}")
            
            elif choice == "10":  # List games
                session_id = input("Session ID [curent]: ").strip() or client.current_session_id
                if not session_id:
                    print("❌ Nicio sesiune selectată!")
                    continue
                
                result = client.list_session_games(session_id)
                games = result.get('games', [])
                print(f"\n🎲 JOCURI ÎN SESIUNEA {session_id} ({len(games)} total)")
                
                for g in games:
                    status_emoji = "✅" if g['status'] == "WON" else "❌" if g['status'] == "LOST" else "⏸️"
                    print(f"\n{status_emoji} {g['game_id']} - {g['status']}")
                    print(f"   Pattern: {g.get('pattern', 'N/A')}")
                    print(f"   Ghiciri: {g['total_guesses']}, Greșeli: {len(g.get('wrong_letters', []))}")
                    if g.get('composite_score'):
                        print(f"   Scor: {g['composite_score']:.2f}")
            
            elif choice == "11":  # Abort game
                if not client.current_session_id or not client.current_game_id:
                    print("❌ Niciun joc activ!")
                    continue
                
                result = client.abort_game(client.current_session_id, client.current_game_id)
                print(f"✅ Joc abandonat: {result['message']}")
                client.current_game_id = None
            
            elif choice == "12":  # Session stats
                session_id = input("Session ID [curent]: ").strip() or client.current_session_id
                if not session_id:
                    print("❌ Nicio sesiune selectată!")
                    continue
                
                stats = client.get_session_stats(session_id)
                print(f"\n📊 STATISTICI SESIUNE: {session_id}")
                print(json.dumps(stats, indent=2))
            
            elif choice == "13":  # User stats
                user_id = input(f"User ID [{client.user_id}]: ").strip() or client.user_id
                period = input("Perioadă (all/today/week/month) [all]: ").strip() or "all"
                
                stats = client.get_user_stats(user_id, period)
                print(f"\n📊 STATISTICI UTILIZATOR: {user_id}")
                print(json.dumps(stats, indent=2))
            
            elif choice == "14":  # Global stats
                period = input("Perioadă (all/today/week/month) [all]: ").strip() or "all"
                stats = client.get_global_stats(period)
                print(f"\n🌍 STATISTICI GLOBALE")
                print(json.dumps(stats, indent=2))
            
            elif choice == "15":  # Leaderboard
                metric = input("Metric (composite_score/win_rate/avg_guesses) [composite_score]: ").strip() or "composite_score"
                limit = int(input("Limită [10]: ").strip() or "10")
                
                result = client.get_leaderboard(metric=metric, limit=limit)
                print(f"\n🏆 LEADERBOARD - {metric.upper()}")
                for i, entry in enumerate(result.get("leaderboard", []), 1):
                    print(f"\n{i}. {entry['nickname']} (User: {entry['user_id']})")
                    print(f"   Scor mediu: {entry.get('avg_composite_score', 0):.2f}")
                    print(f"   Win rate: {entry['win_rate']*100:.1f}%")
                    print(f"   Jocuri: {entry['total_games']}")
            
            else:
                print("❌ Opțiune invalidă!")
        
        except requests.HTTPError as e:
            print(f"\n❌ EROARE HTTP: {e}")
            if e.response is not None:
                try:
                    error_detail = e.response.json()
                    print(f"Detalii: {json.dumps(error_detail, indent=2)}")
                except:
                    print(f"Response: {e.response.text}")
        except Exception as e:
            print(f"\n❌ EROARE: {e}")
        
        input("\n⏎ Apasă Enter pentru a continua...")

if __name__ == "__main__":
    main()
