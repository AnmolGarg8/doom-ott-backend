import sys
import os
import asyncio
import uuid
os.environ["USE_SQLITE"] = "true"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import urllib.request
import json

from app.core.database import AsyncSessionLocal
from app.core.security import create_access_token, get_password_hash
from app.models.user import AdminUser, Role

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


async def create_test_admin():
    async with AsyncSessionLocal() as session:
        # Create role
        res = await session.execute(select_role := select(Role).where(Role.name == "SuperAdmin"))
        role = res.scalars().first()
        if not role:
            role = Role(name="SuperAdmin", permissions=["*"])
            session.add(role)
            await session.flush()

        admin_email = f"admin_{uuid.uuid4().hex[:6]}@doomott.com"
        admin = AdminUser(
            email=admin_email,
            password_hash=get_password_hash("AdminPass123!"),
            role_id=role.id,
        )
        session.add(admin)
        await session.commit()
        await session.refresh(admin)

        token = create_access_token(subject=str(admin.id))
        return token


def run_pipeline_test():
    print("--- 1. Creating Admin User & JWT Token ---")
    admin_token = asyncio.run(create_test_admin())
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    print("Admin Token Created Successfully.")

    print("\n--- 2. Creating Draft Content (POST /admin/content) ---")
    draft_payload = {
        "title": "Doom: End of Days",
        "type": "movie",
        "synopsis": "The final battle for Neo-Veridia unfolds in epic resolution.",
        "cast": ["Karl Urban", "Keanu Reeves"],
        "genre": ["Action", "Sci-Fi"],
        "language": "English",
        "content_rating": "R",
        "release_year": 2026,
        "duration_minutes": 140,
        "poster_url": "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=600",
        "backdrop_url": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=1200",
    }
    st, content = make_request("/admin/content", method="POST", data=draft_payload, headers=admin_headers)
    print("Draft Content Created:", st, "ID:", content.get("id"), "Status:", content.get("status"))
    assert st == 201
    assert content["status"] == "draft"
    content_id = content["id"]

    print("\n--- 3. Attempting to Publish without Video Asset (POST /admin/content/{id}/publish) ---")
    st, err_pub = make_request(f"/admin/content/{content_id}/publish", method="POST", headers=admin_headers)
    print("Publish without video asset (expected 400):", st, err_pub.get("detail"))
    assert st == 400

    print("\n--- 4. Requesting Video Upload URL (POST /admin/content/{id}/video-upload) ---")
    st, upload_info = make_request(f"/admin/content/{content_id}/video-upload", method="POST", headers=admin_headers)
    print("Video Upload Info:", st, upload_info)
    assert st == 200
    assert upload_info["status"] == "uploading"
    assert "upload_url" in upload_info
    video_asset_id = upload_info["video_asset_id"]

    print("\n--- 5. Marking Video Asset Ready via Dev Webhook (POST /admin/dev/mark-video-ready/{id}) ---")
    st, dev_res = make_request(f"/admin/dev/mark-video-ready/{video_asset_id}", method="POST")
    print("Mark Video Ready Status:", st, dev_res)
    assert st == 200
    assert dev_res["status"] == "ready"

    print("\n--- 6. Publishing Content (POST /admin/content/{id}/publish) ---")
    st, pub_content = make_request(f"/admin/content/{content_id}/publish", method="POST", headers=admin_headers)
    print("Published Content:", st, "New Status:", pub_content.get("status"))
    assert st == 200
    assert pub_content["status"] == "published"

    print("\n--- 7. Authenticating Regular User & Fetching Playback URL ---")
    signup_data = {
        "email": f"viewer_{uuid.uuid4().hex[:6]}@doomott.com",
        "password": "ViewerPassword123!",
        "name": "Movie Viewer",
    }
    st, user_auth = make_request("/auth/email/signup", method="POST", data=signup_data)
    user_token = user_auth["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    st, playback_info = make_request(f"/content/{content_id}/playback-url", method="GET", headers=user_headers)
    print("Playback URL Response:", st, playback_info)
    assert st == 200
    assert "playback_url" in playback_info
    assert playback_info["playback_url"].startswith("http")
    assert ".mp4" in playback_info["playback_url"] or ".m3u8" in playback_info["playback_url"]

    print("\nEND-TO-END VIDEO PIPELINE & PLAYBACK URL TEST PASSED PERFECTLY!")


if __name__ == "__main__":
    from sqlalchemy import select
    run_pipeline_test()
