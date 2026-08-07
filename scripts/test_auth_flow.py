import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import urllib.request
import json
from app.services.auth_service import _in_memory_redis_fallback

BASE_URL = "http://127.0.0.1:8000"


def make_request(path, method="GET", data=None, headers=None):
    url = f"{BASE_URL}{path}"
    headers = headers or {}
    if data is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode("utf-8")
    else:
        body = None

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            status_code = resp.status
            resp_body = resp.read().decode("utf-8")
            return status_code, json.loads(resp_body) if resp_body else {}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        return e.code, json.loads(err_body) if err_body else {}


def run_tests():
    print("--- 1. Testing GET /health ---")
    st, res = make_request("/health")
    print("Health Status:", st, res)
    assert st == 200 and res.get("status") == "ok"

    print("\n--- 2. Testing POST /auth/otp/send ---")
    import random
    phone = f"+19876{random.randint(1000000, 9999999)}"
    st, res = make_request("/auth/otp/send", method="POST", data={"phone": phone})
    print("Send OTP:", st, res)
    assert st == 200

    print("\n--- 3. Testing POST /auth/otp/verify ---")
    st, res = make_request("/auth/otp/verify", method="POST", data={"phone": phone, "otp": "123456"})
    print("Verify OTP:", st, res)
    assert st == 200
    assert "access_token" in res

    print("\n--- 4. Testing POST /auth/email/signup ---")
    import uuid
    test_email = f"user_{uuid.uuid4().hex[:6]}@doomott.com"
    signup_data = {
        "email": test_email,
        "password": "SuperSecretPassword123!",
        "name": "Doom Champion",
    }
    st, res = make_request("/auth/email/signup", method="POST", data=signup_data)
    print("Email Signup:", st, res)
    assert st == 201

    print("\n--- 5. Testing POST /auth/email/login ---")
    login_data = {
        "email": test_email,
        "password": "SuperSecretPassword123!",
    }
    st, res = make_request("/auth/email/login", method="POST", data=login_data)
    print("Email Login:", st, res)
    assert st == 200
    access_token = res["access_token"]
    refresh_token = res["refresh_token"]

    print("\n--- 6. Testing GET /auth/me (Protected Route with JWT) ---")
    st, res = make_request(
        "/auth/me",
        method="GET",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    print("Get Current User (/auth/me):", st, res)
    assert st == 200
    assert res["email"] == test_email

    print("\n--- 7. Testing POST /auth/social/google ---")
    st, res = make_request(
        "/auth/social/google",
        method="POST",
        data={"id_token": "mock_google_user_777"},
    )
    print("Google Social Auth:", st, res)
    assert st == 200

    print("\n--- 8. Testing POST /auth/social/apple ---")
    st, res = make_request(
        "/auth/social/apple",
        method="POST",
        data={"id_token": "mock_apple_user_888"},
    )
    print("Apple Social Auth:", st, res)
    assert st == 200

    print("\n--- 9. Testing POST /auth/refresh ---")
    st, res = make_request(
        "/auth/refresh",
        method="POST",
        data={"refresh_token": refresh_token},
    )
    print("Refresh Token:", st, res)
    assert st == 200
    assert "access_token" in res

    print("\n--- 10. Testing POST /auth/logout ---")
    st, res = make_request(
        "/auth/logout",
        method="POST",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    print("Logout:", st, res)
    assert st == 200

    print("\nALL 10 AUTHENTICATION TEST CASES PASSED PERFECTLY!")


if __name__ == "__main__":
    run_tests()
