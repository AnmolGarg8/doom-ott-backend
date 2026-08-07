import sys
import os
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


def run_tests():
    print("--- 1. Testing GET /content (Public Catalog) ---")
    st, res = make_request("/content")
    print("Content List Status:", st, "Total Items:", res.get("total"))
    assert st == 200
    assert res["total"] >= 10
    titles = [item["title"] for item in res["items"]]
    print("Seeded Titles Found:", titles[:5])
    assert "Doom: The Beginning" in titles
    assert "Tears of Steel" in titles
    assert "Sintel: The Quest" in titles

    print("\n--- 2. Testing GET /content with Filters ---")
    st, res = make_request("/content?type=series")
    print("Filter type=series:", st, [item["title"] for item in res["items"]])
    assert st == 200
    assert any(item["title"] == "Cyberpunk 2099" for item in res["items"])

    st, res = make_request("/content?genre=Animation")
    print("Filter genre=Animation:", st, [item["title"] for item in res["items"]])
    assert st == 200
    assert any(item["title"] == "Sintel: The Quest" for item in res["items"])

    st, res = make_request("/content?search=Doom")
    print("Filter search=Doom:", st, [item["title"] for item in res["items"]])
    assert st == 200
    assert len(res["items"]) == 1

    print("\n--- 3. Testing GET /content/{id} & Episodes ---")
    st, catalog = make_request("/content?type=series")
    series_id = catalog["items"][0]["id"]
    st, detail = make_request(f"/content/{series_id}")
    print("Series Detail Title:", detail["title"], "Episodes Count:", len(detail.get("episodes", [])))
    assert st == 200
    assert len(detail["episodes"]) > 0

    print("\n--- 4. Testing GET /content/{id}/similar ---")
    movie_id = catalog["items"][0]["id"]
    st, similar = make_request(f"/content/{movie_id}/similar")
    print("Similar Items Count:", len(similar))
    assert st == 200

    print("\n--- 5. Testing GET /categories ---")
    st, cats = make_request("/categories")
    print("Categories Count:", len(cats), "Sample:", [c["name"] for c in cats[:4]])
    assert st == 200
    assert len(cats) >= 8

    print("\n--- 6. User Profile Management (Auth Required) ---")
    import random
    signup_data = {
        "email": f"tester_{random.randint(1000, 9999)}@doomott.com",
        "password": "Password123!",
        "name": "Profile Tester",
    }
    st, auth_res = make_request("/auth/email/signup", method="POST", data=signup_data)
    token = auth_res["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Create Profile 1, 2, 3, 4
    profiles = []
    for i in range(1, 5):
        st, prof = make_request(
            "/users/profiles",
            method="POST",
            data={"name": f"Profile {i}", "avatar_key": f"avatar_{i}", "is_kids_profile": i == 4},
            headers=auth_headers,
        )
        print(f"Created Profile {i}:", st, prof.get("name"))
        assert st == 201
        profiles.append(prof)

    # Attempt Profile 5 -> Expect 400 Bad Request (Max 4 limit)
    st, err_prof = make_request(
        "/users/profiles",
        method="POST",
        data={"name": "Profile 5 Overflow", "avatar_key": "avatar_5"},
        headers=auth_headers,
    )
    print("Profile 5 Overflow Attempt Status:", st, err_prof)
    assert st == 400
    assert "Maximum profile limit" in err_prof.get("detail", "")

    # PATCH Profile 1
    p1_id = profiles[0]["id"]
    st, updated_p1 = make_request(
        f"/users/profiles/{p1_id}",
        method="PATCH",
        data={"name": "Profile 1 Renamed"},
        headers=auth_headers,
    )
    print("Updated Profile 1 Name:", updated_p1.get("name"))
    assert st == 200 and updated_p1["name"] == "Profile 1 Renamed"

    # GET /users/me
    st, user_me = make_request("/users/me", method="GET", headers=auth_headers)
    print("User /me Profile Count:", len(user_me.get("profiles", [])))
    assert st == 200 and len(user_me["profiles"]) == 4

    print("\n--- 7. Testing Watchlist Endpoints ---")
    target_content_id = catalog["items"][0]["id"]
    st, wl_item = make_request(
        f"/watchlist/{target_content_id}", method="POST", headers=auth_headers
    )
    print("Add to Watchlist:", st, wl_item.get("content_id"))
    assert st == 201

    st, wl_list = make_request("/watchlist", method="GET", headers=auth_headers)
    print("Watchlist Count:", len(wl_list))
    assert st == 200 and len(wl_list) == 1

    st, _ = make_request(
        f"/watchlist/{target_content_id}", method="DELETE", headers=auth_headers
    )
    print("Delete from Watchlist Status:", st)
    assert st == 204

    print("\n--- 8. Testing Watch Progress Endpoints ---")
    st, wp_item = make_request(
        f"/watch-progress/{target_content_id}",
        method="PUT",
        data={"profile_id": p1_id, "position_seconds": 540},
        headers=auth_headers,
    )
    print("Upsert Watch Progress:", st, wp_item.get("position_seconds"))
    assert st == 200 and wp_item["position_seconds"] == 540

    st, wp_list = make_request(
        f"/watch-progress?profile_id={p1_id}", method="GET", headers=auth_headers
    )
    print("Get Watch Progress List Count:", len(wp_list))
    assert st == 200 and len(wp_list) == 1

    print("\nALL CATALOG, USER PROFILES, WATCHLIST & WATCH PROGRESS ENDPOINTS PASSED PERFECTLY!")


if __name__ == "__main__":
    run_tests()
