#!/usr/bin/env python3
"""
Teste pentru pornirea serverului și conectarea clientului.
Testează dacă serverul pornește corect înainte de a lansa GUI-ul.
"""
import subprocess
import sys
import os
import time
import requests
from pathlib import Path

def test_server_already_running():
    """Test 1: Verifică dacă serverul deja rulează."""
    print("\n🔍 Test 1: Verifică server existent...")
    try:
        resp = requests.get("http://localhost:8000/healthz", timeout=2)
        if resp.status_code == 200:
            print("✅ Serverul deja rulează!")
            return True
        else:
            print(f"⚠️ Status code neașteptat: {resp.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Serverul NU rulează")
        return False
    except Exception as e:
        print(f"❌ Eroare: {e}")
        return False

def test_start_server():
    """Test 2: Pornește serverul și verifică dacă devine disponibil."""
    print("\n🚀 Test 2: Pornesc serverul...")
    
    # Găsește directorul server
    current_dir = Path(__file__).parent.parent
    server_dir = current_dir / "server"
    
    if not server_dir.exists():
        print(f"❌ Directorul server nu există: {server_dir}")
        return None
    
    print(f"📁 Director server: {server_dir}")
    
    # Pornește serverul
    try:
        if sys.platform == "win32":
            process = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "src.main:app", 
                 "--host", "0.0.0.0", "--port", "8000"],
                cwd=str(server_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        else:
            process = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "src.main:app",
                 "--host", "0.0.0.0", "--port", "8000"],
                cwd=str(server_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        
        print(f"⏳ Proces pornit (PID: {process.pid}), aștept să devină disponibil...")
        
        # Așteaptă până devine disponibil (max 30 secunde)
        for i in range(60):
            try:
                resp = requests.get("http://localhost:8000/healthz", timeout=1)
                if resp.status_code == 200:
                    print(f"✅ Server disponibil după {i * 0.5:.1f} secunde!")
                    return process
            except requests.exceptions.ConnectionError:
                pass
            except Exception as e:
                print(f"⚠️ Excepție la iterația {i}: {e}")
            
            time.sleep(0.5)
            
            # Verifică dacă procesul încă rulează
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                print(f"❌ Procesul s-a oprit prematur!")
                print(f"STDOUT:\n{stdout.decode()}")
                print(f"STDERR:\n{stderr.decode()}")
                return None
        
        print("❌ Timeout: serverul nu a devenit disponibil în 30 secunde")
        
        # Afișează output pentru debugging
        if process.poll() is None:
            print("\n📋 Server încă rulează, citesc output...")
            time.sleep(1)
        
        return process
        
    except Exception as e:
        print(f"❌ Eroare pornire server: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_api_endpoints(base_url="http://localhost:8000/api/v1"):
    """Test 3: Testează endpoint-uri API esențiale."""
    print("\n🔌 Test 3: Testez endpoint-uri API...")
    
    tests = [
        ("Health check", "GET", "http://localhost:8000/healthz"),
        ("OpenAPI docs", "GET", "http://localhost:8000/docs"),
        ("API root", "GET", base_url),
    ]
    
    results = []
    for name, method, url in tests:
        try:
            if method == "GET":
                resp = requests.get(url, timeout=5)
            
            if resp.status_code == 200:
                print(f"  ✅ {name}: OK ({resp.status_code})")
                results.append(True)
            else:
                print(f"  ⚠️ {name}: Status {resp.status_code}")
                results.append(False)
        except Exception as e:
            print(f"  ❌ {name}: {str(e)[:50]}")
            results.append(False)
    
    return all(results)

def test_auth_flow(base_url="http://localhost:8000/api/v1"):
    """Test 4: Testează fluxul de autentificare."""
    print("\n🔐 Test 4: Testez autentificare...")
    
    import random
    email = f"test_ui_{random.randint(1000, 9999)}@test.com"
    password = "TestPassword123"
    
    try:
        # Register
        print(f"  📝 Înregistrez user: {email}")
        resp = requests.post(f"{base_url}/auth/register",
                            json={"email": email, "password": password})
        
        if resp.status_code != 201:
            print(f"  ❌ Register failed: {resp.status_code}")
            print(f"  Response: {resp.text}")
            return False
        
        user_data = resp.json()
        print(f"  ✅ User creat: {user_data['user_id']}")
        
        # Login
        print(f"  🔓 Login cu user: {email}")
        resp = requests.post(f"{base_url}/auth/login",
                            json={"email": email, "password": password})
        
        if resp.status_code != 200:
            print(f"  ❌ Login failed: {resp.status_code}")
            return False
        
        login_data = resp.json()
        print(f"  ✅ Login OK, token: {login_data['access_token'][:20]}...")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Eroare: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_all_tests():
    """Rulează toate testele."""
    print("="*60)
    print("🧪 TESTE UI - PORNIRE SERVER ȘI CONECTIVITATE")
    print("="*60)
    
    server_process = None
    
    try:
        # Test 1: Server deja rulează?
        if test_server_already_running():
            print("\n✅ Folosesc serverul existent")
        else:
            # Test 2: Pornește server
            server_process = test_start_server()
            if not server_process:
                print("\n❌ FAILED: Nu am putut porni serverul")
                return False
        
        # Test 3: Endpoint-uri
        if not test_api_endpoints():
            print("\n⚠️ WARNING: Unele endpoint-uri au probleme")
        
        # Test 4: Autentificare
        if not test_auth_flow():
            print("\n❌ FAILED: Fluxul de autentificare nu funcționează")
            return False
        
        print("\n" + "="*60)
        print("✅ TOATE TESTELE AU TRECUT!")
        print("="*60)
        return True
        
    except KeyboardInterrupt:
        print("\n⚠️ Întrerupt de user")
        return False
    finally:
        # Cleanup: oprește serverul dacă l-am pornit noi
        if server_process and server_process.poll() is None:
            print("\n🛑 Opresc serverul de test...")
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
                print("✅ Server oprit")
            except:
                server_process.kill()
                print("⚠️ Server forțat să se oprească")

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
