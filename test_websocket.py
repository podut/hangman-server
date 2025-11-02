"""
Simple Python WebSocket test client for Hangman Server API.
Tests WebSocket endpoint with authentication.
"""

import asyncio
import json
import sys
from websockets import connect, ConnectionClosedError
import requests

# Configuration
API_BASE = "http://localhost:8000/api/v1"
WS_URL = "ws://localhost:8000/ws"
EMAIL = "test_ws@example.com"
PASSWORD = "Test123!"


def register_user():
    """Register a test user."""
    print(f"📝 Registering user: {EMAIL}")
    
    response = requests.post(
        f"{API_BASE}/auth/register",
        json={
            "email": EMAIL,
            "password": PASSWORD,
            "nickname": "WSTest"
        }
    )
    
    if response.status_code == 201:
        print("✅ User registered successfully!")
        return True
    elif response.status_code == 409:
        print("ℹ️  User already exists, will use existing account")
        return True
    else:
        print(f"❌ Registration failed: {response.json()}")
        return False


def login_user():
    """Login and get access token."""
    print(f"🔓 Logging in as: {EMAIL}")
    
    response = requests.post(
        f"{API_BASE}/auth/login",
        json={
            "email": EMAIL,
            "password": PASSWORD
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        token = data["access_token"]
        print(f"✅ Login successful!")
        print(f"🎫 Token: {token[:50]}...")
        return token
    else:
        print(f"❌ Login failed: {response.json()}")
        return None


async def test_websocket(token):
    """Test WebSocket connection with various message types."""
    ws_url_with_token = f"{WS_URL}?token={token}"
    
    print(f"\n🔌 Connecting to WebSocket: {WS_URL}")
    
    try:
        async with connect(ws_url_with_token) as websocket:
            print("✅ WebSocket connected!")
            
            # Wait for welcome message
            welcome = await websocket.recv()
            welcome_data = json.loads(welcome)
            print(f"📨 Received welcome: {json.dumps(welcome_data, indent=2)}")
            
            # Test 1: Ping/Pong
            print("\n🏓 Test 1: Sending PING...")
            await websocket.send(json.dumps({
                "type": "ping",
                "data": {}
            }))
            
            response = await websocket.recv()
            pong_data = json.loads(response)
            print(f"📨 Received: {json.dumps(pong_data, indent=2)}")
            assert pong_data["type"] == "pong", "Expected pong response"
            print("✅ Ping/Pong test passed!")
            
            # Test 2: Subscribe to channel
            print("\n📡 Test 2: Subscribing to 'games' channel...")
            await websocket.send(json.dumps({
                "type": "subscribe",
                "data": {"channel": "games"}
            }))
            
            response = await websocket.recv()
            subscribe_data = json.loads(response)
            print(f"📨 Received: {json.dumps(subscribe_data, indent=2)}")
            assert subscribe_data["type"] == "subscribed", "Expected subscribed response"
            assert subscribe_data["data"]["channel"] == "games", "Expected games channel"
            print("✅ Subscribe test passed!")
            
            # Test 3: Send custom message
            print("\n💌 Test 3: Sending custom message...")
            await websocket.send(json.dumps({
                "type": "message",
                "data": {"text": "Hello from Python test client!", "test": True}
            }))
            
            response = await websocket.recv()
            message_data = json.loads(response)
            print(f"📨 Received: {json.dumps(message_data, indent=2)}")
            assert message_data["type"] == "message_received", "Expected message_received response"
            print("✅ Custom message test passed!")
            
            # Test 4: Unknown message type (should get error)
            print("\n❓ Test 4: Sending unknown message type...")
            await websocket.send(json.dumps({
                "type": "unknown_type",
                "data": {}
            }))
            
            response = await websocket.recv()
            error_data = json.loads(response)
            print(f"📨 Received: {json.dumps(error_data, indent=2)}")
            assert error_data["type"] == "error", "Expected error response"
            print("✅ Unknown message type test passed!")
            
            print("\n🎉 All WebSocket tests passed!")
            
    except ConnectionClosedError as e:
        print(f"❌ WebSocket connection closed: {e}")
        return False
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


def main():
    """Main test function."""
    print("=" * 60)
    print("🧪 Hangman Server - WebSocket Test Client")
    print("=" * 60)
    
    # Step 1: Register user (if needed)
    if not register_user():
        print("\n❌ Failed to register user. Exiting.")
        sys.exit(1)
    
    # Step 2: Login and get token
    token = login_user()
    if not token:
        print("\n❌ Failed to login. Exiting.")
        sys.exit(1)
    
    # Step 3: Test WebSocket
    print("\n" + "=" * 60)
    print("Testing WebSocket Connection...")
    print("=" * 60)
    
    success = asyncio.run(test_websocket(token))
    
    if success:
        print("\n" + "=" * 60)
        print("✅ All tests completed successfully!")
        print("=" * 60)
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("❌ Some tests failed!")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
