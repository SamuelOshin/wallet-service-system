# Wallet Service with Paystack, JWT & API Keys

A comprehensive backend wallet service built with FastAPI, featuring Google OAuth authentication, Paystack payment integration, API key-based service access, and asynchronous transfer processing with Celery and Redis.

## Features

✅ **Google OAuth Authentication** - Secure user sign-in with JWT tokens  
✅ **Wallet System** - Individual wallets with unique 13-digit numbers  
✅ **Paystack Deposits** - Integrate payments via Paystack  
✅ **Asynchronous Wallet Transfers** - Send money between users with background processing and idempotency  
✅ **API Key Management** - Create service-to-service authentication keys with permissions  
✅ **Transaction History** - Track all wallet activities  
✅ **Webhook Handling** - Secure Paystack webhook verification  
✅ **Permission System** - Granular control over API key capabilities  

## Architecture

```
wallet_service_system/
├── app/
│   └── api/
│       ├── core/           # Configuration, database, Celery setup
│       ├── models/         # SQLAlchemy ORM models
│       ├── routes/         # API endpoints
│       ├── schemas/        # Pydantic request/response models
│       ├── services/       # Business logic layer & Celery tasks
│       └── utils/          # Helper functions & middleware
├── alembic/                # Database migrations
├── main.py                 # Application entry point
└── .env                    # Environment configuration
```

**Background Processing:**
- **Celery**: Handles asynchronous wallet transfers
- **Redis**: Message broker and result backend for Celery
- **Idempotency**: Client-provided keys prevent duplicate transfers

## Tech Stack

- **Framework**: FastAPI 0.109.0
- **Database**: PostgreSQL/SQLite with SQLAlchemy ORM
- **Authentication**: Google OAuth 2.0 + JWT
- **Payment**: Paystack API
- **Background Tasks**: Celery with Redis
- **Migration**: Alembic

## Prerequisites

- Python 3.10+
- PostgreSQL 14+ or SQLite
- Redis Server
- Google OAuth credentials
- Paystack account (test or live)

## Installation

### 1. Clone Repository

```bash
git clone <repository-url>
cd wallet_service_system
```

### 2. Install uv (if not already installed)

```bash
pip install uv
```

### 3. Create Virtual Environment & Install Dependencies

```bash
uv sync
```

### 4. Install Redis

#### On Windows (using Chocolatey):
```bash
choco install redis-64 -y
```

#### On macOS (using Homebrew):
```bash
brew install redis
```

#### On Linux:
```bash
sudo apt update && sudo apt install redis-server
```

### 5. Configure Environment

Create `.env` file:

```bash
cp .env.example .env
```

Update `.env` with your credentials:

```env
# Database (use SQLite for development)
DATABASE_URL="sqlite:///./wallet.db"
# Or PostgreSQL
# DATABASE_URL="postgresql://user:password@localhost:5432/wallet_db"

# JWT
SECRET_KEY="your-super-secret-key-change-this"

# Google OAuth (Get from Google Cloud Console)
GOOGLE_CLIENT_ID="your-client-id.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET="your-client-secret"
GOOGLE_REDIRECT_URI="http://localhost:8000/api/v1/auth/google/callback"

# Paystack (Get from Paystack Dashboard)
PAYSTACK_SECRET_KEY="sk_test_your_secret_key"
PAYSTACK_PUBLIC_KEY="pk_test_your_public_key"
PAYSTACK_WEBHOOK_SECRET="your_webhook_secret"

# Redis (for Celery)
REDIS_URL="redis://localhost:6379/0"
CELERY_BROKER_URL="redis://localhost:6379/0"
CELERY_RESULT_BACKEND="redis://localhost:6379/0"

# Frontend URL
FRONTEND_URL="http://localhost:3000"
```

### 6. Setup Database

```bash
# For PostgreSQL: Create database
createdb wallet_db

# Run migrations
uv run alembic upgrade head
```

### 6. Setup Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable **Google+ API**
4. Go to **Credentials** → **Create Credentials** → **OAuth 2.0 Client ID**
5. Add authorized redirect URI: `http://localhost:8000/api/v1/auth/google/callback`
6. Copy Client ID and Client Secret to `.env`

### 7. Setup Paystack

1. Sign up at [Paystack](https://paystack.com/)
2. Go to **Settings** → **API Keys & Webhooks**
3. Copy **Secret Key** and **Public Key** to `.env`
4. Set **Webhook URL**: `https://your-domain.com/api/v1/wallet/paystack/webhook`
5. Copy **Webhook Secret** to `.env`

## Running the Application

### 1. Start Redis Server

```bash
# On Windows
redis-server

# On macOS/Linux (if installed via package manager)
redis-server
```

### 2. Start Celery Worker

In a new terminal:

```bash
uv run celery -A app.api.core.celery_config worker --loglevel=info
```

### 3. Start FastAPI Application

#### Development Mode

```bash
uv run fastapi dev main.py
```

#### Production Mode

```bash
uv run fastapi run main.py --host 0.0.0.0 --port 8000 --workers 4
```

API will be available at: `http://localhost:8000`

Documentation: `http://localhost:8000/docs`

## API Endpoints

### Authentication

#### Sign In with Google
```http
GET /api/v1/auth/google
```
Redirects to Google sign-in page.

#### Google Callback
```http
GET /api/v1/auth/google/callback?code={auth_code}
```
Returns JWT token after successful authentication.

**Response:**
```json
{
  "status": "SUCCESS",
  "status_code": 200,
  "message": "Authentication successful",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "user": {
      "id": 1,
      "email": "user@example.com",
      "name": "John Doe",
      "wallet_number": "1234567890123"
    }
  }
}
```

### API Key Management

#### Create API Key
```http
POST /api/v1/keys/create
Authorization: Bearer {jwt_token}
```

**Request:**
```json
{
  "name": "trading-bot",
  "permissions": ["read", "deposit", "transfer"],
  "expiry": "1M"
}
```

**Expiry Options:** `1H` (hour), `1D` (day), `1M` (month), `1Y` (year)

**Response:**
```json
{
  "status": "SUCCESS",
  "status_code": 201,
  "message": "API key created successfully",
  "data": {
    "api_key": "sk_live_abc123xyz789...",
    "name": "trading-bot",
    "permissions": ["read", "deposit", "transfer"],
    "expires_at": "2025-02-09T12:00:00Z"
  }
}
```

⚠️ **Important:** API key is shown only once. Store it securely!

#### Rollover Expired Key
```http
POST /api/v1/keys/rollover
Authorization: Bearer {jwt_token}
```

**Request:**
```json
{
  "expired_key_id": 5,
  "expiry": "1M"
}
```

Creates new key with same permissions as expired key.

#### List API Keys
```http
GET /api/v1/keys
Authorization: Bearer {jwt_token}
```

Returns all API keys (active, expired, revoked).

#### Revoke API Key
```http
DELETE /api/v1/keys/{key_id}
Authorization: Bearer {jwt_token}
```

Permanently revokes an API key.

### Wallet Operations

#### Deposit Funds
```http
POST /api/v1/wallet/deposit
Authorization: Bearer {jwt_token}
OR
x-api-key: {api_key}  # Must have 'deposit' permission
```

**Request:**
```json
{
  "amount": 5000.00
}
```

**Response:**
```json
{
  "status": "SUCCESS",
  "status_code": 200,
  "message": "Deposit initialized successfully",
  "data": {
    "reference": "DEP_1234567890_abc123",
    "authorization_url": "https://checkout.paystack.com/...",
    "amount": "5000.00"
  }
}
```

User completes payment on the `authorization_url`.

#### Paystack Webhook (Internal)
```http
POST /api/v1/wallet/paystack/webhook
x-paystack-signature: {signature}
```

**Automatically called by Paystack** when payment succeeds/fails. Credits wallet on success.

⚠️ **Critical:** Only this endpoint should credit wallets!

#### Check Deposit Status
```http
GET /api/v1/wallet/deposit/{reference}/status
Authorization: Bearer {jwt_token}
OR
x-api-key: {api_key}  # Must have 'read' permission
```

**Response:**
```json
{
  "status": "SUCCESS",
  "status_code": 200,
  "message": "Transaction status retrieved",
  "data": {
    "reference": "DEP_1234567890_abc123",
    "status": "success",
    "amount": "5000.00",
    "created_at": "2025-01-09T12:00:00Z"
  }
}
```

#### Get Wallet Balance
```http
GET /api/v1/wallet/balance
Authorization: Bearer {jwt_token}
OR
x-api-key: {api_key}  # Must have 'read' permission
```

**Response:**
```json
{
  "status": "SUCCESS",
  "status_code": 200,
  "message": "Wallet balance retrieved",
  "data": {
    "balance": "15000.00",
    "wallet_number": "1234567890123"
  }
}
```

#### Transfer Funds (Asynchronous)
```http
POST /api/v1/wallet/transfer
Authorization: Bearer {jwt_token}
OR
x-api-key: {api_key}  # Must have 'transfer' permission
```

**Request:**
```json
{
  "wallet_number": "9876543210123",
  "amount": 3000.00,
  "idempotency_key": "unique-transfer-id-12345"
}
```

**Response (202 Accepted):**
```json
{
  "status": "success",
  "status_code": 202,
  "message": "Transfer initiated successfully",
  "data": {
    "reference": "TRF_1234567890_xyz",
    "status": "pending"
  }
}
```

**Notes:**
- Transfers are processed asynchronously in the background using Celery
- Use the `idempotency_key` to prevent duplicate transfers (client-generated UUID)
- Poll the transfer status using the reference

#### Check Transfer Status
```http
GET /api/v1/wallet/transfer/{reference}/status
Authorization: Bearer {jwt_token}
OR
x-api-key: {api_key}  # Must have 'read' permission
```

**Response (when pending):**
```json
{
  "status": "success",
  "status_code": 200,
  "message": "Transfer status retrieved",
  "data": {
    "reference": "TRF_1234567890_xyz",
    "status": "pending",
    "created_at": "2024-01-01T12:00:00Z"
  }
}
```

**Response (when completed):**
```json
{
  "status": "success",
  "status_code": 200,
  "message": "Transfer completed successfully",
  "data": {
    "reference": "TRF_1234567890_xyz",
    "status": "completed",
    "amount": "3000.00",
    "recipient_wallet": "9876543210123",
    "completed_at": "2024-01-01T12:00:05Z"
  }
}
```

**Response (when failed):**
```json
{
  "status": "failure",
  "status_code": 200,
  "message": "Transfer failed",
  "data": {
    "reference": "TRF_1234567890_xyz",
    "status": "failed",
    "error": "Insufficient funds",
    "failed_at": "2024-01-01T12:00:05Z"
  }
}
```

#### Transaction History
```http
GET /api/v1/wallet/transactions
Authorization: Bearer {jwt_token}
OR
x-api-key: {api_key}  # Must have 'read' permission
```

**Response:**
```json
{
  "status": "SUCCESS",
  "status_code": 200,
  "message": "Transaction history retrieved",
  "data": {
    "transactions": [
      {
        "id": 1,
        "type": "deposit",
        "amount": "5000.00",
        "status": "success",
        "reference": "DEP_123",
        "metadata": {},
        "created_at": "2025-01-09T12:00:00Z"
      },
      {
        "id": 2,
        "type": "transfer_out",
        "amount": "3000.00",
        "status": "success",
        "reference": "TRF_456",
        "metadata": {"recipient_wallet": "9876543210123"},
        "created_at": "2025-01-09T13:00:00Z"
      }
    ],
    "total": 2
  }
}
```

## Authentication Methods

### 1. JWT Token (For Users)

Used after Google sign-in:

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

**Permissions:** Full access to all wallet operations.

### 2. API Key (For Services)

Used for service-to-service access:

```http
x-api-key: sk_live_abc123xyz789...
```

**Permissions:** Limited to specified permissions (`read`, `deposit`, `transfer`).

## Security Features

✅ **Signature Verification** - All Paystack webhooks are verified  
✅ **API Key Hashing** - Keys stored as SHA-256 hashes  
✅ **Permission System** - Granular access control  
✅ **Key Expiry** - Automatic expiration of API keys  
✅ **Rate Limiting** - Maximum 5 active keys per user  
✅ **Atomic Transactions** - Transfers succeed or fail completely  
✅ **Idempotent Webhooks** - Prevents double-crediting  

## Testing

### Test Paystack Payments

Use test cards in sandbox mode:

**Success:**
```
Card: 4084 0840 8408 4081
CVV: 408
Expiry: Any future date
PIN: 0000
OTP: 123456
```

**Insufficient Funds:**
```
Card: 5060 6666 6666 6666
CVV: 123
Expiry: Any future date
```

### Testing Webhooks Locally

Use [ngrok](https://ngrok.com/) to expose local server:

```bash
ngrok http 8000
```

Update Paystack webhook URL to ngrok URL:
```
https://your-ngrok-url.ngrok.io/api/v1/wallet/paystack/webhook
```

## Common Issues

### Issue: Google OAuth Redirect Mismatch

**Solution:** Ensure redirect URI in Google Console matches `.env`:
```
http://localhost:8000/api/v1/auth/google/callback
```

### Issue: Paystack Webhook Not Working

**Solution:**
1. Verify webhook URL is publicly accessible (use ngrok for local testing)
2. Check `PAYSTACK_WEBHOOK_SECRET` matches Paystack dashboard
3. Ensure webhook signature validation is enabled

### Issue: API Key Permission Denied

**Solution:** Check API key has required permission:
- `/wallet/deposit` → needs `deposit`
- `/wallet/transfer` → needs `transfer`
- `/wallet/balance` → needs `read`

## Project Structure Explained

```
app/api/
├── core/
│   ├── config.py          # Environment configuration
│   ├── database.py        # Database connection
│   └── celery_config.py   # Celery background task configuration
├── models/
│   ├── base.py            # Base model & mixins
│   └── user.py            # User, Wallet, Transaction, APIKey, IdempotencyKey models
├── routes/
│   ├── auth.py            # Google OAuth endpoints
│   ├── api_keys.py        # API key management
│   └── wallet.py          # Wallet operations (including async transfers)
├── schemas/
│   ├── auth.py            # Auth request/response schemas
│   ├── api_key.py         # API key schemas
│   └── wallet.py          # Wallet schemas (updated for async transfers)
├── services/
│   ├── google_auth_service.py  # Google OAuth logic
│   ├── wallet_service.py       # Wallet business logic
│   ├── api_key_service.py      # API key management logic
│   └── tasks.py                # Celery background tasks
└── utils/
    ├── auth_middleware.py      # JWT & API key authentication
    ├── security.py             # Hashing, JWT, signature verification
    ├── response_payload.py     # Standard response helpers
    └── exception_handlers.py   # Global error handling
```

## Asynchronous Transfer Processing

Wallet transfers are processed asynchronously using Celery to prevent timeouts and ensure reliability:

- **Initiation**: Client sends transfer request with idempotency key
- **Queueing**: Transfer is queued as a background task
- **Processing**: Celery worker processes the transfer atomically
- **Status Polling**: Client can check transfer status using the reference
- **Idempotency**: Duplicate requests with same key are rejected

**Benefits:**
- No request timeouts for large transfers
- Reliable processing even during high load
- Duplicate prevention via client-provided keys
- Real-time status updates

## License

MIT License

## Support

For issues and questions, please open an issue on GitHub.

---

