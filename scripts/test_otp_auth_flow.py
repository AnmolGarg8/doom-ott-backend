import sys
import os
import urllib.request
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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


def test_otp_flow():
    phone = "+19876543210"
    print("--- 1. POST /auth/otp/send ---")
    st, send_res = make_request("/auth/otp/send", method="POST", data={"phone": phone})
    print("OTP Send Response:", st, send_res)
    assert st == 200

    # Retrieve OTP from redis / fallback or redis client directly
    import redis as sync_redis
    try:
        r = sync_redis.Redis.from_url("redis://localhost:6380/0", decode_responses=True)
        otp = r.get(f"otp:{phone}")
    except Exception:
        otp = _in_memory_redis_fallback.get(f"otp:{phone}")

    print("Retrieved OTP from Redis:", otp)
    assert otp is not None and len(otp) == 6

    print("\n--- 2. POST /auth/otp/verify ---")
    st, verify_res = make_request("/auth/otp/verify", method="POST", data={"phone": phone, "otp": otp})
    print("OTP Verify Response:", st, verify_res)
    assert st == 200
    assert "access_token" in verify_res
    assert "refresh_token" in verify_res

    access_token = verify_res["access_token"]

    print("\n--- 3. GET /auth/me ---")
    headers = {"Authorization": f"Bearer {access_token}"}
    st, me_res = make_request("/auth/me", method="GET", headers=headers)
    print("GET /auth/me Response:", st, me_res)
    assert st == 200
    assert me_res["phone"] == phone
    print("\nOTP AUTHENTICATION FLOW PASSED PERFECTLY!")


if __name__ == "__main__":
    test_otp_flow()
