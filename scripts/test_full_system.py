import sys
import os
import asyncio
import uuid
os.environ["USE_SQLITE"] = "true"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import urllib.request
import json

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


def run_full_system_test():
    print("================================================================")
    print("   DOOM OTT BACKEND - FULL SYSTEM & REGRESSION TEST SUITE       ")
    print("================================================================")

    print("\n--- Phase 1: Admin Login & Authentication ---")
    admin_login_data = {"email": "admin@doomott.com", "password": "AdminPass123!"}
    st, admin_auth = make_request("/auth/admin/login", method="POST", data=admin_login_data)
    print("Admin Login Status:", st)
    assert st == 200
    admin_token = admin_auth["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    print("Admin access token issued successfully.")

    print("\n--- Phase 2: Admin User Management & Block Toggle ---")
    # Register a temporary user to test user listing & blocking
    temp_user_data = {
        "email": f"testuser_{uuid.uuid4().hex[:6]}@doomott.com",
        "password": "UserPassword123!",
        "name": "Temporary Test User",
    }
    st, user_auth = make_request("/auth/email/signup", method="POST", data=temp_user_data)
    assert st == 201
    user_token = user_auth["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    st, me_info = make_request("/auth/me", method="GET", headers=user_headers)
    assert st == 200
    user_id = me_info["id"]

    # Fetch admin users list
    st, user_list = make_request("/admin/users", method="GET", headers=admin_headers)
    print(f"Admin User List: {user_list['total']} users found.")
    assert st == 200
    assert user_list["total"] >= 1

    # Block user
    st, blocked_res = make_request(f"/admin/users/{user_id}/block", method="PATCH", data={"is_blocked": True}, headers=admin_headers)
    print("Blocked User Status:", st, "is_blocked:", blocked_res.get("is_blocked"))
    assert st == 200
    assert blocked_res["is_blocked"] == True

    # Confirm user gets 403 Forbidden when calling authenticated endpoint while blocked
    st, blocked_err = make_request("/users/me", method="GET", headers=user_headers)
    print("Blocked user /users/me attempt (expected 403):", st, blocked_err)
    assert st == 403

    # Unblock user
    st, unblocked_res = make_request(f"/admin/users/{user_id}/block", method="PATCH", data={"is_blocked": False}, headers=admin_headers)
    assert st == 200
    assert unblocked_res["is_blocked"] == False
    print("User unblocked successfully.")

    print("\n--- Phase 3: Admin Reports & Broadcast Notifications ---")
    st, reports = make_request("/admin/reports/overview", method="GET", headers=admin_headers)
    print("Reports Overview Response:", st, reports)
    assert st == 200
    assert "total_users" in reports
    assert "active_subscriptions" in reports
    assert "revenue_this_month" in reports

    broadcast_payload = {
        "title": "Season Finale Stream",
        "body": "The thrilling season finale of Doom: Legacy is now live!",
        "target_segment": "all",
    }
    st, b_res = make_request("/admin/notifications/broadcast", method="POST", data=broadcast_payload, headers=admin_headers)
    print("Broadcast Response:", st, b_res)
    assert st == 200
    assert b_res["notifications_created"] >= 1

    print("\n--- Phase 4: Video Upload & Publishing Pipeline ---")
    draft_payload = {
        "title": f"Doom: Ragnarok {uuid.uuid4().hex[:4]}",
        "type": "movie",
        "synopsis": "An interstellar battle for survival across distant planetary rings.",
        "cast": ["Karl Urban", "Elena Vance"],
        "genre": ["Action", "Sci-Fi"],
        "language": "English",
        "content_rating": "PG-13",
        "release_year": 2026,
        "duration_minutes": 135,
        "poster_url": "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=600",
        "backdrop_url": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=1200",
    }
    st, content = make_request("/admin/content", method="POST", data=draft_payload, headers=admin_headers)
    assert st == 201
    content_id = content["id"]

    # Request video upload
    st, upload_info = make_request(f"/admin/content/{content_id}/video-upload", method="POST", headers=admin_headers)
    assert st == 200
    video_asset_id = upload_info["video_asset_id"]

    # Mark video asset ready
    st, dev_res = make_request(f"/admin/dev/mark-video-ready/{video_asset_id}", method="POST")
    assert st == 200

    # Publish content
    st, pub_content = make_request(f"/admin/content/{content_id}/publish", method="POST", headers=admin_headers)
    assert st == 200
    assert pub_content["status"] == "published"
    print(f"Content '{pub_content['title']}' created, video uploaded, ready & published!")

    print("\n--- Phase 5: Public Catalog Browsing & Playback URL ---")
    st, catalog = make_request("/content?page=1&page_size=10", method="GET")
    assert st == 200
    print(f"Public Catalog: {catalog['total']} items available.")

    st, detail = make_request(f"/content/{content_id}", method="GET")
    assert st == 200

    st, playback = make_request(f"/content/{content_id}/playback-url", method="GET", headers=user_headers)
    print("Signed Playback URL:", st, playback.get("playback_url"))
    assert st == 200
    assert playback["playback_url"].startswith("http")

    print("\n--- Phase 6: Subscription Plans, Coupon Checkout & Payment Verification ---")
    st, plans = make_request("/subscription/plans", method="GET")
    assert st == 200
    plan = plans[0]

    checkout_payload = {
        "plan_id": plan["id"],
        "coupon_code": "WELCOME50",
    }
    st, checkout = make_request("/payment/checkout", method="POST", data=checkout_payload, headers=user_headers)
    assert st == 200
    tx_id = checkout["transaction_id"]

    verify_payload = {
        "transaction_id": tx_id,
        "payment_id": f"pay_sys_test_{uuid.uuid4().hex[:6]}",
        "signature": "sig_valid_sys_test",
    }
    st, verify = make_request("/payment/verify", method="POST", data=verify_payload, headers=user_headers)
    assert st == 200

    st, sub = make_request("/subscription/current", method="GET", headers=user_headers)
    assert st == 200
    assert sub["status"] == "active"

    st, history = make_request("/payment/history", method="GET", headers=user_headers)
    assert st == 200
    assert len(history) >= 1
    assert history[0]["status"] == "success"

    print("\n================================================================")
    print(" ALL 6 PHASES PASSED WITH ZERO REGRESSIONS! SYSTEM IS READY! ")
    print("================================================================")


if __name__ == "__main__":
    run_full_system_test()
