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


def run_payment_test():
    print("--- 1. Fetching Active Subscription Plans (GET /subscription/plans) ---")
    st, plans = make_request("/subscription/plans", method="GET")
    print(f"Fetched {len(plans)} plans:", [p['name'] for p in plans])
    assert st == 200
    assert len(plans) >= 3
    selected_plan = plans[0]  # Mobile Monthly
    print(f"Selected Plan: {selected_plan['name']} (Rs. {selected_plan['price']})")

    print("\n--- 2. Authenticating New User ---")
    signup_data = {
        "email": f"subscriber_{uuid.uuid4().hex[:6]}@doomott.com",
        "password": "SubPassword123!",
        "name": "Subscriber User",
    }
    st, user_auth = make_request("/auth/email/signup", method="POST", data=signup_data)
    assert st == 201
    user_token = user_auth["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}
    print("User authenticated successfully.")

    print("\n--- 3. Initiating Checkout with Coupon WELCOME50 (POST /payment/checkout) ---")
    checkout_payload = {
        "plan_id": selected_plan["id"],
        "coupon_code": "WELCOME50",  # 50% discount
    }
    st, checkout_res = make_request("/payment/checkout", method="POST", data=checkout_payload, headers=user_headers)
    print("Checkout Response:", st, checkout_res)
    assert st == 200
    assert checkout_res["amount"] == round(float(selected_plan["price"]) * 0.5, 2)
    assert "transaction_id" in checkout_res
    assert "order_id" in checkout_res
    transaction_id = checkout_res["transaction_id"]
    order_id = checkout_res["order_id"]

    print("\n--- 4. Verifying Payment (POST /payment/verify) ---")
    verify_payload = {
        "transaction_id": transaction_id,
        "payment_id": f"pay_mock_{uuid.uuid4().hex[:8]}",
        "signature": "sig_mock_valid_signature",
    }
    st, verify_res = make_request("/payment/verify", method="POST", data=verify_payload, headers=user_headers)
    print("Verify Response:", st, verify_res)
    assert st == 200
    assert verify_res["status"] == "success"

    print("\n--- 5. Confirming Active Subscription (GET /subscription/current) ---")
    st, current_sub = make_request("/subscription/current", method="GET", headers=user_headers)
    print("Current Subscription:", st, current_sub)
    assert st == 200
    assert current_sub is not None
    assert current_sub["status"] == "active"
    assert current_sub["plan_id"] == selected_plan["id"]
    assert current_sub["plan"]["name"] == selected_plan["name"]

    print("\n--- 6. Fetching Payment History (GET /payment/history) ---")
    st, history = make_request("/payment/history", method="GET", headers=user_headers)
    print(f"Transaction History ({len(history)} items):", history)
    assert st == 200
    assert len(history) >= 1
    latest_tx = history[0]
    assert latest_tx["id"] == transaction_id
    assert latest_tx["status"] == "success"
    assert latest_tx["amount"] == checkout_res["amount"]

    print("\nEND-TO-END SUBSCRIPTION & PAYMENT PIPELINE TEST PASSED PERFECTLY!")


if __name__ == "__main__":
    run_payment_test()
