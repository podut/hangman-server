#!/usr/bin/env python3
"""
Teste pentru componentele GUI - verifică inițializarea și funcționalitatea de bază.
NU lansează GUI-ul efectiv, doar testează API wrapper-ul și logica.
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "client-examples"))

def test_api_wrapper_init():
    """Test 1: Inițializare HangmanAPI."""
    print("\n🧩 Test 1: Inițializare HangmanAPI...")
    
    try:
        from gui_client_pro import HangmanAPI
        
        api = HangmanAPI()
        assert api.base_url == "http://localhost:8000/api/v1"
        assert api.token is None
        assert api.user_id is None
        
        print("  ✅ HangmanAPI inițializat corect")
        return True
    except Exception as e:
        print(f"  ❌ Eroare: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_wrapper_methods():
    """Test 2: Verifică că toate metodele API există."""
    print("\n🔧 Test 2: Verifică metode API...")
    
    try:
        from gui_client_pro import HangmanAPI
        
        api = HangmanAPI()
        
        required_methods = [
            'register', 'login', 'delete_account',
            'create_session', 'list_sessions', 'get_session', 'abort_session',
            'create_game', 'get_game_state', 'make_guess', 'abort_game', 'list_session_games',
            'get_user_stats', 'get_session_stats', 'get_global_stats',
            'get_leaderboard', 'list_dictionaries'
        ]
        
        missing = []
        for method_name in required_methods:
            if not hasattr(api, method_name):
                missing.append(method_name)
            elif not callable(getattr(api, method_name)):
                missing.append(f"{method_name} (not callable)")
        
        if missing:
            print(f"  ❌ Metode lipsă: {', '.join(missing)}")
            return False
        
        print(f"  ✅ Toate cele {len(required_methods)} metode există")
        return True
        
    except Exception as e:
        print(f"  ❌ Eroare: {e}")
        return False

def test_gui_class_structure():
    """Test 3: Verifică structura clasei HangmanGUI."""
    print("\n🎨 Test 3: Verifică structura HangmanGUI...")
    
    try:
        from gui_client_pro import HangmanGUI
        
        required_methods = [
            'start_server', 'show_server_status',
            'clear_window', 'create_header', 'create_menu_bar',
            'setup_login_page', 'do_login', 'do_register', 'logout',
            'show_dashboard', 'quick_create_session',
            'show_sessions_page', 'show_session_details',
            'show_game_page', 'show_stats_page',
            'show_leaderboard_page', 'show_settings_page'
        ]
        
        # Nu putem instanția GUI fără Tk, dar putem verifica că metoda există
        missing = []
        for method_name in required_methods:
            if not hasattr(HangmanGUI, method_name):
                missing.append(method_name)
        
        if missing:
            print(f"  ❌ Metode lipsă: {', '.join(missing)}")
            return False
        
        print(f"  ✅ Toate cele {len(required_methods)} metode GUI există")
        return True
        
    except Exception as e:
        print(f"  ❌ Eroare: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_imports():
    """Test 4: Verifică că toate import-urile funcționează."""
    print("\n📦 Test 4: Verifică import-uri...")
    
    required_modules = [
        'tkinter', 'requests', 'json', 'subprocess', 
        'sys', 'os', 'time', 'threading'
    ]
    
    missing = []
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing.append(module)
    
    if missing:
        print(f"  ❌ Module lipsă: {', '.join(missing)}")
        return False
    
    print(f"  ✅ Toate cele {len(required_modules)} module sunt disponibile")
    return True

def run_all_tests():
    """Rulează toate testele de componente."""
    print("="*60)
    print("🧪 TESTE UI - COMPONENTE GUI")
    print("="*60)
    
    tests = [
        test_imports,
        test_api_wrapper_init,
        test_api_wrapper_methods,
        test_gui_class_structure
    ]
    
    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"\n❌ Excepție în {test_func.__name__}: {e}")
            results.append(False)
    
    print("\n" + "="*60)
    passed = sum(results)
    total = len(results)
    
    if all(results):
        print(f"✅ TOATE TESTELE AU TRECUT! ({passed}/{total})")
        print("="*60)
        return True
    else:
        print(f"⚠️ UNELE TESTE AU EȘUAT: {passed}/{total} trecute")
        print("="*60)
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
