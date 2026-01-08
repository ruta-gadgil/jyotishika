#!/usr/bin/env python3
"""
Test script for Google OAuth authentication endpoints.

This script helps test the authentication endpoints without needing a browser.
Note: The OAuth flow requires a browser for the actual Google login, but this
script can test the endpoints that don't require user interaction.
"""

import requests
import json
from urllib.parse import urlparse, parse_qs

# Configuration
BASE_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:3000"


def test_health_check():
    """Test that the server is running."""
    print("\n1. Testing health check endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/healthz", timeout=5)
        if response.status_code == 200:
            print("   ✓ Server is running")
            return True
        else:
            print(f"   ✗ Server returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("   ✗ Cannot connect to server. Is it running?")
        return False
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def test_me_endpoint_not_logged_in():
    """Test /me endpoint when not logged in."""
    print("\n2. Testing /me endpoint (not logged in)...")
    try:
        response = requests.get(f"{BASE_URL}/me", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("logged_in") == False:
                print("   ✓ Correctly returns logged_in: false")
                return True
            else:
                print(f"   ✗ Unexpected response: {data}")
                return False
        else:
            print(f"   ✗ Unexpected status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def test_logout_endpoint_not_logged_in():
    """Test /auth/logout endpoint when not logged in."""
    print("\n3. Testing /auth/logout endpoint (not logged in)...")
    try:
        response = requests.post(f"{BASE_URL}/auth/logout", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if "message" in data:
                print("   ✓ Logout endpoint responds correctly")
                return True
            else:
                print(f"   ✗ Unexpected response: {data}")
                return False
        else:
            print(f"   ✗ Unexpected status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def test_google_login_redirect():
    """Test that /auth/google/login redirects to Google."""
    print("\n4. Testing /auth/google/login redirect...")
    try:
        # Don't follow redirects so we can check the redirect URL
        response = requests.get(
            f"{BASE_URL}/auth/google/login",
            allow_redirects=False,
            timeout=5
        )
        if response.status_code == 302:
            redirect_url = response.headers.get("Location", "")
            if "accounts.google.com" in redirect_url:
                print("   ✓ Redirects to Google OAuth")
                print(f"   ✓ Redirect URL: {redirect_url[:80]}...")
                
                # Parse the redirect URL to check parameters
                parsed = urlparse(redirect_url)
                params = parse_qs(parsed.query)
                
                required_params = ["client_id", "redirect_uri", "response_type", "scope", "state"]
                missing = [p for p in required_params if p not in params]
                
                if not missing:
                    print("   ✓ All required OAuth parameters present")
                    return True
                else:
                    print(f"   ✗ Missing parameters: {missing}")
                    return False
            else:
                print(f"   ✗ Does not redirect to Google: {redirect_url}")
                return False
        else:
            print(f"   ✗ Unexpected status code: {response.status_code}")
            if response.status_code == 500:
                try:
                    error = response.json()
                    print(f"   Error: {error}")
                except:
                    print(f"   Response: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def test_callback_without_code():
    """Test callback endpoint without authorization code."""
    print("\n5. Testing /auth/google/callback (missing code)...")
    try:
        response = requests.get(
            f"{BASE_URL}/auth/google/callback",
            allow_redirects=False,
            timeout=5
        )
        # Should redirect to frontend with error
        if response.status_code in [302, 400]:
            print("   ✓ Correctly handles missing code")
            return True
        else:
            print(f"   ✗ Unexpected status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def test_callback_with_invalid_state():
    """Test callback endpoint with invalid state token."""
    print("\n6. Testing /auth/google/callback (invalid state)...")
    try:
        response = requests.get(
            f"{BASE_URL}/auth/google/callback?code=test_code&state=invalid_state",
            allow_redirects=False,
            timeout=5
        )
        # Should return 400 for invalid state
        if response.status_code == 400:
            data = response.json()
            if "INVALID_STATE" in str(data):
                print("   ✓ Correctly rejects invalid state token")
                return True
            else:
                print(f"   ✗ Unexpected error: {data}")
                return False
        else:
            print(f"   ✗ Unexpected status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def print_manual_testing_instructions():
    """Print instructions for manual browser testing."""
    print("\n" + "="*70)
    print("MANUAL TESTING INSTRUCTIONS")
    print("="*70)
    print("\nTo test the complete OAuth flow, you need to use a browser:")
    print("\n1. Start your Flask server:")
    print("   cd backend")
    print("   python -m flask run --port 8000")
    print("\n2. Open your browser and navigate to:")
    print(f"   {BASE_URL}/auth/google/login")
    print("\n3. You should be redirected to Google's login page.")
    print("   - Log in with your Google account")
    print("   - Grant permissions if prompted")
    print("\n4. After authentication, you'll be redirected back to:")
    print(f"   {FRONTEND_URL}?auth=success")
    print("\n5. Test the /me endpoint with cookies:")
    print("   - Open browser developer tools (F12)")
    print("   - Go to Application/Storage > Cookies")
    print("   - Verify that 'session_id' cookie is set")
    print("   - Make a request to /me endpoint:")
    print(f"     curl -v {BASE_URL}/me --cookie-jar cookies.txt --cookie cookies.txt")
    print("\n6. Test logout:")
    print(f"   curl -X POST {BASE_URL}/auth/logout --cookie-jar cookies.txt --cookie cookies.txt")
    print("\n7. Verify session is cleared:")
    print(f"   curl {BASE_URL}/me --cookie cookies.txt")
    print("   Should return: {\"logged_in\": false}")
    print("\n" + "="*70)


def main():
    """Run all tests."""
    print("="*70)
    print("Google OAuth Authentication - Test Suite")
    print("="*70)
    
    results = []
    
    # Run automated tests
    results.append(("Health Check", test_health_check()))
    results.append(("Me Endpoint (not logged in)", test_me_endpoint_not_logged_in()))
    results.append(("Logout Endpoint (not logged in)", test_logout_endpoint_not_logged_in()))
    results.append(("Google Login Redirect", test_google_login_redirect()))
    results.append(("Callback (missing code)", test_callback_without_code()))
    results.append(("Callback (invalid state)", test_callback_with_invalid_state()))
    
    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All automated tests passed!")
        print("  You can now proceed with manual browser testing.")
    else:
        print("\n⚠ Some tests failed. Check the errors above.")
        print("  Make sure your server is running and environment variables are set.")
    
    # Print manual testing instructions
    print_manual_testing_instructions()


if __name__ == "__main__":
    main()

