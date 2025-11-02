#!/usr/bin/env python3
"""
Hangman GUI Client Professional
Interfață grafică completă cu pagini separate pentru fiecare funcționalitate.
Pornește automat serverul la început.
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import requests
import json
import subprocess
import sys
import os
import time
import threading
from ui_logger import get_logger, init_logger

BASE_URL = "http://localhost:8000/api/v1"

# Inițializează logger-ul cu path absolut
import os
log_dir = os.path.join(os.path.dirname(__file__), "logs")
logger = init_logger(log_dir)

class HangmanAPI:
    """Wrapper pentru API-ul serverului."""
    
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url
        self.token = None
        self.user_id = None
        self.email = None
        self.nickname = None
    
    def _headers(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}
    
    def register(self, email, password, nickname=None):
        logger.log_api_call("POST", "/auth/register")
        logger.debug(f"Register attempt: email={email}, nickname={nickname}")
        try:
            data = {"email": email, "password": password}
            if nickname:
                data["nickname"] = nickname
            resp = requests.post(f"{self.base_url}/auth/register", json=data)
            resp.raise_for_status()
            result = resp.json()
            logger.log_api_call("POST", "/auth/register", resp.status_code)
            logger.info(f"Register SUCCESS: user_id={result.get('user_id')}, is_admin={result.get('is_admin')}")
            return result
        except Exception as e:
            logger.log_api_call("POST", "/auth/register", error=str(e))
            logger.log_exception(e, "register")
            raise
    
    def login(self, email, password):
        logger.log_api_call("POST", "/auth/login")
        logger.debug(f"Login attempt: email={email}")
        try:
            resp = requests.post(f"{self.base_url}/auth/login", 
                                json={"email": email, "password": password})
            resp.raise_for_status()
            data = resp.json()
            self.token = data["access_token"]
            self.user_id = data["user_id"]
            self.email = email
            logger.log_api_call("POST", "/auth/login", resp.status_code)
            logger.info(f"Login SUCCESS: user_id={self.user_id}, token={self.token[:20]}...")
            return data
        except Exception as e:
            logger.log_api_call("POST", "/auth/login", error=str(e))
            logger.log_exception(e, "login")
            raise
    
    def delete_account(self):
        """Delete the current user account."""
        resp = requests.delete(f"{self.base_url}/users/me", headers=self._headers())
        resp.raise_for_status()
        # 204 No Content - no JSON response
        return {"status": "deleted"}
    
    def create_session(self, **kwargs):
        resp = requests.post(f"{self.base_url}/sessions", 
                            headers=self._headers(), json=kwargs)
        resp.raise_for_status()
        return resp.json()
    
    def list_sessions(self):
        resp = requests.get(f"{self.base_url}/sessions", headers=self._headers())
        resp.raise_for_status()
        return resp.json()
    
    def get_session(self, session_id):
        resp = requests.get(f"{self.base_url}/sessions/{session_id}", headers=self._headers())
        resp.raise_for_status()
        return resp.json()
    
    def abort_session(self, session_id):
        resp = requests.post(f"{self.base_url}/sessions/{session_id}/abort", headers=self._headers())
        resp.raise_for_status()
        return resp.json()
    
    def create_game(self, session_id):
        resp = requests.post(f"{self.base_url}/sessions/{session_id}/games", headers=self._headers())
        resp.raise_for_status()
        return resp.json()
    
    def get_game_state(self, session_id, game_id):
        resp = requests.get(f"{self.base_url}/sessions/{session_id}/games/{game_id}/state", 
                           headers=self._headers())
        resp.raise_for_status()
        return resp.json()
    
    def make_guess(self, session_id, game_id, guess):
        # Determine if it's a letter (single char) or word guess
        payload = {"letter": guess} if len(guess) == 1 else {"word": guess}
        resp = requests.post(f"{self.base_url}/sessions/{session_id}/games/{game_id}/guess",
                            headers=self._headers(), json=payload)
        resp.raise_for_status()
        return resp.json()
    
    def abort_game(self, session_id, game_id):
        resp = requests.post(f"{self.base_url}/sessions/{session_id}/games/{game_id}/abort",
                            headers=self._headers())
        resp.raise_for_status()
        return resp.json()
    
    def list_session_games(self, session_id):
        resp = requests.get(f"{self.base_url}/sessions/{session_id}/games", headers=self._headers())
        resp.raise_for_status()
        return resp.json()
    
    def get_user_stats(self, user_id, period="all"):
        resp = requests.get(f"{self.base_url}/users/{user_id}/stats",
                           headers=self._headers(), params={"period": period})
        resp.raise_for_status()
        return resp.json()
    
    def get_session_stats(self, session_id):
        resp = requests.get(f"{self.base_url}/sessions/{session_id}/stats", headers=self._headers())
        resp.raise_for_status()
        return resp.json()
    
    def get_global_stats(self, period="all"):
        resp = requests.get(f"{self.base_url}/stats/global", params={"period": period})
        resp.raise_for_status()
        return resp.json()
    
    def get_leaderboard(self, metric="composite_score", period="all", limit=10):
        resp = requests.get(f"{self.base_url}/leaderboard",
                           params={"metric": metric, "period": period, "limit": limit})
        resp.raise_for_status()
        return resp.json()
    
    def list_dictionaries(self):
        resp = requests.get(f"{self.base_url}/admin/dictionaries", headers=self._headers())
        resp.raise_for_status()
        return resp.json()

class HangmanGUI:
    """Interfața grafică principală cu sistem de pagini."""
    
    def __init__(self, root):
        logger.info("🎮 Inițializare HangmanGUI")
        
        self.root = root
        self.root.title("🎮 Hangman Game - Professional Client")
        self.root.geometry("1200x800")
        
        # Theme colors
        self.bg_primary = "#1a1a2e"
        self.bg_secondary = "#16213e"
        self.accent = "#0f3460"
        self.highlight = "#e94560"
        self.success = "#27ae60"
        self.warning = "#f39c12"
        self.text = "#eaeaea"
        
        self.root.configure(bg=self.bg_primary)
        
        self.api = HangmanAPI()
        self.server_process = None
        
        # State
        self.current_session = None
        self.current_game = None
        
        logger.debug("GUI configuration complete")
        
        # Status bar
        self.status_bar = tk.Frame(root, bg=self.bg_secondary, height=25)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_bar.pack_propagate(False)
        
        self.status_label = tk.Label(self.status_bar, text="🟡 Inițializare...", 
                                     bg=self.bg_secondary, fg=self.text,
                                     font=("Arial", 9))
        self.status_label.pack(side=tk.LEFT, padx=10)
        
        # Start server
        self.start_server()
        
        # Setup UI
        self.setup_login_page()
    
    def start_server(self):
        """Pornește serverul în background."""
        logger.log_server_event("START_ATTEMPT", "Checking if server already running")
        
        def run_server():
            try:
                # Verifică dacă serverul deja rulează
                try:
                    resp = requests.get("http://localhost:8000/healthz", timeout=2)
                    if resp.status_code == 200:
                        print("✓ Serverul deja rulează")
                        logger.log_server_event("ALREADY_RUNNING", "Server is already active")
                        self.show_server_status("🟢 Server conectat")
                        return
                except:
                    pass
                
                # Pornește serverul
                print("🚀 Pornesc serverul...")
                logger.log_server_event("LAUNCHING", "Starting uvicorn process")
                self.show_server_status("🟡 Server pornește (poate dura ~15-20s)...")
                
                server_dir = os.path.join(os.path.dirname(__file__), "..", "server")
                logger.debug(f"Server directory: {server_dir}")
                
                if sys.platform == "win32":
                    # Windows - pornește în fereastră PowerShell separată (vizibilă în background)
                    self.server_process = subprocess.Popen(
                        [sys.executable, "-m", "uvicorn", "src.main:app", 
                         "--host", "0.0.0.0", "--port", "8000"],
                        cwd=server_dir,
                        creationflags=subprocess.CREATE_NEW_CONSOLE
                    )
                else:
                    self.server_process = subprocess.Popen(
                        [sys.executable, "-m", "uvicorn", "src.main:app",
                         "--host", "0.0.0.0", "--port", "8000"],
                        cwd=server_dir,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                
                print(f"⏳ Proces pornit (PID: {self.server_process.pid}), aștept să devină disponibil...")
                logger.log_server_event("PROCESS_STARTED", f"PID: {self.server_process.pid}")
                
                # Așteaptă pornirea (până la 40 secunde, cu progress updates)
                for i in range(80):  # 40 secunde (80 * 0.5s)
                    try:
                        resp = requests.get("http://localhost:8000/healthz", timeout=1)
                        if resp.status_code == 200:
                            elapsed = i * 0.5
                            print(f"✓ Server pornit după {elapsed:.1f} secunde!")
                            logger.log_server_event("READY", f"Server ready after {elapsed:.1f}s")
                            self.show_server_status("🟢 Server ACTIV ✓")
                            return
                    except:
                        # Update progress la fiecare 2 secunde
                        if i % 4 == 0:
                            elapsed = i * 0.5
                            self.show_server_status(f"🟡 Pornire server... {elapsed:.0f}s")
                            if i % 8 == 0:  # Log la fiecare 4 secunde
                                logger.debug(f"Waiting for server... {elapsed:.0f}s")
                        time.sleep(0.5)
                
                print("⚠ Server-ul nu a pornit în 40 secunde")
                logger.error("SERVER_TIMEOUT: Server did not start within 40 seconds")
                self.show_server_status("🔴 Server timeout - încearcă să reporești aplicația")
            except Exception as e:
                print(f"❌ Eroare pornire server: {e}")
                logger.log_exception(e, "start_server")
                self.show_server_status(f"🔴 Eroare: {str(e)[:30]}")
        
        threading.Thread(target=run_server, daemon=True).start()
    
    def show_server_status(self, status):
        """Update server status (thread-safe)."""
        try:
            if hasattr(self, 'status_label'):
                self.root.after(0, lambda: self.status_label.config(text=status))
        except:
            pass
    
    def clear_window(self):
        """Șterge tot conținutul ferestrei (păstrează status bar)."""
        for widget in self.root.winfo_children():
            if widget != self.status_bar:  # Nu șterge status bar-ul
                widget.destroy()
        # Clear notification reference
        self.notification_frame = None
    
    def show_notification(self, message, type="success", duration=3000):
        """Afișează o notificare inline (fără messagebox).
        
        Args:
            message: Mesajul de afișat
            type: "success" (verde), "error" (roșu), "info" (albastru), "warning" (portocaliu)
            duration: Timp în ms (0 = permanent, apasă X pentru închidere)
        """
        # Remove old notification if exists
        if hasattr(self, 'notification_frame') and self.notification_frame:
            try:
                self.notification_frame.destroy()
            except:
                pass
        
        # Colors based on type
        colors = {
            "success": ("#27ae60", "✅"),
            "error": ("#e74c3c", "❌"),
            "info": ("#3498db", "ℹ️"),
            "warning": ("#f39c12", "⚠️")
        }
        
        bg_color, icon = colors.get(type, colors["info"])
        
        # Create notification frame at the top
        self.notification_frame = tk.Frame(self.root, bg=bg_color, height=50)
        self.notification_frame.pack(side=tk.TOP, fill=tk.X, after=self.status_bar)
        self.notification_frame.pack_propagate(False)
        
        # Icon and message
        tk.Label(self.notification_frame, text=f"{icon} {message}", 
                bg=bg_color, fg="white", font=("Arial", 11, "bold")).pack(side=tk.LEFT, padx=20, pady=12)
        
        # Close button (only if not auto-dismiss)
        if duration == 0:
            close_btn = tk.Label(self.notification_frame, text="✖", 
                                bg=bg_color, fg="white", font=("Arial", 14, "bold"),
                                cursor="hand2")
            close_btn.pack(side=tk.RIGHT, padx=10)
            close_btn.bind("<Button-1>", lambda e: self.notification_frame.destroy())
        
        # Auto-dismiss after duration
        if duration > 0:
            self.root.after(duration, lambda: self.notification_frame.destroy() if self.notification_frame else None)
    
    def create_header(self, title, subtitle=""):
        """Creează header pentru pagină."""
        header = tk.Frame(self.root, bg=self.accent, height=80)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(header, text=title, font=("Arial", 24, "bold"),
                bg=self.accent, fg=self.text).pack(pady=(15, 0))
        
        if subtitle:
            tk.Label(header, text=subtitle, font=("Arial", 10),
                    bg=self.accent, fg=self.text).pack()
        
        return header
    
    def create_menu_bar(self):
        """Creează bara de meniu."""
        menubar = tk.Frame(self.root, bg=self.bg_secondary, height=40)
        menubar.pack(fill=tk.X)
        
        buttons = [
            ("🏠 Dashboard", self.show_dashboard),
            ("🎯 Sesiuni", self.show_sessions_page),
            ("🎲 Joacă", self.show_game_page),
            ("📊 Statistici", self.show_stats_page),
            ("🏆 Leaderboard", self.show_leaderboard_page),
            ("⚙️ Setări", self.show_settings_page),
            ("🚪 Logout", self.logout)
        ]
        
        for text, command in buttons:
            btn = tk.Button(menubar, text=text, command=command,
                           bg=self.bg_secondary, fg=self.text,
                           relief=tk.FLAT, padx=15, pady=5,
                           font=("Arial", 9))
            btn.pack(side=tk.LEFT, padx=2)
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=self.accent))
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg=self.bg_secondary))
        
        # User info
        if self.api.user_id:
            user_label = tk.Label(menubar, text=f"👤 {self.api.user_id}",
                                 bg=self.bg_secondary, fg=self.text,
                                 font=("Arial", 9))
            user_label.pack(side=tk.RIGHT, padx=10)
    
    # ============= LOADING SPINNER =============
    def show_loading(self, message="Se încarcă..."):
        """Arată spinner de loading peste interfață."""
        self.loading_overlay = tk.Frame(self.root, bg='#1a1a2e')  # Fundal semi-opac
        self.loading_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.loading_overlay.lift()
        
        # Container pentru spinner
        spinner_frame = tk.Frame(self.loading_overlay, bg=self.bg_secondary, relief=tk.RAISED, bd=3)
        spinner_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        # Mesaj
        tk.Label(spinner_frame, text=message, font=("Arial", 14, "bold"),
                bg=self.bg_secondary, fg=self.text, padx=40, pady=20).pack()
        
        # Spinner animat (text simplu)
        self.spinner_label = tk.Label(spinner_frame, text="⏳", font=("Arial", 32),
                                     bg=self.bg_secondary, fg=self.highlight)
        self.spinner_label.pack(pady=(0, 20))
        
        # Animație spinner
        self.spinner_chars = ['⏳', '⌛']
        self.spinner_index = 0
        self.animate_spinner()
    
    def animate_spinner(self):
        """Animează spinner-ul."""
        if hasattr(self, 'spinner_label') and self.spinner_label.winfo_exists():
            self.spinner_index = (self.spinner_index + 1) % len(self.spinner_chars)
            self.spinner_label.config(text=self.spinner_chars[self.spinner_index])
            self.root.after(500, self.animate_spinner)
    
    def hide_loading(self):
        """Ascunde spinner-ul."""
        if hasattr(self, 'loading_overlay'):
            self.loading_overlay.destroy()
            delattr(self, 'loading_overlay')
    
    # ============= LOGIN PAGE =============
    def setup_login_page(self):
        """Pagina de login/register cu tabs."""
        self.clear_window()
        
        self.create_header("🎮 HANGMAN GAME", "Bun venit! Autentifică-te pentru a juca")
        
        # Container central
        container = tk.Frame(self.root, bg=self.bg_primary)
        container.pack(expand=True)
        
        # Tabs pentru Login/Register
        self.auth_notebook = ttk.Notebook(container)
        self.auth_notebook.pack(pady=20)
        
        # Tab Login
        self.login_tab = tk.Frame(self.auth_notebook, bg=self.bg_secondary)
        self.auth_notebook.add(self.login_tab, text="🔐 Autentificare")
        self.setup_login_tab()
        
        # Tab Register
        self.register_tab = tk.Frame(self.auth_notebook, bg=self.bg_secondary)
        self.auth_notebook.add(self.register_tab, text="📝 Înregistrare")
        self.setup_register_tab()
        
        # Help text jos
        help_frame = tk.Frame(container, bg=self.bg_primary)
        help_frame.pack(pady=20)
        
        help_text = """
💡 WORKFLOW RECOMANDAT:
1️⃣ Prima rulare: Mergi la tab "📝 Înregistrare" → creează cont
2️⃣ După înregistrare: alege "DA" la auto-login SAU
3️⃣ Folosește tab "🔐 Autentificare" cu același email/parolă
4️⃣ Primul user devine administrator automat! ⭐

📋 Datele sunt pre-completate în ambele tab-uri pentru test rapid.
        """
        tk.Label(help_frame, text=help_text, bg=self.bg_primary, fg=self.warning,
                font=("Arial", 9), justify=tk.LEFT).pack()
    
    def setup_login_tab(self):
        """Setup tab de login."""
        frame = tk.Frame(self.login_tab, bg=self.bg_secondary, padx=50, pady=30)
        frame.pack(expand=True, fill=tk.BOTH)
        
        tk.Label(frame, text="Email:", bg=self.bg_secondary, fg=self.text,
                font=("Arial", 11)).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.login_email = tk.Entry(frame, width=35, font=("Arial", 11))
        self.login_email.grid(row=1, column=0, pady=(0, 10))
        self.login_email.insert(0, "newuser@test.com")  # Synchronized cu register tab
        
        tk.Label(frame, text="Parolă:", bg=self.bg_secondary, fg=self.text,
                font=("Arial", 11)).grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        self.login_password = tk.Entry(frame, width=35, show="*", font=("Arial", 11))
        self.login_password.grid(row=3, column=0, pady=(0, 20))
        self.login_password.insert(0, "Password123")  # Synchronized cu register tab
        self.login_password.bind('<Return>', lambda e: self.do_login())
        
        # Hint label
        tk.Label(frame, text="💡 Dacă e prima rulare, creează cont în tab Înregistrare",
                bg=self.bg_secondary, fg=self.warning,
                font=("Arial", 8, "italic")).grid(row=5, column=0, pady=(10, 0))
        
        tk.Button(frame, text="🔓 Login", command=self.do_login,
                 bg=self.success, fg="white", font=("Arial", 12, "bold"),
                 width=30, pady=8).grid(row=4, column=0)
    
    def setup_register_tab(self):
        """Setup tab de înregistrare."""
        frame = tk.Frame(self.register_tab, bg=self.bg_secondary, padx=50, pady=30)
        frame.pack(expand=True, fill=tk.BOTH)
        
        tk.Label(frame, text="Email:", bg=self.bg_secondary, fg=self.text,
                font=("Arial", 11)).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.reg_email = tk.Entry(frame, width=35, font=("Arial", 11))
        self.reg_email.grid(row=1, column=0, pady=(0, 10))
        self.reg_email.insert(0, "newuser@test.com")  # Exemplu
        
        tk.Label(frame, text="Parolă:", bg=self.bg_secondary, fg=self.text,
                font=("Arial", 11)).grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        self.reg_password = tk.Entry(frame, width=35, show="*", font=("Arial", 11))
        self.reg_password.grid(row=3, column=0, pady=(0, 10))
        self.reg_password.insert(0, "Password123")  # Exemplu
        
        tk.Label(frame, text="Nickname (opțional):", bg=self.bg_secondary, fg=self.text,
                font=("Arial", 11)).grid(row=4, column=0, sticky=tk.W, pady=(0, 5))
        self.reg_nickname = tk.Entry(frame, width=35, font=("Arial", 11))
        self.reg_nickname.grid(row=5, column=0, pady=(0, 20))
        self.reg_nickname.insert(0, "Player")  # Exemplu
        
        tk.Button(frame, text="✍ Înregistrare", command=self.do_register,
                 bg=self.highlight, fg="white", font=("Arial", 12, "bold"),
                 width=30, pady=8).grid(row=6, column=0)
    
    def show_login_tab(self):
        """Switch la tab-ul de login."""
        if hasattr(self, 'auth_notebook'):
            self.auth_notebook.select(0)
    
    def do_login(self):
        """Execută login cu loading spinner."""
        email = self.login_email.get().strip()
        password = self.login_password.get().strip()
        
        logger.log_user_action("LOGIN_ATTEMPT", f"email={email}")
        
        if not email or not password:
            logger.warning("Login validation failed: empty email or password")
            self.show_notification("Completează email și parola!", "error")
            return
        
        # Dezactivează butoane și arată loading
        self.show_loading("Autentificare în curs...")
        logger.debug("Loading spinner displayed for login")
        
        def login_task():
            try:
                result = self.api.login(email, password)
                self.root.after(0, lambda: self.on_login_success(result))
            except requests.exceptions.HTTPError as e:
                error_msg = f"Eroare HTTP {e.response.status_code}"
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get('detail', str(e))
                    logger.error(f"Login HTTP error {e.response.status_code}: {error_msg}")
                except:
                    error_msg = str(e)
                    logger.error(f"Login HTTP error: {error_msg}")
                self.root.after(0, lambda: self.on_login_error(error_msg))
            except Exception as e:
                logger.log_exception(e, "login_task")
                self.root.after(0, lambda: self.on_login_error(str(e)))
        
        threading.Thread(target=login_task, daemon=True).start()
    
    def on_login_success(self, result):
        """Callback după login cu succes."""
        self.hide_loading()
        logger.info(f"✅ Login successful: user_id={result['user_id']}")
        logger.log_navigation("LOGIN_PAGE", "DASHBOARD")
        self.show_dashboard()
        self.show_notification(f"Bun venit! User ID: {result['user_id']}", "success")
    
    def on_login_error(self, error_msg):
        """Callback după eroare login."""
        self.hide_loading()
        logger.error(f"❌ Login failed: {error_msg}")
        self.show_notification(f"Nu m-am putut autentifica: {error_msg}", "error", duration=5000)
    
    def do_register(self):
        """Execută înregistrare cu loading spinner."""
        email = self.reg_email.get().strip()
        password = self.reg_password.get().strip()
        nickname = self.reg_nickname.get().strip() or None
        
        logger.log_user_action("REGISTER_ATTEMPT", f"email={email}, nickname={nickname}")
        
        if not email or not password:
            logger.warning("Register validation failed: empty email or password")
            self.show_notification("Email și parola sunt obligatorii!", "error")
            return
        
        # Arată loading
        self.show_loading("Creare cont în curs...")
        logger.debug("Loading spinner displayed for register")
        
        def register_task():
            try:
                result = self.api.register(email, password, nickname)
                self.root.after(0, lambda: self.on_register_success(result, email, password))
            except requests.exceptions.HTTPError as e:
                error_msg = f"Eroare HTTP {e.response.status_code}"
                try:
                    error_data = e.response.json()
                    if isinstance(error_data.get('detail'), list):
                        # Eroare de validare (422)
                        errors = []
                        for err in error_data['detail']:
                            field = err.get('loc', [''])[1] if len(err.get('loc', [])) > 1 else 'unknown'
                            msg = err.get('msg', 'Eroare validare')
                            errors.append(f"• {field}: {msg}")
                        error_msg = "Erori validare:\n" + "\n".join(errors)
                    else:
                        error_msg = error_data.get('detail', str(e))
                except:
                    error_msg = str(e)
                self.root.after(0, lambda: self.on_register_error(error_msg))
            except Exception as e:
                self.root.after(0, lambda: self.on_register_error(str(e)))
        
        threading.Thread(target=register_task, daemon=True).start()
    
    def on_register_success(self, result, email, password):
        """Callback după register cu succes."""
        self.hide_loading()
        is_admin = "DA ✓" if result.get('is_admin') else "NU"
        logger.info(f"✅ Register successful: user_id={result['user_id']}, is_admin={is_admin}")
        
        # Auto-login direct (fără confirmare)
        logger.log_user_action("AUTO_LOGIN", "Auto-login after registration")
        self.api.token = None  # Reset
        self.show_loading("Autentificare automată...")
        
        def auto_login():
            try:
                login_result = self.api.login(email, password)
                self.root.after(0, lambda: self.on_login_success(login_result))
            except Exception as e:
                logger.error(f"Auto-login failed: {e}")
                self.root.after(0, lambda: (
                    self.hide_loading(),
                    self.show_login_tab(),
                    self.show_notification("Cont creat! Loghează-te manual.", "info", duration=5000)
                ))
        
        threading.Thread(target=auto_login, daemon=True).start()
    
    def on_register_error(self, error_msg):
        """Callback după eroare register."""
        self.hide_loading()
        logger.error(f"❌ Register failed: {error_msg}")
        self.show_notification(error_msg, "error", duration=5000)
    
    def logout(self):
        """Logout."""
        logger.log_user_action("LOGOUT_ATTEMPT")
        if messagebox.askyesno("Logout", "Sigur vrei să ieși?"):
            logger.info(f"✅ Logout: user_id={self.api.user_id}")
            self.api.token = None
            self.api.user_id = None
            self.current_session = None
            self.current_game = None
            logger.log_navigation("ANY_PAGE", "LOGIN_PAGE")
            self.setup_login_page()
        else:
            logger.debug("Logout cancelled by user")
    
    # ============= DASHBOARD =============
    def show_dashboard(self):
        """Dashboard principal după login."""
        logger.log_navigation("PREVIOUS", "DASHBOARD")
        self.clear_window()
        self.create_header("🏠 Dashboard", f"Utilizator: {self.api.user_id}")
        self.create_menu_bar()
        
        # Main content
        content = tk.Frame(self.root, bg=self.bg_primary)
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Quick actions
        actions_frame = tk.LabelFrame(content, text="⚡ Acțiuni Rapide",
                                      bg=self.bg_secondary, fg=self.text,
                                      font=("Arial", 12, "bold"))
        actions_frame.pack(fill=tk.X, pady=(0, 20))
        
        buttons_info = [
            ("🎯 Creează Sesiune Nouă", self.show_create_session_page, self.success, 
             "Pornește o sesiune de joc nouă cu setări personalizate"),
            ("🎲 Joacă Acum", self.show_game_page, self.highlight,
             "Mergi direct la pagina de joc"),
            ("📊 Vezi Statistici", self.show_stats_page, self.accent,
             "Consultă statisticile tale de joc"),
            ("🏆 Leaderboard", self.show_leaderboard_page, self.warning,
             "Vezi clasamentul jucătorilor")
        ]
        
        for i, (text, cmd, color, desc) in enumerate(buttons_info):
            frame = tk.Frame(actions_frame, bg=self.bg_secondary)
            frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=10, pady=10)
            
            btn = tk.Button(frame, text=text, command=cmd,
                           bg=color, fg="white", font=("Arial", 11, "bold"),
                           pady=15, relief=tk.RAISED, bd=2)
            btn.pack(fill=tk.X)
            
            tk.Label(frame, text=desc, bg=self.bg_secondary, fg=self.text,
                    font=("Arial", 8), wraplength=200).pack()
        
        # Stats summary
        try:
            stats = self.api.get_user_stats(self.api.user_id)
            
            stats_frame = tk.LabelFrame(content, text="📈 Rezumat Statistici",
                                       bg=self.bg_secondary, fg=self.text,
                                       font=("Arial", 12, "bold"))
            stats_frame.pack(fill=tk.BOTH, expand=True)
            
            stats_grid = tk.Frame(stats_frame, bg=self.bg_secondary)
            stats_grid.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
            
            stat_items = [
                ("🎮 Total Jocuri", stats.get('total_games', 0)),
                ("✅ Jocuri Câștigate", stats.get('games_won', 0)),
                ("❌ Jocuri Pierdute", stats.get('games_lost', 0)),
                ("📊 Win Rate", f"{stats.get('win_rate', 0)*100:.1f}%"),
                ("🎯 Scor Mediu", f"{stats.get('avg_score', 0):.2f}"),
                ("⭐ Best Score", f"{stats.get('best_score', 0):.2f}")
            ]
            
            for i, (label, value) in enumerate(stat_items):
                row, col = i // 3, i % 3
                frame = tk.Frame(stats_grid, bg=self.accent, relief=tk.RAISED, bd=2)
                frame.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
                
                tk.Label(frame, text=label, bg=self.accent, fg=self.text,
                        font=("Arial", 10)).pack(pady=(10, 5))
                tk.Label(frame, text=str(value), bg=self.accent, fg=self.highlight,
                        font=("Arial", 18, "bold")).pack(pady=(0, 10))
            
            for i in range(3):
                stats_grid.columnconfigure(i, weight=1)
        except:
            pass
    
    def show_create_session_page(self):
        """Pagină dedicată pentru creare sesiune (conform spec Hangman Server)."""
        logger.log_navigation("PREVIOUS", "CREATE_SESSION")
        self.clear_window()
        self.create_header("🎯 Creează Sesiune Nouă", "Configurează parametrii setului de jocuri")
        self.create_menu_bar()
        
        content = tk.Frame(self.root, bg=self.bg_primary)
        content.pack(fill=tk.BOTH, expand=True, padx=30, pady=15)
        
        # Info box - Modern compact
        info_frame = tk.Frame(content, bg="#2c3e50", relief=tk.FLAT, bd=0)
        info_frame.pack(fill=tk.X, pady=(0, 15))
        
        info_text = "💡 Formularul este pre-completat cu date demo. Modifică parametrii după preferință sau apasă direct Creează!"
        tk.Label(info_frame, text=info_text, bg="#2c3e50", fg="#ecf0f1",
                font=("Arial", 9, "italic"), justify=tk.LEFT, wraplength=1000).pack(padx=15, pady=8)
        
        # Form principal - Modern card layout
        form_frame = tk.Frame(content, bg="#34495e", relief=tk.RAISED, bd=2)
        form_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Header form
        tk.Label(form_frame, text="⚙️ Configurare Parametri", 
                bg="#34495e", fg="#ecf0f1",
                font=("Arial", 13, "bold")).pack(pady=(15, 10))
        
        form = tk.Frame(form_frame, bg="#34495e")
        form.pack(padx=25, pady=(0, 15))
        
        # num_games - Compact
        tk.Label(form, text="📊 Număr jocuri:", bg="#34495e", fg="#ecf0f1",
                font=("Arial", 10, "bold")).grid(row=0, column=0, sticky=tk.W, pady=(5, 3))
        tk.Label(form, text="1=rapid | 100=batch | custom(max 1000)",
                bg="#34495e", fg="#95a5a6",
                font=("Arial", 8)).grid(row=1, column=0, columnspan=2, sticky=tk.W)
        
        num_games_var = tk.IntVar(value=3)  # Mock: 3 jocuri pentru demo
        num_games_frame = tk.Frame(form, bg="#34495e")
        num_games_frame.grid(row=2, column=0, columnspan=2, pady=(3, 10), sticky=tk.W)
        
        tk.Radiobutton(num_games_frame, text="1", variable=num_games_var, value=1,
                      bg="#34495e", fg="#ecf0f1", selectcolor="#27ae60",
                      font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=3)
        tk.Radiobutton(num_games_frame, text="3", variable=num_games_var, value=3,
                      bg="#34495e", fg="#ecf0f1", selectcolor="#27ae60",
                      font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=3)
        tk.Radiobutton(num_games_frame, text="100", variable=num_games_var, value=100,
                      bg="#34495e", fg="#ecf0f1", selectcolor="#27ae60",
                      font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=3)
        
        tk.Label(num_games_frame, text="Custom:", bg="#34495e", fg="#ecf0f1",
                font=("Arial", 9)).pack(side=tk.LEFT, padx=(8, 3))
        num_games_custom = tk.Spinbox(num_games_frame, from_=1, to=1000, width=6,
                                      font=("Arial", 9))
        num_games_custom.delete(0, tk.END)
        num_games_custom.insert(0, "5")  # Mock: 5 pentru custom
        num_games_custom.pack(side=tk.LEFT)
        
        # difficulty - Compact
        tk.Label(form, text="🎯 Dificultate:", bg="#34495e", fg="#ecf0f1",
                font=("Arial", 10, "bold")).grid(row=3, column=0, sticky=tk.W, pady=(5, 3))
        tk.Label(form, text="easy=3-5 | normal=6-8 | hard=9+ | auto=mixt",
                bg="#34495e", fg="#95a5a6",
                font=("Arial", 8)).grid(row=4, column=0, columnspan=2, sticky=tk.W)
        
        difficulty_var = tk.StringVar(value="normal")  # Mock: normal pentru demonstrație
        difficulty_frame = tk.Frame(form, bg="#34495e")
        difficulty_frame.grid(row=5, column=0, columnspan=2, pady=(3, 10), sticky=tk.W)
        
        for diff in ["easy", "normal", "hard", "auto"]:
            tk.Radiobutton(difficulty_frame, text=diff.upper(), variable=difficulty_var, value=diff,
                          bg="#34495e", fg="#ecf0f1", selectcolor="#3498db",
                          font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=8)
        
        # max_misses - Compact
        tk.Label(form, text="❌ Greșeli maxime:", bg="#34495e", fg="#ecf0f1",
                font=("Arial", 10, "bold")).grid(row=6, column=0, sticky=tk.W, pady=(5, 3))
        tk.Label(form, text="1-10 (clasic=6)",
                bg="#34495e", fg="#95a5a6",
                font=("Arial", 8)).grid(row=7, column=0, columnspan=2, sticky=tk.W)
        
        max_misses_var = tk.IntVar(value=6)
        max_misses_frame = tk.Frame(form, bg="#34495e")
        max_misses_frame.grid(row=8, column=0, columnspan=2, pady=(3, 10), sticky=tk.W)
        
        tk.Scale(max_misses_frame, from_=1, to=10, orient=tk.HORIZONTAL, variable=max_misses_var,
                bg="#34495e", fg="#ecf0f1", highlightthickness=0, length=250,
                font=("Arial", 9), troughcolor="#2c3e50").pack(side=tk.LEFT)
        
        # seed - Compact
        tk.Label(form, text="🌱 Seed (opțional):", bg="#34495e", fg="#ecf0f1",
                font=("Arial", 10, "bold")).grid(row=9, column=0, sticky=tk.W, pady=(5, 3))
        tk.Label(form, text="Pentru reproducere (default: 42)",
                bg="#34495e", fg="#95a5a6",
                font=("Arial", 8)).grid(row=10, column=0, columnspan=2, sticky=tk.W)
        
        seed_entry = tk.Entry(form, width=15, font=("Arial", 10), bg="#2c3e50", fg="#ecf0f1",
                             insertbackground="#ecf0f1", relief=tk.FLAT, bd=2)
        seed_entry.insert(0, "42")  # Mock: seed 42 (număr popular în testing)
        seed_entry.grid(row=11, column=0, pady=(3, 10), sticky=tk.W)
        
        # Buttons - Modern design with separation
        tk.Frame(form, height=15, bg="#34495e").grid(row=12, column=0, columnspan=2)
        
        def reset_to_mock():
            """Resetează toate valorile la datele mock."""
            logger.log_user_action("RESET_MOCK_DATA")
            num_games_var.set(3)
            num_games_custom.delete(0, tk.END)
            num_games_custom.insert(0, "5")
            difficulty_var.set("normal")
            max_misses_var.set(6)
            seed_entry.delete(0, tk.END)
            seed_entry.insert(0, "42")
            logger.debug("Form reset to mock values")
        
        def create_session():
            logger.log_user_action("CREATE_SESSION", f"num_games={num_games_var.get()}, difficulty={difficulty_var.get()}")
            try:
                # Determină num_games
                if num_games_var.get() in [1, 3, 100]:
                    num_games = num_games_var.get()
                else:
                    num_games = int(num_games_custom.get())
                
                data = {
                    "num_games": num_games,
                    "difficulty": difficulty_var.get(),
                    "max_misses": max_misses_var.get()
                }
                
                if seed_entry.get().strip():
                    data["seed"] = int(seed_entry.get())
                
                logger.debug(f"Creating session with params: {data}")
                result = self.api.create_session(**data)
                self.current_session = result
                
                logger.info(f"✅ Session created: {result['session_id']}")
                
                # Build info message safely (not all fields may be present)
                info_parts = [
                    "✅ Sesiune creată cu succes!",
                    "",
                    f"🆔 ID: {result.get('session_id', 'N/A')}",
                    f"🎮 Jocuri: {result.get('num_games', data['num_games'])}",
                    f"🎯 Dificultate: {data.get('difficulty', 'N/A')}",
                    f"❌ Greșeli max: {data.get('max_misses', 6)}",
                ]
                
                if 'seed' in data:
                    info_parts.append(f"🌱 Seed: {data['seed']}")
                
                info_parts.extend(["", "🚀 Acum poți crea și juca jocuri!"])
                
                self.show_game_page()
                self.show_notification("Sesiune creată cu succes! " + info_parts[2], "success")
            except Exception as e:
                logger.log_exception(e, "create_session")
                error_msg = str(e)
                if "422" in error_msg:
                    error_msg = "Parametri invalizi! Verifică valorile introduse."
                elif "409" in error_msg:
                    error_msg = "Sesiune duplicată sau conflict. Încearcă din nou."
                self.show_notification(f"Nu am putut crea sesiunea: {error_msg}", "error", duration=5000)
        
        # BUTON PRINCIPAL MARE - Modern Card Style
        create_btn_frame = tk.Frame(form, bg="#27ae60", relief=tk.RAISED, bd=3)
        create_btn_frame.grid(row=13, column=0, columnspan=2, pady=(15, 10), sticky="ew")
        
        create_btn = tk.Button(create_btn_frame, text="🚀 CREEAZĂ SESIUNE ACUM", 
                              command=create_session,
                              bg="#27ae60", fg="white", 
                              font=("Arial", 14, "bold"),
                              relief=tk.FLAT, bd=0,
                              cursor="hand2",
                              activebackground="#229954",
                              activeforeground="white",
                              padx=40, pady=18)
        create_btn.pack(fill=tk.X, expand=True)
        
        # Hover effect simulation (manual)
        def on_enter(e):
            create_btn.config(bg="#229954")
        def on_leave(e):
            create_btn.config(bg="#27ae60")
        
        create_btn.bind("<Enter>", on_enter)
        create_btn.bind("<Leave>", on_leave)
        
        # Secondary buttons - Compact row
        secondary_frame = tk.Frame(form, bg="#34495e")
        secondary_frame.grid(row=14, column=0, columnspan=2, pady=(5, 10))
        
        tk.Button(secondary_frame, text="🔄 Reset", command=reset_to_mock,
                 bg="#3498db", fg="white", font=("Arial", 9),
                 relief=tk.FLAT, bd=0,
                 padx=15, pady=6).pack(side=tk.LEFT, padx=5)
        
        tk.Button(secondary_frame, text="❌ Anulează", command=self.show_sessions_page,
                 bg="#e74c3c", fg="white", font=("Arial", 9),
                 relief=tk.FLAT, bd=0,
                 padx=15, pady=6).pack(side=tk.LEFT, padx=5)
        
        tk.Button(secondary_frame, text="📋 Vezi Sesiuni", command=self.show_sessions_page,
                 bg="#95a5a6", fg="white", font=("Arial", 9),
                 relief=tk.FLAT, bd=0,
                 padx=15, pady=6).pack(side=tk.LEFT, padx=5)
    
    # ============= SESSIONS PAGE =============
    def show_sessions_page(self):
        """Pagina pentru management sesiuni."""
        logger.log_navigation("PREVIOUS", "SESSIONS")
        self.clear_window()
        self.create_header("🎯 Sesiuni", "Gestionează sesiunile tale de joc")
        self.create_menu_bar()
        
        content = tk.Frame(self.root, bg=self.bg_primary)
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Buttons
        btn_frame = tk.Frame(content, bg=self.bg_primary)
        btn_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Button(btn_frame, text="➕ Creează Sesiune Nouă", command=self.show_create_session_page,
                 bg=self.success, fg="white", font=("Arial", 11, "bold"),
                 padx=20, pady=8).pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_frame, text="🔄 Reîmprospătează Listă", command=self.show_sessions_page,
                 bg=self.accent, fg="white", font=("Arial", 10, "bold"),
                 padx=15, pady=5).pack(side=tk.LEFT, padx=5)
        
        # Sessions list
        list_frame = tk.LabelFrame(content, text="📋 Sesiunile Mele",
                                   bg=self.bg_secondary, fg=self.text,
                                   font=("Arial", 12, "bold"))
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        try:
            sessions_data = self.api.list_sessions()
            logger.debug(f"Sessions API response: {sessions_data}")
            
            # Handle response format - could be list or dict with 'sessions' key
            if isinstance(sessions_data, dict):
                sessions = sessions_data.get('sessions', sessions_data.get('items', []))
            else:
                sessions = sessions_data
            
            logger.info(f"Loaded {len(sessions)} sessions")
            
            if not sessions:
                tk.Label(list_frame, text="Nu ai sesiuni create încă.\nCreează una nouă pentru a începe!",
                        bg=self.bg_secondary, fg=self.warning,
                        font=("Arial", 12)).pack(pady=50)
            else:
                # Table
                tree_frame = tk.Frame(list_frame, bg=self.bg_secondary)
                tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                
                scrollbar = ttk.Scrollbar(tree_frame)
                scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                
                tree = ttk.Treeview(tree_frame, columns=("ID", "Status", "Jocuri", "Dificultate", "Creat"),
                                   show="headings", yscrollcommand=scrollbar.set, height=15)
                tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                scrollbar.config(command=tree.yview)
                
                tree.heading("ID", text="Session ID")
                tree.heading("Status", text="Status")
                tree.heading("Jocuri", text="Jocuri")
                tree.heading("Dificultate", text="Dificultate")
                tree.heading("Creat", text="Creat La")
                
                tree.column("ID", width=100)
                tree.column("Status", width=120)
                tree.column("Jocuri", width=100)
                tree.column("Dificultate", width=100)
                tree.column("Creat", width=200)
                
                for s in sessions:
                    status_emoji = "✅" if s['status'] == "COMPLETED" else "🎮"
                    status_text = s.get('status', 'UNKNOWN')
                    games_info = f"{s.get('games_created', 0)}/{s.get('num_games', '?')}"
                    difficulty = s.get('difficulty', 'N/A')
                    created = s.get('created_at', 'N/A')[:19]
                    
                    tree.insert("", tk.END, values=(
                        s['session_id'],
                        f"{status_emoji} {status_text}",
                        games_info,
                        difficulty,
                        created
                    ))
                
                def on_select(event):
                    selected = tree.selection()
                    if selected:
                        item = tree.item(selected[0])
                        session_id = item['values'][0]
                        self.show_session_details(session_id)
                
                def on_double_click(event):
                    """Double-click pentru a continua sesiunea direct."""
                    selected = tree.selection()
                    if selected:
                        item = tree.item(selected[0])
                        session_id = item['values'][0]
                        status = item['values'][1]
                        
                        # Continue session if active (ACTIVE is the API status, not IN_PROGRESS)
                        if "ACTIVE" in status or "IN_PROGRESS" in status or "🎮" in status:
                            logger.info(f"Continuing session: {session_id}")
                            try:
                                # Get full session data from API
                                session = self.api.get_session(session_id)
                                logger.debug(f"Loaded session data: {session}")
                                
                                # Ensure params exist (difficulty is in params)
                                if 'params' not in session:
                                    session['params'] = {}
                                if not session['params'].get('difficulty'):
                                    session['params']['difficulty'] = 'MEDIUM'  # Default fallback
                                
                                self.current_session = session
                                self.show_game_page()
                                self.show_notification(f"Continui sesiunea {session_id}", "info", duration=2000)
                            except Exception as e:
                                logger.error(f"Failed to load session: {e}", exc_info=True)
                                self.show_notification(f"Eroare: {str(e)}", "error", duration=4000)
                        else:
                            self.show_session_details(session_id)
                
                tree.bind('<<TreeviewSelect>>', on_select)
                tree.bind('<Double-Button-1>', on_double_click)
                
                # Info label
                tk.Label(list_frame, text="💡 Tip: Dublu-click pe o sesiune IN_PROGRESS pentru a continua",
                        bg=self.bg_secondary, fg=self.warning,
                        font=("Arial", 9, "italic")).pack(pady=5)
                
        except Exception as e:
            tk.Label(list_frame, text=f"Eroare încărcare sesiuni:\n{str(e)}",
                    bg=self.bg_secondary, fg=self.highlight,
                    font=("Arial", 10)).pack(pady=20)
    
    def show_session_details(self, session_id):
        """Dialog cu detalii sesiune."""
        try:
            session = self.api.get_session(session_id)
            games = self.api.list_session_games(session_id)
            stats = self.api.get_session_stats(session_id)
            
            dialog = tk.Toplevel(self.root)
            dialog.title(f"Sesiune: {session_id}")
            dialog.geometry("600x500")
            dialog.configure(bg=self.bg_secondary)
            
            text = scrolledtext.ScrolledText(dialog, bg=self.bg_primary, fg=self.text,
                                            font=("Consolas", 10), wrap=tk.WORD)
            text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            text.insert(tk.END, f"╔{'='*58}╗\n")
            text.insert(tk.END, f"║  SESIUNE: {session_id:<43} ║\n")
            text.insert(tk.END, f"╚{'='*58}╝\n\n")
            
            # Extract params safely
            params = session.get('params', {})
            difficulty = params.get('difficulty', 'N/A')
            max_misses = params.get('max_misses', 'N/A')
            
            text.insert(tk.END, f"Status: {session['status']}\n")
            text.insert(tk.END, f"Dificultate: {difficulty}\n")
            text.insert(tk.END, f"Jocuri: {session['games_created']}/{session['num_games']}\n")
            text.insert(tk.END, f"Greșeli maxime: {max_misses}\n\n")
            
            text.insert(tk.END, "STATISTICI:\n")
            text.insert(tk.END, f"  Win Rate: {stats['win_rate']}%\n")
            text.insert(tk.END, f"  Ghiciri medii: {stats['avg_total_guesses']:.1f}\n")
            text.insert(tk.END, f"  Scor compozit: {stats.get('composite_score', 0):.2f}\n\n")
            
            text.insert(tk.END, f"JOCURI ({len(games.get('games', []))}):\n")
            text.insert(tk.END, "-"*60 + "\n")
            
            for g in games.get('games', []):
                status_emoji = "✅" if g['status'] == "WON" else "❌" if g['status'] == "LOST" else "⏸️"
                text.insert(tk.END, f"\n{status_emoji} {g['game_id']} - {g['status']}\n")
                text.insert(tk.END, f"  Pattern: {g.get('pattern', 'N/A')}\n")
                if g.get('composite_score'):
                    text.insert(tk.END, f"  Scor: {g['composite_score']:.2f}\n")
            
            text.config(state=tk.DISABLED)
            
            # Buttons
            btn_frame = tk.Frame(dialog, bg=self.bg_secondary)
            btn_frame.pack(fill=tk.X, padx=10, pady=10)
            
            # Show play button for ACTIVE sessions (ACTIVE is the correct status from API)
            if session['status'] in ['ACTIVE', 'IN_PROGRESS']:
                tk.Button(btn_frame, text="🎲 Joacă în această sesiune",
                         command=lambda: (setattr(self, 'current_session', session), dialog.destroy(), self.show_game_page()),
                         bg=self.success, fg="white", font=("Arial", 11, "bold"),
                         pady=8).pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
            
            # Close button
            tk.Button(btn_frame, text="✖ Închide",
                     command=dialog.destroy,
                     bg=self.accent, fg="white", font=("Arial", 10),
                     pady=6).pack(side=tk.LEFT, padx=5)
        except Exception as e:
            messagebox.showerror("Eroare", str(e))
    
    # ============= GAME PAGE =============
    def show_game_page(self):
        """Pagina principală de joc - Workflow complet."""
        logger.log_navigation("PREVIOUS", "GAME")
        self.clear_window()
        self.create_header("🎲 Joc", "Ghicește cuvântul secret!")
        self.create_menu_bar()
        
        content = tk.Frame(self.root, bg=self.bg_primary)
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Verificare sesiune activă
        if not self.current_session:
            tk.Label(content, text="⚠️ Nu ai o sesiune activă!",
                    bg=self.bg_primary, fg=self.warning,
                    font=("Arial", 16, "bold")).pack(pady=(50, 20))
            tk.Label(content, text="Mergi la Sesiuni pentru a crea o sesiune nouă\nsau alege una existentă.",
                    bg=self.bg_primary, fg=self.text,
                    font=("Arial", 12)).pack(pady=10)
            
            btn_frame = tk.Frame(content, bg=self.bg_primary)
            btn_frame.pack(pady=20)
            tk.Button(btn_frame, text="➕ Creează Sesiune Nouă", command=self.show_create_session_page,
                     bg=self.success, fg="white", font=("Arial", 12, "bold"),
                     padx=30, pady=10).pack(side=tk.LEFT, padx=10)
            tk.Button(btn_frame, text="📋 Vezi Sesiuni", command=self.show_sessions_page,
                     bg=self.accent, fg="white", font=("Arial", 11),
                     padx=30, pady=10).pack(side=tk.LEFT, padx=10)
            return
        
        session_id = self.current_session['session_id']
        
        # Info sesiune
        info_frame = tk.LabelFrame(content, text="📋 Sesiune Activă",
                                   bg=self.bg_secondary, fg=self.text,
                                   font=("Arial", 11, "bold"))
        info_frame.pack(fill=tk.X, pady=(0, 20))
        
        info = tk.Frame(info_frame, bg=self.bg_secondary)
        info.pack(padx=15, pady=10)
        
        # Safe field access with fallbacks
        session_id_display = self.current_session.get('session_id', session_id)
        # Difficulty is inside 'params' object
        params = self.current_session.get('params', {})
        difficulty = params.get('difficulty', 'N/A')
        games_created = self.current_session.get('games_created', 0)
        num_games = self.current_session.get('num_games', '?')
        
        tk.Label(info, text=f"🎯 ID: {session_id_display} | Dificultate: {difficulty} | "
                           f"Jocuri: {games_created}/{num_games}",
                bg=self.bg_secondary, fg=self.warning,
                font=("Arial", 10, "bold")).pack()
        
        # Game area
        game_frame = tk.LabelFrame(content, text="🎮 Control Joc",
                                   bg=self.bg_secondary, fg=self.text,
                                   font=("Arial", 12, "bold"))
        game_frame.pack(fill=tk.BOTH, expand=True)
        
        game_content = tk.Frame(game_frame, bg=self.bg_secondary)
        game_content.pack(padx=20, pady=20, fill=tk.BOTH, expand=True)
        
        # Check if there's a current game or need to create one
        if not hasattr(self, 'current_game') or not self.current_game:
            self.show_create_game_interface(game_content, session_id)
        else:
            self.show_active_game_interface(game_content, session_id)
    
    def show_create_game_interface(self, parent, session_id):
        """Interfață pentru crearea unui joc nou în sesiune."""
        tk.Label(parent, text="🎲 Pregătit pentru un joc nou?",
                bg=self.bg_secondary, fg=self.text,
                font=("Arial", 16, "bold")).pack(pady=(50, 20))
        
        tk.Label(parent, text="Click butonul de mai jos pentru a crea un joc nou în această sesiune.\n"
                             "Fiecare joc va avea un cuvânt random bazat pe dificultatea aleasă.",
                bg=self.bg_secondary, fg=self.warning,
                font=("Arial", 11)).pack(pady=10)
        
        def create_and_start_game():
            logger.log_user_action("CREATE_GAME", f"session={session_id}")
            
            # Show loading spinner
            self.show_loading("Se creează jocul...")
            
            def create_task():
                try:
                    game = self.api.create_game(session_id)
                    self.current_game = game
                    logger.info(f"✅ Game created: {game['game_id']}")
                    
                    # Refresh session info
                    self.current_session = self.api.get_session(session_id)
                    
                    # Update UI in main thread
                    def on_success():
                        self.hide_loading()
                        self.show_notification(f"🎲 Joc creat: {game['game_id']} | {game['pattern']}", "success", duration=2000)
                        self.root.after(100, self.show_game_page)
                    
                    self.root.after(0, on_success)
                except Exception as e:
                    logger.log_exception(e, "create_game")
                    def on_error():
                        self.hide_loading()
                        self.show_notification(f"Eroare: {str(e)}", "error", duration=3000)
                    self.root.after(0, on_error)
            
            threading.Thread(target=create_task, daemon=True).start()
        
        btn_frame = tk.Frame(parent, bg=self.bg_secondary)
        btn_frame.pack(pady=30)
        
        tk.Button(btn_frame, text="🎲 Creează Joc Nou", command=create_and_start_game,
                 bg=self.success, fg="white", font=("Arial", 14, "bold"),
                 padx=40, pady=15).pack(side=tk.LEFT, padx=10)
        
        tk.Button(btn_frame, text="📊 Vezi Statistici Sesiune",
                 command=lambda: self.show_session_stats_dialog(session_id),
                 bg=self.accent, fg="white", font=("Arial", 11),
                 padx=20, pady=10).pack(side=tk.LEFT, padx=10)
        
        tk.Button(btn_frame, text="❌ Abandonează Sesiune",
                 command=lambda: self.abort_current_session(),
                 bg=self.highlight, fg="white", font=("Arial", 10),
                 padx=15, pady=8).pack(side=tk.LEFT, padx=10)
    
    def show_active_game_interface(self, parent, session_id):
        """Interfață pentru jocul activ - ghicire litere/cuvinte."""
        game_id = self.current_game['game_id']
        
        try:
            # Get current game state
            state = self.api.get_game_state(session_id, game_id)
            
            # Pattern display (cuvântul cu litere ascunse) - Store reference
            pattern_frame = tk.Frame(parent, bg=self.bg_primary, relief=tk.RIDGE, bd=3)
            pattern_frame.pack(pady=20)
            
            pattern = state.get('pattern', '_ _ _ _ _')
            self.pattern_label = tk.Label(pattern_frame, text=pattern, 
                    bg=self.bg_primary, fg=self.success,
                    font=("Courier New", 36, "bold"))
            self.pattern_label.pack(padx=30, pady=20)
            
            # Game info - Store references for independent updates
            info_grid = tk.Frame(parent, bg=self.bg_secondary)
            info_grid.pack(pady=20)
            
            # Safe access to state fields with fallbacks
            # API returns: guessed_letters = ALL guessed (correct + wrong), wrong_letters = only incorrect
            all_guessed = state.get('guessed_letters', [])     # TOATE literele încercate
            wrong_letters = state.get('wrong_letters', [])      # Doar literele GREȘITE
            max_misses = state.get('max_misses', 6)
            
            # Calculate CORRECT letters = all_guessed - wrong_letters
            correct_letters = [letter for letter in all_guessed if letter not in wrong_letters]
            
            # DEBUG: Log what API returns
            logger.debug(f"API State - All: {all_guessed}, Wrong: {wrong_letters}, Correct: {correct_letters}")
            
            # Store label references for live updates
            self.mistakes_label = tk.Label(info_grid, text=f"❌ Greșeli: {len(wrong_letters)}/{max_misses}",
                    bg=self.bg_secondary, fg=self.highlight,
                    font=("Arial", 12, "bold"))
            self.mistakes_label.grid(row=0, column=0, padx=20)
            
            self.correct_label = tk.Label(info_grid, text=f"✅ Litere corecte: {', '.join(correct_letters) or 'niciunǎ'}",
                    bg=self.bg_secondary, fg=self.success,
                    font=("Arial", 12))
            self.correct_label.grid(row=0, column=1, padx=20)
            
            self.wrong_label = tk.Label(info_grid, text=f"❗ Litere greșite: {', '.join(wrong_letters) or 'niciunǎ'}",
                    bg=self.bg_secondary, fg=self.warning,
                    font=("Arial", 12))
            self.wrong_label.grid(row=0, column=2, padx=20)
            
            # Check if game ended
            game_status = state.get('status', 'IN_PROGRESS')
            if game_status in ['WON', 'LOST']:
                result_text = "🎉 AI CÂȘTIGAT!" if game_status == 'WON' else "💔 AI PIERDUT!"
                result_color = self.success if game_status == 'WON' else self.highlight
                
                tk.Label(parent, text=result_text,
                        bg=self.bg_secondary, fg=result_color,
                        font=("Arial", 24, "bold")).pack(pady=20)
                
                if game_status == 'LOST':
                    tk.Label(parent, text=f"Cuvântul era: {state.get('word', '???')}",
                            bg=self.bg_secondary, fg=self.text,
                            font=("Arial", 16)).pack(pady=10)
                
                total_guesses = state.get('total_guesses', 0)
                tk.Label(parent, text=f"Scor: {state.get('composite_score', 0):.2f} | "
                                     f"Timp: {state.get('time_seconds', 0)}s | "
                                     f"Ghiciri: {total_guesses}",
                        bg=self.bg_secondary, fg=self.warning,
                        font=("Arial", 11)).pack(pady=10)
                
                # Next game button
                btn_frame = tk.Frame(parent, bg=self.bg_secondary)
                btn_frame.pack(pady=20)
                
                if self.current_session['games_created'] < self.current_session['num_games']:
                    tk.Button(btn_frame, text="🎲 Joc Următor", 
                             command=lambda: (setattr(self, 'current_game', None), self.show_game_page()),
                             bg=self.success, fg="white", font=("Arial", 13, "bold"),
                             padx=30, pady=12).pack(side=tk.LEFT, padx=10)
                else:
                    tk.Label(parent, text="✅ Toate jocurile din sesiune au fost create!",
                            bg=self.bg_secondary, fg=self.success,
                            font=("Arial", 12, "bold")).pack(pady=10)
                
                tk.Button(btn_frame, text="📊 Statistici Sesiune",
                         command=lambda: self.show_session_stats_dialog(session_id),
                         bg=self.accent, fg="white", font=("Arial", 11),
                         padx=20, pady=10).pack(side=tk.LEFT, padx=10)
                
                tk.Button(btn_frame, text="📋 Vezi Toate Sesiunile",
                         command=self.show_sessions_page,
                         bg=self.accent, fg="white", font=("Arial", 10),
                         padx=15, pady=8).pack(side=tk.LEFT, padx=10)
                
                return
            
            # Guess interface (for active games)
            guess_frame = tk.LabelFrame(parent, text="💭 Ghicește",
                                        bg=self.bg_secondary, fg=self.text,
                                        font=("Arial", 11, "bold"))
            guess_frame.pack(fill=tk.X, pady=20, padx=50)
            
            guess_content = tk.Frame(guess_frame, bg=self.bg_secondary)
            guess_content.pack(padx=20, pady=15)
            
            tk.Label(guess_content, text="Introdu o literă sau cuvântul complet:",
                    bg=self.bg_secondary, fg=self.text,
                    font=("Arial", 11)).pack(pady=(0, 10))
            
            guess_entry = tk.Entry(guess_content, font=("Arial", 14), width=20, justify=tk.CENTER)
            guess_entry.pack(pady=5)
            guess_entry.focus()
            
            def make_guess():
                guess = guess_entry.get().strip().lower()
                if not guess:
                    self.show_notification("Introdu o literă sau un cuvânt!", "warning", duration=1500)
                    return
                
                logger.log_user_action("GUESS", f"game={game_id}, guess={guess}")
                
                # Clear entry and disable during request
                guess_entry.delete(0, tk.END)
                guess_entry.config(state='disabled')
                
                try:
                    result = self.api.make_guess(session_id, game_id, guess)
                    logger.info(f"✅ Guess result: correct={result.get('correct')}, status={result.get('status')}")
                    
                    # Show notification FIRST
                    if result.get('correct'):
                        self.show_notification(f"✅ Corect! '{guess}'", "success", duration=1500)
                    else:
                        self.show_notification(f"❌ Greșit! '{guess}'", "error", duration=1500)
                    
                    # Update only game state components (NO full refresh!)
                    def update_game_state():
                        try:
                            new_state = self.api.get_game_state(session_id, game_id)
                            
                            # Update pattern label
                            if hasattr(self, 'pattern_label') and self.pattern_label.winfo_exists():
                                self.pattern_label.config(text=new_state.get('pattern', ''))
                            
                            # Update stats labels
                            all_guessed = new_state.get('guessed_letters', [])
                            wrong_letters = new_state.get('wrong_letters', [])
                            correct_letters = [l for l in all_guessed if l not in wrong_letters]
                            max_misses = new_state.get('max_misses', 6)
                            
                            if hasattr(self, 'mistakes_label') and self.mistakes_label.winfo_exists():
                                self.mistakes_label.config(text=f"❌ Greșeli: {len(wrong_letters)}/{max_misses}")
                            
                            if hasattr(self, 'correct_label') and self.correct_label.winfo_exists():
                                self.correct_label.config(text=f"✅ Litere corecte: {', '.join(correct_letters) or 'niciunǎ'}")
                            
                            if hasattr(self, 'wrong_label') and self.wrong_label.winfo_exists():
                                self.wrong_label.config(text=f"❗ Litere greșite: {', '.join(wrong_letters) or 'niciunǎ'}")
                            
                            # Check if game ended
                            game_status = new_state.get('status', 'IN_PROGRESS')
                            if game_status in ['WON', 'LOST']:
                                # Game ended - full refresh needed
                                self.show_game_page()
                            else:
                                # Re-enable entry and focus
                                guess_entry.config(state='normal')
                                guess_entry.focus()
                        except Exception as e:
                            logger.error(f"Update state error: {e}")
                            guess_entry.config(state='normal')
                            guess_entry.focus()
                    
                    # Update after small delay
                    self.root.after(200, update_game_state)
                    
                except Exception as e:
                    logger.log_exception(e, "make_guess")
                    self.show_notification(f"Eroare: {str(e)}", "error", duration=2000)
                    guess_entry.config(state='normal')
                    guess_entry.focus()
            
            def on_enter(event):
                make_guess()
            
            guess_entry.bind('<Return>', on_enter)
            
            # Function for refresh button - update without full redraw
            def refresh_game_state():
                """Refresh doar state-ul jocului, nu toată pagina."""
                try:
                    new_state = self.api.get_game_state(session_id, game_id)
                    
                    # Update pattern
                    if hasattr(self, 'pattern_label') and self.pattern_label.winfo_exists():
                        self.pattern_label.config(text=new_state.get('pattern', ''))
                    
                    # Update stats
                    all_guessed = new_state.get('guessed_letters', [])
                    wrong_letters = new_state.get('wrong_letters', [])
                    correct_letters = [l for l in all_guessed if l not in wrong_letters]
                    max_misses = new_state.get('max_misses', 6)
                    
                    if hasattr(self, 'mistakes_label') and self.mistakes_label.winfo_exists():
                        self.mistakes_label.config(text=f"❌ Greșeli: {len(wrong_letters)}/{max_misses}")
                    
                    if hasattr(self, 'correct_label') and self.correct_label.winfo_exists():
                        self.correct_label.config(text=f"✅ Litere corecte: {', '.join(correct_letters) or 'niciunǎ'}")
                    
                    if hasattr(self, 'wrong_label') and self.wrong_label.winfo_exists():
                        self.wrong_label.config(text=f"❗ Litere greșite: {', '.join(wrong_letters) or 'niciunǎ'}")
                    
                    # Check if game ended
                    if new_state.get('status') in ['WON', 'LOST']:
                        self.show_game_page()  # Full refresh only if game ended
                    else:
                        self.show_notification("🔄 Actualizat!", "info", duration=1000)
                        
                except Exception as e:
                    logger.error(f"Refresh error: {e}")
                    self.show_notification(f"Eroare: {str(e)}", "error", duration=2000)
            
            # Function for abort button - smooth transition
            def abort_game():
                """Abandonează jocul cu confirmare rapidă."""
                if messagebox.askyesno("Abandonare", "Sigur vrei să abandonezi jocul curent?"):
                    try:
                        self.api.abort_game(session_id, game_id)
                        logger.info(f"Game aborted: {game_id}")
                        self.show_notification("Joc abandonat", "info", duration=2000)
                        # Refresh to show next game or session stats
                        self.root.after(500, self.show_game_page)
                    except Exception as e:
                        logger.error(f"Abort error: {e}")
                        self.show_notification(f"Eroare: {str(e)}", "error", duration=2000)
            
            btn_guess_frame = tk.Frame(guess_content, bg=self.bg_secondary)
            btn_guess_frame.pack(pady=10)
            
            tk.Button(btn_guess_frame, text="✅ Trimite Ghicire", command=make_guess,
                     bg=self.success, fg="white", font=("Arial", 12, "bold"),
                     padx=25, pady=8).pack(side=tk.LEFT, padx=10)
            
            tk.Button(btn_guess_frame, text="🔄 Reîmprospătează", command=refresh_game_state,
                     bg=self.accent, fg="white", font=("Arial", 10),
                     padx=15, pady=6).pack(side=tk.LEFT, padx=10)
            
            tk.Button(btn_guess_frame, text="🚫 Abandonează Joc", command=abort_game,
                     bg=self.highlight, fg="white", font=("Arial", 10),
                     padx=15, pady=6).pack(side=tk.LEFT, padx=10)
            
        except Exception as e:
            logger.log_exception(e, "show_active_game")
            tk.Label(parent, text=f"❌ Eroare la încărcarea jocului:\n{str(e)}",
                    bg=self.bg_secondary, fg=self.highlight,
                    font=("Arial", 12)).pack(pady=50)
    
    def show_session_stats_dialog(self, session_id):
        """Dialog cu statistici sesiune."""
        try:
            stats = self.api.get_session_stats(session_id)
            games = self.api.list_session_games(session_id)
            
            dialog = tk.Toplevel(self.root)
            dialog.title(f"📊 Statistici Sesiune")
            dialog.geometry("700x600")
            dialog.configure(bg=self.bg_secondary)
            
            # Title
            tk.Label(dialog, text=f"📊 Statistici pentru {session_id}",
                    bg=self.bg_secondary, fg=self.text,
                    font=("Arial", 14, "bold")).pack(pady=10)
            
            # Stats display
            stats_frame = tk.LabelFrame(dialog, text="Rezultate Generale",
                                        bg=self.bg_primary, fg=self.text,
                                        font=("Arial", 11, "bold"))
            stats_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
            
            text = scrolledtext.ScrolledText(stats_frame, bg=self.bg_primary, fg=self.text,
                                            font=("Consolas", 10), wrap=tk.WORD, height=20)
            text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            text.insert(tk.END, "="*60 + "\n")
            text.insert(tk.END, "STATISTICI SESIUNE\n")
            text.insert(tk.END, "="*60 + "\n\n")
            
            text.insert(tk.END, f"Jocuri Total: {stats['games_total']}\n")
            text.insert(tk.END, f"Jocuri Finalizate: {stats['games_finished']}\n")
            text.insert(tk.END, f"Jocuri Câștigate: {stats['games_won']} ✅\n")
            text.insert(tk.END, f"Jocuri Pierdute: {stats['games_lost']} ❌\n")
            text.insert(tk.END, f"Jocuri Abandonate: {stats['games_aborted']} 🚫\n\n")
            
            text.insert(tk.END, f"Win Rate: {stats['win_rate']:.1f}%\n")
            text.insert(tk.END, f"Ghiciri Medii: {stats['avg_total_guesses']:.1f}\n")
            text.insert(tk.END, f"Litere Greșite Medii: {stats['avg_wrong_letters']:.1f}\n")
            text.insert(tk.END, f"Timp Mediu: {stats['avg_time_sec']:.1f}s\n")
            text.insert(tk.END, f"Scor Compozit: {stats['composite_score']:.2f}\n\n")
            
            text.insert(tk.END, "="*60 + "\n")
            text.insert(tk.END, "ISTORIC JOCURI\n")
            text.insert(tk.END, "="*60 + "\n\n")
            
            for g in games.get('games', []):
                status_emoji = {"WON": "✅", "LOST": "❌", "ABORTED": "🚫", "IN_PROGRESS": "⏳"}.get(g['status'], "❓")
                text.insert(tk.END, f"{status_emoji} {g['game_id']}\n")
                text.insert(tk.END, f"   Pattern: {g.get('pattern', 'N/A')}\n")
                text.insert(tk.END, f"   Status: {g['status']}\n")
                if g.get('composite_score'):
                    text.insert(tk.END, f"   Scor: {g['composite_score']:.2f}\n")
                text.insert(tk.END, "\n")
            
            text.config(state=tk.DISABLED)
            
            tk.Button(dialog, text="✅ Închide", command=dialog.destroy,
                     bg=self.accent, fg="white", font=("Arial", 11),
                     padx=30, pady=8).pack(pady=10)
            
        except Exception as e:
            messagebox.showerror("Eroare", f"Nu am putut încărca statisticile:\n{str(e)}")
    
    def abort_current_session(self):
        """Abandonează sesiunea curentă."""
        if not self.current_session:
            return
        
        session_id = self.current_session['session_id']
        
        if not messagebox.askyesno("Confirmare", 
                                   f"Sigur vrei să abandonezi sesiunea {session_id}?\n"
                                   "Toate jocurile în progres vor fi abandonate."):
            return
        
        logger.log_user_action("ABORT_SESSION", session_id)
        try:
            self.api.abort_session(session_id)
            logger.info(f"✅ Session aborted: {session_id}")
            
            self.current_session = None
            self.current_game = None
            
            self.show_sessions_page()
            self.show_notification("Sesiunea a fost abandonată.", "info")
        except Exception as e:
            logger.log_exception(e, "abort_session")
            self.show_notification(f"Nu am putut abandona sesiunea: {str(e)}", "error", duration=4000)
    
    def abort_current_game(self, session_id, game_id):
        """Abandonează jocul curent."""
        # Confirmarea o fac direct (fără dialog)
        logger.log_user_action("ABORT_GAME", f"session={session_id}, game={game_id}")
        try:
            self.api.abort_game(session_id, game_id)
            logger.info(f"✅ Game aborted: {game_id}")
            
            self.current_game = None
            self.show_game_page()
            self.show_notification("Jocul a fost abandonat.", "info")
        except Exception as e:
            logger.log_exception(e, "abort_game")
            self.show_notification(f"Nu am putut abandona jocul: {str(e)}", "error", duration=4000)
    
    # ============= STATS PAGE =============
    def show_stats_page(self):
        """Pagina de statistici."""
        self.clear_window()
        self.create_header("📊 Statistici", "Performanțele tale")
        self.create_menu_bar()
        
        content = tk.Frame(self.root, bg=self.bg_primary)
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        try:
            stats = self.api.get_user_stats(self.api.user_id)
            
            text = scrolledtext.ScrolledText(content, bg=self.bg_primary, fg=self.text,
                                            font=("Consolas", 11), wrap=tk.WORD)
            text.pack(fill=tk.BOTH, expand=True)
            
            text.insert(tk.END, json.dumps(stats, indent=2))
            text.config(state=tk.DISABLED)
        except Exception as e:
            tk.Label(content, text=f"Eroare:\n{str(e)}",
                    bg=self.bg_primary, fg=self.highlight).pack(expand=True)
    
    # ============= LEADERBOARD PAGE =============
    def show_leaderboard_page(self):
        """Pagina cu leaderboard."""
        self.clear_window()
        self.create_header("🏆 Leaderboard", "Cei mai buni jucători")
        self.create_menu_bar()
        
        content = tk.Frame(self.root, bg=self.bg_primary)
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        try:
            result = self.api.get_leaderboard()
            
            for i, entry in enumerate(result.get("leaderboard", []), 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                
                frame = tk.Frame(content, bg=self.accent, relief=tk.RAISED, bd=2)
                frame.pack(fill=tk.X, pady=5, padx=10)
                
                tk.Label(frame, text=f"{medal} {entry['nickname']}",
                        bg=self.accent, fg=self.text,
                        font=("Arial", 12, "bold")).pack(side=tk.LEFT, padx=10, pady=5)
                
                info = f"Scor: {entry.get('avg_composite_score', 0):.2f} | Win: {entry['win_rate']*100:.1f}% | Jocuri: {entry['total_games']}"
                tk.Label(frame, text=info,
                        bg=self.accent, fg=self.text,
                        font=("Arial", 10)).pack(side=tk.RIGHT, padx=10, pady=5)
        except Exception as e:
            tk.Label(content, text=f"Eroare:\n{str(e)}",
                    bg=self.bg_primary, fg=self.highlight).pack(expand=True)
    
    # ============= SETTINGS PAGE =============
    def show_settings_page(self):
        """Pagina de setări."""
        logger.log_navigation("PREVIOUS", "SETTINGS")
        self.clear_window()
        self.create_header("⚙️ Setări", "Configurează aplicația")
        self.create_menu_bar()
        
        content = tk.Frame(self.root, bg=self.bg_primary)
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Log viewer
        log_frame = tk.LabelFrame(content, text="📝 Log Viewer - Ultimele 100 linii",
                                  bg=self.bg_secondary, fg=self.text,
                                  font=("Arial", 12, "bold"))
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Buttons
        btn_frame = tk.Frame(log_frame, bg=self.bg_secondary)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Button(btn_frame, text="🔄 Reîmprospătează Log",
                 command=lambda: self.refresh_logs(log_text),
                 bg=self.accent, fg="white", font=("Arial", 10, "bold"),
                 padx=15, pady=5).pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_frame, text="📂 Deschide fișier log",
                 command=self.open_log_file,
                 bg=self.highlight, fg="white", font=("Arial", 10, "bold"),
                 padx=15, pady=5).pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_frame, text="🗑️ Șterge console",
                 command=lambda: log_text.delete(1.0, tk.END),
                 bg=self.warning, fg="white", font=("Arial", 10, "bold"),
                 padx=15, pady=5).pack(side=tk.LEFT, padx=5)
        
        # Log text area
        log_text = scrolledtext.ScrolledText(log_frame, bg=self.bg_primary, fg=self.text,
                                             font=("Consolas", 9), wrap=tk.WORD, height=25)
        log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Load initial logs
        self.refresh_logs(log_text)
        
        # Account Management Section
        account_frame = tk.LabelFrame(content, text="👤 Gestionare Cont",
                                      bg=self.bg_secondary, fg=self.text,
                                      font=("Arial", 12, "bold"))
        account_frame.pack(fill=tk.X, pady=(0, 10))
        
        account_content = tk.Frame(account_frame, bg=self.bg_secondary)
        account_content.pack(padx=20, pady=15)
        
        tk.Label(account_content, text=f"📧 Email: {self.api.email}",
                bg=self.bg_secondary, fg=self.text,
                font=("Arial", 11)).pack(anchor=tk.W, pady=5)
        
        tk.Label(account_content, text=f"🆔 User ID: {self.api.user_id}",
                bg=self.bg_secondary, fg=self.text,
                font=("Arial", 11)).pack(anchor=tk.W, pady=5)
        
        # Delete Account Button
        delete_frame = tk.Frame(account_content, bg="#e74c3c", relief=tk.RAISED, bd=2)
        delete_frame.pack(pady=(15, 5), fill=tk.X)
        
        tk.Button(delete_frame, text="🗑️ ȘTERGE CONT PERMANENT",
                 command=self.delete_account_confirmation,
                 bg="#e74c3c", fg="white", font=("Arial", 11, "bold"),
                 relief=tk.FLAT, cursor="hand2",
                 activebackground="#c0392b",
                 padx=20, pady=10).pack(fill=tk.X)
        
        tk.Label(account_content, text="⚠️ ATENȚIE: Această acțiune este IREVERSIBILĂ!\nToate sesiunile, jocurile și statisticile tale vor fi șterse definitiv.",
                bg=self.bg_secondary, fg=self.warning,
                font=("Arial", 9, "italic"),
                justify=tk.LEFT).pack(pady=5)
        
        # Info
        info_frame = tk.Frame(content, bg=self.bg_secondary, relief=tk.RAISED, bd=2)
        info_frame.pack(fill=tk.X)
        
        log_path = logger.get_log_file_path()
        tk.Label(info_frame, text=f"📁 Fișier log: {log_path}",
                bg=self.bg_secondary, fg=self.success,
                font=("Arial", 9)).pack(padx=10, pady=5)
    
    def refresh_logs(self, text_widget):
        """Reîmprospătează conținutul log-urilor."""
        logger.log_user_action("REFRESH_LOGS")
        try:
            logs = logger.get_recent_logs(100)
            text_widget.delete(1.0, tk.END)
            text_widget.insert(tk.END, "".join(logs))
            text_widget.see(tk.END)  # Scroll la final
            logger.debug("Logs refreshed successfully")
        except Exception as e:
            logger.log_exception(e, "refresh_logs")
            text_widget.insert(tk.END, f"\n❌ Eroare citire log: {e}\n")
    
    def open_log_file(self):
        """Deschide fișierul de log în editor extern."""
        logger.log_user_action("OPEN_LOG_FILE")
        try:
            log_path = logger.get_log_file_path()
            if sys.platform == "win32":
                os.startfile(log_path)
            elif sys.platform == "darwin":  # macOS
                subprocess.Popen(["open", log_path])
            else:  # Linux
                subprocess.Popen(["xdg-open", log_path])
            logger.info(f"Opened log file: {log_path}")
        except Exception as e:
            logger.log_exception(e, "open_log_file")
            messagebox.showerror("Eroare", f"Nu pot deschide fișierul:\n{e}")
    
    def delete_account_confirmation(self):
        """Confirmă și șterge contul utilizatorului."""
        logger.log_user_action("DELETE_ACCOUNT_ATTEMPT", f"user={self.api.user_id}")
        
        # Double confirmation
        first_confirm = messagebox.askyesno(
            "⚠️ ATENȚIE - Ștergere Cont",
            f"Ești SIGUR că vrei să ștergi contul?\n\n"
            f"📧 Email: {self.api.email}\n"
            f"🆔 User ID: {self.api.user_id}\n\n"
            f"⚠️ Această acțiune va șterge DEFINITIV:\n"
            f"  • Toate sesiunile tale\n"
            f"  • Toate jocurile tale\n"
            f"  • Toate statisticile tale\n"
            f"  • Datele contului tău\n\n"
            f"❌ ACȚIUNE IREVERSIBILĂ!",
            icon='warning'
        )
        
        if not first_confirm:
            logger.debug("Account deletion cancelled by user (first prompt)")
            return
        
        # Second confirmation with text input
        import tkinter.simpledialog as simpledialog
        confirmation_text = simpledialog.askstring(
            "Confirmare Finală",
            f"Pentru a confirma ștergerea, tastează:\nDELETE\n\n(cu majuscule)",
            parent=self.root
        )
        
        if confirmation_text != "DELETE":
            logger.debug(f"Account deletion cancelled - wrong confirmation text: {confirmation_text}")
            self.show_notification("Ștergerea contului a fost anulată. Contul tău este în siguranță.", "info", duration=4000)
            return
        
        # Proceed with deletion
        try:
            logger.info(f"🗑️ Deleting account: {self.api.user_id}")
            self.api.delete_account()
            
            logger.info("✅ Account deleted successfully")
            
            # Clear session and return to login
            self.api.token = None
            self.api.user_id = None
            self.api.email = None
            self.current_session = None
            self.current_game = None
            
            # Return to login page
            self.setup_login_page()
            self.show_notification("Contul tău a fost șters cu succes! Toate datele au fost eliminate. 👋", "success", duration=6000)
            
        except Exception as e:
            logger.log_exception(e, "delete_account")
            error_msg = str(e)
            if "401" in error_msg or "403" in error_msg:
                error_msg = "Sesiune expirată. Loghează-te din nou."
                # Clear session and return to login
                self.api.token = None
                self.api.user_id = None
                self.setup_login_page()
            self.show_notification(f"Nu am putut șterge contul: {error_msg}", "error", duration=5000)

def main():
    root = tk.Tk()
    app = HangmanGUI(root)
    
    def on_closing():
        """Închide aplicația și oprește serverul."""
        logger.log_user_action("APP_CLOSE_ATTEMPT")
        
        # Ask for confirmation only
        if messagebox.askyesno("Închidere", "Sigur vrei să închizi aplicația?"):
            logger.info("🚪 Closing application...")
            
            # Stop server if we started it
            if app.server_process:
                try:
                    print("🛑 Opresc serverul...")
                    logger.log_server_event("STOPPING", f"Terminating PID {app.server_process.pid}")
                    app.server_process.terminate()
                    
                    # Wait max 3 seconds for graceful shutdown
                    try:
                        app.server_process.wait(timeout=3)
                        print("✓ Server oprit")
                        logger.log_server_event("STOPPED", "Server terminated successfully")
                    except subprocess.TimeoutExpired:
                        print("⚠ Server nu s-a oprit, forțez oprirea...")
                        logger.warning("Server didn't stop gracefully, forcing kill")
                        app.server_process.kill()
                        app.server_process.wait()
                        print("✓ Server forțat oprit")
                        logger.log_server_event("KILLED", "Server killed forcefully")
                except Exception as e:
                    logger.error(f"Error stopping server: {e}")
                    print(f"⚠ Eroare la oprire server: {e}")
            
            logger.info("="*80)
            logger.info("👋 Application closed normally")
            logger.info("="*80)
            root.destroy()
        else:
            logger.debug("App close cancelled by user")
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    try:
        logger.info("🎮 Starting main event loop")
        root.mainloop()
    except Exception as e:
        logger.critical("💥 FATAL ERROR in main loop", exc_info=True)
        raise

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical("💥 Application crashed", exc_info=True)
        raise
