#!/usr/bin/env python3
"""Hangman GUI Client - Interfață grafică profesională cu pagini."""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import requests
import json
from typing import Optional
import threading
import subprocess
import sys
import os
import time

BASE_URL = "http://localhost:8000/api/v1"

class HangmanAPI:
    """API wrapper pentru comunicarea cu serverul."""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.token: Optional[str] = None
        self.user_id: Optional[str] = None
    
    def _headers(self):
        if not self.token:
            raise Exception("Nu ești autentificat!")
        return {"Authorization": f"Bearer {self.token}"}
    
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
    
    def create_session(self, num_games: int, difficulty: str, max_misses: int, seed: int = None):
        data = {"num_games": num_games, "difficulty": difficulty, "max_misses": max_misses}
        if seed:
            data["seed"] = seed
        resp = requests.post(f"{self.base_url}/sessions", 
            headers=self._headers(), json=data)
        resp.raise_for_status()
        return resp.json()
    
    def list_sessions(self):
        resp = requests.get(f"{self.base_url}/sessions", headers=self._headers())
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
    
    def guess(self, session_id: str, game_id: str, guess: str):
        resp = requests.post(f"{self.base_url}/sessions/{session_id}/games/{game_id}/guess",
            headers=self._headers(),
            json={"guess": guess})
        resp.raise_for_status()
        return resp.json()
    
    def get_leaderboard(self):
        resp = requests.get(f"{self.base_url}/leaderboard",
            params={"metric": "composite_score", "limit": 10})
        resp.raise_for_status()
        return resp.json()
    
    def get_user_stats(self, user_id: str):
        resp = requests.get(f"{self.base_url}/users/{user_id}/stats",
            headers=self._headers())
        resp.raise_for_status()
        return resp.json()

class HangmanGUI:
    """Interfața grafică principală."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("🎮 Hangman Game Client")
        self.root.geometry("900x700")
        self.root.resizable(True, True)
        
        self.api = HangmanAPI()
        self.current_session_id = None
        self.current_game_id = None
        
        # Stiluri
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Culori
        self.bg_color = "#2c3e50"
        self.fg_color = "#ecf0f1"
        self.accent_color = "#3498db"
        self.success_color = "#27ae60"
        self.error_color = "#e74c3c"
        
        self.root.configure(bg=self.bg_color)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Configurează interfața."""
        # Header
        header_frame = tk.Frame(self.root, bg=self.accent_color, height=60)
        header_frame.pack(fill=tk.X, side=tk.TOP)
        
        tk.Label(header_frame, text="🎮 HANGMAN GAME", 
                font=("Arial", 24, "bold"), 
                bg=self.accent_color, fg="white").pack(pady=10)
        
        # Main container
        main_container = tk.Frame(self.root, bg=self.bg_color)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel - Auth & Sessions
        left_panel = tk.Frame(main_container, bg=self.bg_color, width=300)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        self.setup_auth_panel(left_panel)
        self.setup_session_panel(left_panel)
        
        # Right panel - Game
        right_panel = tk.Frame(main_container, bg=self.bg_color)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.setup_game_panel(right_panel)
        
        # Status bar
        self.status_var = tk.StringVar(value="Neautentificat")
        status_bar = tk.Label(self.root, textvariable=self.status_var, 
                             bg=self.bg_color, fg=self.fg_color,
                             anchor=tk.W, relief=tk.SUNKEN)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def setup_auth_panel(self, parent):
        """Panoul de autentificare."""
        frame = tk.LabelFrame(parent, text="👤 Autentificare", 
                             bg=self.bg_color, fg=self.fg_color,
                             font=("Arial", 12, "bold"))
        frame.pack(fill=tk.X, pady=(0, 10))
        
        # Email
        tk.Label(frame, text="Email:", bg=self.bg_color, fg=self.fg_color).pack(anchor=tk.W, padx=10, pady=(10, 0))
        self.email_entry = tk.Entry(frame, width=30)
        self.email_entry.pack(padx=10, pady=5)
        
        # Password
        tk.Label(frame, text="Parolă:", bg=self.bg_color, fg=self.fg_color).pack(anchor=tk.W, padx=10)
        self.password_entry = tk.Entry(frame, width=30, show="*")
        self.password_entry.pack(padx=10, pady=5)
        
        # Nickname (optional)
        tk.Label(frame, text="Nickname (opțional):", bg=self.bg_color, fg=self.fg_color).pack(anchor=tk.W, padx=10)
        self.nickname_entry = tk.Entry(frame, width=30)
        self.nickname_entry.pack(padx=10, pady=5)
        
        # Buttons
        btn_frame = tk.Frame(frame, bg=self.bg_color)
        btn_frame.pack(pady=10)
        
        tk.Button(btn_frame, text="Înregistrare", command=self.register,
                 bg=self.success_color, fg="white", width=12).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Login", command=self.login,
                 bg=self.accent_color, fg="white", width=12).pack(side=tk.LEFT, padx=5)
    
    def setup_session_panel(self, parent):
        """Panoul pentru sesiuni."""
        frame = tk.LabelFrame(parent, text="🎯 Sesiuni & Setări", 
                             bg=self.bg_color, fg=self.fg_color,
                             font=("Arial", 12, "bold"))
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Număr jocuri
        tk.Label(frame, text="Număr jocuri:", bg=self.bg_color, fg=self.fg_color).pack(anchor=tk.W, padx=10, pady=(10, 0))
        self.num_games_var = tk.IntVar(value=1)
        tk.Spinbox(frame, from_=1, to=20, textvariable=self.num_games_var, width=28).pack(padx=10, pady=5)
        
        # Dificultate
        tk.Label(frame, text="Dificultate:", bg=self.bg_color, fg=self.fg_color).pack(anchor=tk.W, padx=10)
        self.difficulty_var = tk.StringVar(value="medium")
        difficulty_combo = ttk.Combobox(frame, textvariable=self.difficulty_var, 
                                       values=["easy", "medium", "hard"], 
                                       state="readonly", width=27)
        difficulty_combo.pack(padx=10, pady=5)
        
        # Max greșeli
        tk.Label(frame, text="Greșeli maxime:", bg=self.bg_color, fg=self.fg_color).pack(anchor=tk.W, padx=10)
        self.max_misses_var = tk.IntVar(value=6)
        tk.Spinbox(frame, from_=1, to=10, textvariable=self.max_misses_var, width=28).pack(padx=10, pady=5)
        
        # Seed
        tk.Label(frame, text="Seed (opțional):", bg=self.bg_color, fg=self.fg_color).pack(anchor=tk.W, padx=10)
        self.seed_entry = tk.Entry(frame, width=30)
        self.seed_entry.pack(padx=10, pady=5)
        
        # Buttons
        tk.Button(frame, text="🎯 Creează Sesiune", command=self.create_session,
                 bg=self.success_color, fg="white", width=25).pack(padx=10, pady=10)
        
        tk.Button(frame, text="📋 Vezi Sesiunile Mele", command=self.show_sessions,
                 bg=self.accent_color, fg="white", width=25).pack(padx=10, pady=(0, 10))
        
        tk.Button(frame, text="🏆 Leaderboard", command=self.show_leaderboard,
                 bg="#9b59b6", fg="white", width=25).pack(padx=10, pady=(0, 10))
        
        tk.Button(frame, text="📊 Statisticile Mele", command=self.show_stats,
                 bg="#e67e22", fg="white", width=25).pack(padx=10, pady=(0, 10))
    
    def setup_game_panel(self, parent):
        """Panoul de joc."""
        # Info frame
        info_frame = tk.Frame(parent, bg=self.bg_color)
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.session_label = tk.Label(info_frame, text="Sesiune: -", 
                                      bg=self.bg_color, fg=self.fg_color,
                                      font=("Arial", 10))
        self.session_label.pack(side=tk.LEFT, padx=10)
        
        self.game_label = tk.Label(info_frame, text="Joc: -", 
                                   bg=self.bg_color, fg=self.fg_color,
                                   font=("Arial", 10))
        self.game_label.pack(side=tk.LEFT, padx=10)
        
        # Game display frame
        game_frame = tk.LabelFrame(parent, text="🎲 JOC", 
                                  bg=self.bg_color, fg=self.fg_color,
                                  font=("Arial", 14, "bold"))
        game_frame.pack(fill=tk.BOTH, expand=True)
        
        # Pattern display
        self.pattern_var = tk.StringVar(value="_ _ _ _ _ _")
        pattern_label = tk.Label(game_frame, textvariable=self.pattern_var,
                                font=("Courier New", 36, "bold"),
                                bg=self.bg_color, fg="#f39c12")
        pattern_label.pack(pady=20)
        
        # Game info
        info_container = tk.Frame(game_frame, bg=self.bg_color)
        info_container.pack(pady=10)
        
        self.wrong_letters_var = tk.StringVar(value="Greșeli: -")
        tk.Label(info_container, textvariable=self.wrong_letters_var,
                font=("Arial", 12), bg=self.bg_color, fg=self.error_color).pack()
        
        self.remaining_var = tk.StringVar(value="Rămase: - | Ghiciri: -")
        tk.Label(info_container, textvariable=self.remaining_var,
                font=("Arial", 12), bg=self.bg_color, fg=self.fg_color).pack()
        
        # Input frame
        input_frame = tk.Frame(game_frame, bg=self.bg_color)
        input_frame.pack(pady=20)
        
        tk.Label(input_frame, text="Ghicește:", 
                bg=self.bg_color, fg=self.fg_color,
                font=("Arial", 12)).pack(side=tk.LEFT, padx=5)
        
        self.guess_entry = tk.Entry(input_frame, width=20, font=("Arial", 14))
        self.guess_entry.pack(side=tk.LEFT, padx=5)
        self.guess_entry.bind('<Return>', lambda e: self.make_guess())
        
        tk.Button(input_frame, text="✓ Trimite", command=self.make_guess,
                 bg=self.success_color, fg="white", 
                 font=("Arial", 12, "bold")).pack(side=tk.LEFT, padx=5)
        
        # Control buttons
        control_frame = tk.Frame(game_frame, bg=self.bg_color)
        control_frame.pack(pady=10)
        
        tk.Button(control_frame, text="🎲 Joc Nou", command=self.create_game,
                 bg=self.accent_color, fg="white", width=15).pack(side=tk.LEFT, padx=5)
        
        tk.Button(control_frame, text="🔄 Reîmprospătează", command=self.refresh_game,
                 bg="#16a085", fg="white", width=15).pack(side=tk.LEFT, padx=5)
        
        tk.Button(control_frame, text="❌ Abandonează", command=self.abort_game,
                 bg=self.error_color, fg="white", width=15).pack(side=tk.LEFT, padx=5)
        
        # Log area
        log_frame = tk.LabelFrame(parent, text="📝 Istoric", 
                                 bg=self.bg_color, fg=self.fg_color,
                                 font=("Arial", 10, "bold"))
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, 
                                                  bg="#34495e", fg=self.fg_color,
                                                  font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def log(self, message, color=None):
        """Adaugă mesaj în log."""
        self.log_text.insert(tk.END, message + "\n")
        if color:
            # Adaugă tag pentru culoare (simplificat)
            pass
        self.log_text.see(tk.END)
    
    def register(self):
        """Înregistrare utilizator."""
        email = self.email_entry.get().strip()
        password = self.password_entry.get().strip()
        nickname = self.nickname_entry.get().strip() or None
        
        if not email or not password:
            messagebox.showerror("Eroare", "Email și parola sunt obligatorii!")
            return
        
        try:
            result = self.api.register(email, password, nickname)
            messagebox.showinfo("Succes", 
                f"Înregistrare reușită!\nUser ID: {result['user_id']}\nAdmin: {'DA' if result.get('is_admin') else 'NU'}")
            self.log(f"✓ Înregistrat: {result['user_id']}")
        except requests.HTTPError as e:
            error = e.response.json() if e.response else {}
            messagebox.showerror("Eroare", error.get('detail', str(e)))
    
    def login(self):
        """Login utilizator."""
        email = self.email_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if not email or not password:
            messagebox.showerror("Eroare", "Email și parola sunt obligatorii!")
            return
        
        try:
            result = self.api.login(email, password)
            self.status_var.set(f"✓ Autentificat: {self.api.user_id}")
            self.log(f"✓ Login reușit: {self.api.user_id}")
            messagebox.showinfo("Succes", f"Bun venit!\nUser ID: {self.api.user_id}")
        except requests.HTTPError as e:
            error = e.response.json() if e.response else {}
            messagebox.showerror("Eroare", error.get('detail', str(e)))
    
    def create_session(self):
        """Creează sesiune nouă."""
        if not self.api.token:
            messagebox.showerror("Eroare", "Trebuie să te autentifici mai întâi!")
            return
        
        try:
            seed = self.seed_entry.get().strip()
            seed = int(seed) if seed else None
            
            result = self.api.create_session(
                self.num_games_var.get(),
                self.difficulty_var.get(),
                self.max_misses_var.get(),
                seed
            )
            
            self.current_session_id = result['session_id']
            self.session_label.config(text=f"Sesiune: {self.current_session_id}")
            
            self.log(f"✓ Sesiune creată: {self.current_session_id}")
            self.log(f"  Dificultate: {result['difficulty']}, Jocuri: {result['num_games']}")
            
            messagebox.showinfo("Succes", 
                f"Sesiune creată!\nID: {self.current_session_id}\nDificultate: {result['difficulty']}")
        except Exception as e:
            messagebox.showerror("Eroare", str(e))
    
    def create_game(self):
        """Creează joc nou."""
        if not self.current_session_id:
            messagebox.showerror("Eroare", "Creează o sesiune mai întâi!")
            return
        
        try:
            result = self.api.create_game(self.current_session_id)
            self.current_game_id = result['game_id']
            self.game_label.config(text=f"Joc: {self.current_game_id}")
            
            self.pattern_var.set(" ".join(result['pattern']))
            self.wrong_letters_var.set("Greșeli: -")
            self.remaining_var.set(f"Rămase: {result['max_misses']} | Ghiciri: 0")
            
            self.log(f"\n🎲 JOC NOU: {self.current_game_id}")
            self.log(f"  Pattern: {result['pattern']} ({result['length']} litere)")
            self.log(f"  Max greșeli: {result['max_misses']}")
            
            self.guess_entry.delete(0, tk.END)
            self.guess_entry.focus()
            
        except Exception as e:
            messagebox.showerror("Eroare", str(e))
    
    def refresh_game(self):
        """Reîmprospătează starea jocului."""
        if not self.current_session_id or not self.current_game_id:
            messagebox.showwarning("Atenție", "Niciun joc activ!")
            return
        
        try:
            state = self.api.get_game_state(self.current_session_id, self.current_game_id)
            self.update_game_display(state)
        except Exception as e:
            messagebox.showerror("Eroare", str(e))
    
    def make_guess(self):
        """Face o ghicire."""
        if not self.current_session_id or not self.current_game_id:
            messagebox.showwarning("Atenție", "Creează un joc mai întâi!")
            return
        
        guess = self.guess_entry.get().strip().lower()
        if not guess:
            return
        
        try:
            result = self.api.guess(self.current_session_id, self.current_game_id, guess)
            
            if len(guess) == 1:
                self.log(f"→ Literă: {guess} - Pattern: {result['pattern']}")
            else:
                self.log(f"→ Cuvânt: {guess} - {result['status']}")
            
            self.update_game_display(result)
            self.guess_entry.delete(0, tk.END)
            
            # Verifică dacă jocul s-a terminat
            if result['status'] != 'IN_PROGRESS':
                self.show_game_result(result)
            
        except requests.HTTPError as e:
            error = e.response.json() if e.response else {}
            messagebox.showerror("Eroare", error.get('detail', str(e)))
            self.log(f"✗ Eroare: {error.get('detail', str(e))}")
    
    def update_game_display(self, state):
        """Actualizează afișajul jocului."""
        self.pattern_var.set(" ".join(state['pattern']))
        
        if state['wrong_letters']:
            self.wrong_letters_var.set(f"Greșeli: {', '.join(state['wrong_letters'])}")
        else:
            self.wrong_letters_var.set("Greșeli: -")
        
        self.remaining_var.set(
            f"Rămase: {state['remaining_misses']} | Ghiciri: {state['total_guesses']}"
        )
    
    def show_game_result(self, state):
        """Afișează rezultatul final al jocului."""
        if state['status'] == 'WON':
            title = "🎉 AI CÂȘTIGAT!"
            color = self.success_color
        elif state['status'] == 'LOST':
            title = "😔 AI PIERDUT"
            color = self.error_color
        else:
            title = "⏸️ JOC ABANDONAT"
            color = "#95a5a6"
        
        message = f"Status: {state['status']}\n"
        
        if state.get('result'):
            message += f"\nCuvânt secret: {state['result']['secret']}\n"
            message += f"Ghiciri: {state['total_guesses']}\n"
            
            if state.get('composite_score'):
                message += f"Scor: {state['composite_score']:.2f}\n"
            if state.get('time_seconds'):
                message += f"Timp: {state['time_seconds']:.2f}s"
        
        self.log(f"\n{title}")
        self.log(f"  {message}")
        
        messagebox.showinfo(title, message)
        
        self.current_game_id = None
        self.game_label.config(text="Joc: -")
    
    def abort_game(self):
        """Abandonează jocul curent."""
        if not self.current_game_id:
            messagebox.showwarning("Atenție", "Niciun joc activ!")
            return
        
        if messagebox.askyesno("Confirmare", "Sigur vrei să abandonezi jocul?"):
            # Implementează abandon
            self.log("❌ Joc abandonat")
            self.current_game_id = None
            self.game_label.config(text="Joc: -")
    
    def show_sessions(self):
        """Afișează sesiunile utilizatorului."""
        if not self.api.token:
            messagebox.showerror("Eroare", "Trebuie să te autentifici!")
            return
        
        try:
            sessions = self.api.list_sessions()
            
            window = tk.Toplevel(self.root)
            window.title("📋 Sesiunile Mele")
            window.geometry("600x400")
            window.configure(bg=self.bg_color)
            
            text = scrolledtext.ScrolledText(window, bg="#34495e", fg=self.fg_color,
                                            font=("Consolas", 10))
            text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            text.insert(tk.END, f"SESIUNILE MELE ({len(sessions)} total)\n")
            text.insert(tk.END, "="*60 + "\n\n")
            
            for s in sessions:
                status_emoji = "✅" if s['status'] == "COMPLETED" else "🎮" if s['status'] == "IN_PROGRESS" else "❌"
                text.insert(tk.END, f"{status_emoji} {s['session_id']} - {s['status']}\n")
                text.insert(tk.END, f"   Jocuri: {s['games_created']}/{s['num_games']}\n")
                text.insert(tk.END, f"   Dificultate: {s['difficulty']}, Max greșeli: {s['max_misses']}\n\n")
            
            text.config(state=tk.DISABLED)
            
        except Exception as e:
            messagebox.showerror("Eroare", str(e))
    
    def show_leaderboard(self):
        """Afișează leaderboard-ul."""
        try:
            result = self.api.get_leaderboard()
            
            window = tk.Toplevel(self.root)
            window.title("🏆 Leaderboard")
            window.geometry("600x400")
            window.configure(bg=self.bg_color)
            
            text = scrolledtext.ScrolledText(window, bg="#34495e", fg=self.fg_color,
                                            font=("Consolas", 10))
            text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            text.insert(tk.END, "🏆 LEADERBOARD - TOP 10\n")
            text.insert(tk.END, "="*60 + "\n\n")
            
            for i, entry in enumerate(result.get("leaderboard", []), 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                text.insert(tk.END, f"{medal} {entry['nickname']} (User: {entry['user_id']})\n")
                text.insert(tk.END, f"   Scor mediu: {entry.get('avg_composite_score', 0):.2f}\n")
                text.insert(tk.END, f"   Win rate: {entry['win_rate']*100:.1f}%\n")
                text.insert(tk.END, f"   Jocuri: {entry['total_games']}\n\n")
            
            text.config(state=tk.DISABLED)
            
        except Exception as e:
            messagebox.showerror("Eroare", str(e))
    
    def show_stats(self):
        """Afișează statisticile utilizatorului."""
        if not self.api.user_id:
            messagebox.showerror("Eroare", "Trebuie să te autentifici!")
            return
        
        try:
            stats = self.api.get_user_stats(self.api.user_id)
            
            window = tk.Toplevel(self.root)
            window.title("📊 Statisticile Mele")
            window.geometry("500x400")
            window.configure(bg=self.bg_color)
            
            text = scrolledtext.ScrolledText(window, bg="#34495e", fg=self.fg_color,
                                            font=("Consolas", 10))
            text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            text.insert(tk.END, f"📊 STATISTICI - {self.api.user_id}\n")
            text.insert(tk.END, "="*50 + "\n\n")
            text.insert(tk.END, json.dumps(stats, indent=2))
            text.config(state=tk.DISABLED)
            
        except Exception as e:
            messagebox.showerror("Eroare", str(e))

def main():
    root = tk.Tk()
    app = HangmanGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
