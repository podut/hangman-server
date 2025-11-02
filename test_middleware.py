"""
Test script to demonstrate middleware features.

This script makes various requests to the server to show:
1. Request ID generation and tracking
2. Structured logging with correlation
3. Error handling with request IDs
4. Response time tracking
"""

import requests
import json

BASE_URL = "http://localhost:8000"


def print_section(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_health_check():
    """Test health endpoint with request tracking."""
    print_section("1. Health Check with Request ID")
    
    # Request without custom request ID
    print("\nRequest WITHOUT custom X-Request-ID:")
    response = requests.get(f"{BASE_URL}/healthz")
    print(f"Status: {response.status_code}")
    print(f"X-Request-ID: {response.headers.get('X-Request-ID')}")
    print(f"X-Response-Time: {response.headers.get('X-Response-Time')}")
    print(f"Response: {response.json()}")
    
    # Request with custom request ID
    print("\n\nRequest WITH custom X-Request-ID:")
    headers = {"X-Request-ID": "test-request-12345"}
    response = requests.get(f"{BASE_URL}/healthz", headers=headers)
    print(f"Status: {response.status_code}")
    print(f"X-Request-ID: {response.headers.get('X-Request-ID')}")
    print(f"X-Response-Time: {response.headers.get('X-Response-Time')}")
    print(f"Response: {response.json()}")


def test_version():
    """Test version endpoint."""
    print_section("2. Version Endpoint")
    
    response = requests.get(f"{BASE_URL}/version")
    print(f"Status: {response.status_code}")
    print(f"X-Request-ID: {response.headers.get('X-Request-ID')}")
    print(f"X-Response-Time: {response.headers.get('X-Response-Time')}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")


def test_error_handling():
    """Test error handling with request tracking."""
    print_section("3. Error Handling with Request ID")
    
    # Test 404 error
    print("\n404 Not Found Error:")
    headers = {"X-Request-ID": "test-404-request"}
    response = requests.get(f"{BASE_URL}/api/v1/nonexistent", headers=headers)
    print(f"Status: {response.status_code}")
    print(f"X-Request-ID: {response.headers.get('X-Request-ID')}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    # Test validation error
    print("\n\nValidation Error (missing required fields):")
    headers = {"X-Request-ID": "test-validation-error"}
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/register",
        json={},  # Missing required fields
        headers=headers
    )
    print(f"Status: {response.status_code}")
    print(f"X-Request-ID: {response.headers.get('X-Request-ID')}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")


def test_authentication_error():
    """Test authentication error."""
    print_section("4. Authentication Error")
    
    print("\nUnauthorized Access (no token):")
    headers = {"X-Request-ID": "test-auth-error"}
    response = requests.get(f"{BASE_URL}/api/v1/auth/profile", headers=headers)
    print(f"Status: {response.status_code}")
    print(f"X-Request-ID: {response.headers.get('X-Request-ID')}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("  MIDDLEWARE DEMONSTRATION")
    print("  Request Tracking & Structured Logging")
    print("=" * 60)
    
    try:
        test_health_check()
        test_version()
        test_error_handling()
        test_authentication_error()
        
        print("\n" + "=" * 60)
        print("  ✓ All tests completed!")
        print("  Check server logs for structured JSON output")
        print("=" * 60 + "\n")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to server")
        print("   Make sure the server is running:")
        print("   python -m server.src.main\n")
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")


if __name__ == "__main__":
    main()
