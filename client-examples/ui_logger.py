#!/usr/bin/env python3
"""
Logger pentru GUI - salvează toate evenimentele și erorile în fișier.
Util pentru debugging și troubleshooting.
"""
import logging
import os
from datetime import datetime
from pathlib import Path

class UILogger:
    """Logger personalizat pentru interfața GUI."""
    
    def __init__(self, log_dir="logs"):
        """
        Inițializează logger-ul.
        
        Args:
            log_dir: Directorul unde se salvează log-urile
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Nume fișier cu timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"gui_{timestamp}.log"
        
        # Configurare logger
        self.logger = logging.getLogger("HangmanGUI")
        self.logger.setLevel(logging.DEBUG)
        
        # Handler pentru fișier - toate nivelurile
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(funcName)-20s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        
        # Handler pentru consolă - doar INFO și mai sus
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(levelname)s: %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        
        # Adaugă handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # Log inițializare
        self.logger.info("="*80)
        self.logger.info("🚀 GUI Logger inițializat")
        self.logger.info(f"📝 Log file: {self.log_file}")
        self.logger.info("="*80)
    
    def debug(self, message):
        """Log la nivel DEBUG."""
        self.logger.debug(message)
    
    def info(self, message):
        """Log la nivel INFO."""
        self.logger.info(message)
    
    def warning(self, message):
        """Log la nivel WARNING."""
        self.logger.warning(message)
    
    def error(self, message, exc_info=None):
        """Log la nivel ERROR."""
        self.logger.error(message, exc_info=exc_info)
    
    def critical(self, message, exc_info=None):
        """Log la nivel CRITICAL."""
        self.logger.critical(message, exc_info=exc_info)
    
    def log_event(self, event_type, details):
        """
        Logare eveniment cu detalii structurate.
        
        Args:
            event_type: Tip eveniment (ex: "LOGIN", "REGISTER", "API_CALL")
            details: Dicționar cu detalii
        """
        msg = f"[{event_type}] {details}"
        self.logger.info(msg)
    
    def log_api_call(self, method, endpoint, status_code=None, error=None):
        """Logare apel API."""
        if error:
            self.logger.error(f"API {method} {endpoint} - FAILED: {error}")
        else:
            self.logger.info(f"API {method} {endpoint} - Status: {status_code}")
    
    def log_navigation(self, from_page, to_page):
        """Logare navigare între pagini."""
        self.logger.info(f"NAVIGATION: {from_page} → {to_page}")
    
    def log_user_action(self, action, details=""):
        """Logare acțiune utilizator."""
        msg = f"USER_ACTION: {action}"
        if details:
            msg += f" | {details}"
        self.logger.info(msg)
    
    def log_server_event(self, event, details=""):
        """Logare eveniment server."""
        msg = f"SERVER: {event}"
        if details:
            msg += f" | {details}"
        self.logger.info(msg)
    
    def log_exception(self, exception, context=""):
        """Logare excepție completă cu stack trace."""
        msg = f"EXCEPTION in {context}: {str(exception)}"
        self.logger.error(msg, exc_info=True)
    
    def get_log_file_path(self):
        """Returnează path-ul către fișierul de log curent."""
        return str(self.log_file)
    
    def get_recent_logs(self, lines=50):
        """
        Citește ultimele N linii din log.
        
        Args:
            lines: Număr de linii
            
        Returns:
            Lista cu ultimele linii
        """
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                return all_lines[-lines:]
        except Exception as e:
            self.logger.error(f"Nu pot citi log-ul: {e}")
            return []

# Instanță globală
_ui_logger = None

def get_logger():
    """Obține instanța globală a logger-ului."""
    global _ui_logger
    if _ui_logger is None:
        _ui_logger = UILogger()
    return _ui_logger

def init_logger(log_dir="logs"):
    """Inițializează logger-ul cu director custom."""
    global _ui_logger
    _ui_logger = UILogger(log_dir)
    return _ui_logger
