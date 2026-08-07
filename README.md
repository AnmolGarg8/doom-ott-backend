# DOOM OTT Backend

Production-grade FastAPI backend for **DOOM OTT**, a high-performance video streaming platform.

Built with Python 3.12, FastAPI, Async SQLAlchemy 2.0, PostgreSQL, Redis, Alembic, and Pydantic v2. Uses clean provider abstractions for SMS, Video CDN streaming, and Payment Gateways.

---

## Tech Stack & Architecture

- **Framework**: FastAPI (Async Python 3.12, Uvicorn)
- **Database**: PostgreSQL 16 (Async SQLAlchemy 2.0 + `asyncpg`, SQLite fallback for dev)
- **Migrations**: Alembic
- **Caching & OTP**: Redis (`redis.asyncio` with in-memory fallback for local dev)
- **Authentication**: JWT access tokens (15-min TTL) & refresh tokens (30-day TTL bcrypt-hashed in Redis), passlib/bcrypt password hashing, SMS OTP authentication, Admin-scoped auth.
- **Provider Abstractions**:
  - **SMS**: Mock SMS logger & MSG91 SMS gateway driver (`SMS_PROVIDER`)
  - **Video**: Mock public video stream driver & Bunny Stream CDN driver with SHA-256 token security (`VIDEO_PROVIDER`)
  - **Payment**: Mock payment checkout/verification & Razorpay Gateway driver with HMAC verification (`PAYMENT_PROVIDER`)

---

## Project Structure

```text
doom-ott-backend/
├── app/
│   ├── main.py                     # FastAPI application entry point & router registration
│   ├── dependencies.py             # Auth dependencies (get_current_user, get_current_admin, get_db, get_redis)
│   ├── core/
│   │   ├── config.py               # Pydantic-settings configuration
│   │   ├── database.py             # Async SQLAlchemy engine & session maker
│   │   ├── security.py             # JWT token handling & password hashing
│   │   └── redis_client.py         # Redis async client & fallback handling
│   ├── models/                     # SQLAlchemy 2.0 models (User, Profile, Content, VideoAsset, Subscription, etc.)
│   ├── schemas/                    # Pydantic v2 schemas (Auth, Content, Billing, Admin)
│   ├── providers/                  # Modular provider interfaces & implementations
│   │   ├── sms/                    # SMSProvider (MockSMSProvider, MSG91Provider)
│   │   ├── video/                  # VideoProvider (MockVideoProvider, BunnyStreamProvider)
│   │   └── payment/                # PaymentProvider (MockPaymentProvider, RazorpayProvider)
│   ├── routers/                    # API Route definitions
│   │   ├── auth.py                 # OTP send/verify, email signup/login, admin login, refresh, logout
│   │   ├── users.py                # Profile management (CRUD max 4 per user)
│   │   ├── content.py              # Catalog browsing, playback URLs, watchlist, watch progress
│   │   ├── subscription.py         # Active plans & current subscription status
│   │   ├── payment.py              # Checkout, payment verification & transaction history
│   │   └── admin/                  # Admin panel endpoints (Content pipeline, Billing/Coupons, Users/Reports)
│   └── services/                   # Business logic (AuthService, etc.)
├── alembic/                        # DB migration scripts
├── scripts/                        # Automated end-to-end test suites
├── seed_data.py                    # Database seeder (Categories, Plans, Coupons, Admin User, Demo Content)
├── Dockerfile                      # Production container image
├── docker-compose.yml              # Local PostgreSQL 16 & Redis 7 development containers
├── requirements.txt                # Python dependencies
└── .env.example                    # Environment configuration template
```

---

## Quickstart & Local Setup

### 1. Clone & Environment Setup
```bash
git clone https://github.com/AnmolGarg8/doom-ott-backend.git
cd doom-ott-backend

# Create virtual environment
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
```

### 2. Start Database & Redis via Docker
```bash
docker-compose up -d
```

### 3. Run Database Migrations & Seed Data
```bash
# Run Alembic migrations
alembic upgrade head

# Seed initial categories, subscription plans, demo coupons, admin user, and content catalog
python seed_data.py
```

### 4. Start Development Server
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
Open Interactive API Docs (Swagger UI) at: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## Demo Admin Credentials

The database seeder initializes a default superadmin user for testing admin endpoints:
- **Email**: `admin@doomott.com`
- **Password**: `AdminPass123!`
- **Endpoint**: `POST /auth/admin/login`

---

## Switching Providers from Mock to Production

The backend uses environment flags to toggle between mock mode (zero external API calls required) and live production providers:

### 1. SMS Provider (`SMS_PROVIDER`)
- **Mock Mode** (default):
  ```env
  SMS_PROVIDER=mock
  ```
  *Logs generated 6-digit OTPs directly to console/logs.*
- **MSG91 Production Mode**:
  ```env
  SMS_PROVIDER=msg91
  MSG91_AUTH_KEY=your_msg91_auth_key
  MSG91_TEMPLATE_ID=your_msg91_template_id
  ```

### 2. Video Provider (`VIDEO_PROVIDER`)
- **Mock Mode** (default):
  ```env
  VIDEO_PROVIDER=mock
  ```
  *Generates mock upload URLs and returns working public MP4 sample video streams.*
- **Bunny Stream CDN Mode**:
  ```env
  VIDEO_PROVIDER=bunny
  BUNNY_LIBRARY_ID=your_bunny_library_id
  BUNNY_API_KEY=your_bunny_api_key
  BUNNY_CDN_HOSTNAME=your_video_cdn.b-cdn.net
  BUNNY_TOKEN_KEY=your_bunny_token_authentication_key
  ```

### 3. Payment Provider (`PAYMENT_PROVIDER`)
- **Mock Mode** (default):
  ```env
  PAYMENT_PROVIDER=mock
  ```
  *Instantly simulates order creation and valid payment signature verification.*
- **Razorpay Production Mode**:
  ```env
  PAYMENT_PROVIDER=razorpay
  RAZORPAY_KEY_ID=rzp_live_your_key_id
  RAZORPAY_KEY_SECRET=your_razorpay_secret
  ```

---

## Automated Test Suites

Run end-to-end integration test scripts:
```bash
# Test Auth flow (OTP, Email, Social, Token Refresh & Logout)
python scripts/test_auth_flow.py

# Test Catalog browsing, Watchlist, Watch Progress & User Profiles
python scripts/test_catalog_and_users.py

# Test Admin Video Upload, Processing Status Webhook, Publish & Public Playback URL
python scripts/test_video_pipeline.py

# Test Subscription Plans, Coupon Discounts, Checkout, Verification & History
python scripts/test_payment_flow.py

# Run Complete End-to-End System Test
python scripts/test_full_system.py
```

---

## Production Deployment (Railway / Render / Docker)

Build and run the production Docker container:
```bash
docker build -t doom-ott-backend .
docker run -p 8000:8000 --env-file .env doom-ott-backend
```
