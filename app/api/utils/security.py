"""
Security utilities for JWT and API key management.

Provides functions for:
- JWT token creation and verification
- API key generation and hashing
- Password hashing (if needed in future)
"""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt

from app.api.core.config import get_settings

settings = get_settings()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Args:
        data (dict): Payload to encode in the token (e.g., {"sub": user_email, "user_id": 1}).
        expires_delta (Optional[timedelta]): Custom expiration time. Defaults to config value.

    Returns:
        str: Encoded JWT token.

    Examples:
        >>> token = create_access_token({"sub": "user@example.com", "user_id": 1})
        >>> print(token[:20])
        'eyJhbGciOiJIUzI1NiIs'
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    return encoded_jwt


def verify_access_token(token: str) -> Optional[dict]:
    """
    Verify and decode a JWT access token.

    Args:
        token (str): JWT token string to verify.

    Returns:
        Optional[dict]: Decoded token payload if valid, None if invalid.

    Raises:
        JWTError: If token is invalid or expired.

    Examples:
        >>> payload = verify_access_token(token)
        >>> if payload:
        >>>     user_id = payload.get("user_id")
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


def generate_api_key() -> str:
    """
    Generate a random API key with configured prefix.

    Returns:
        str: API key string (e.g., "sk_live_abc123def456...").

    Examples:
        >>> key = generate_api_key()
        >>> print(key.startswith("sk_live_"))
        True
        >>> print(len(key))
        48
    """
    random_part = secrets.token_urlsafe(32)  # 32 bytes = ~43 chars in base64
    return f"{settings.API_KEY_PREFIX}{random_part}"


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key for secure storage using SHA-256.

    Args:
        api_key (str): Plain text API key to hash.

    Returns:
        str: Hexadecimal hash of the API key.

    Examples:
        >>> key_hash = hash_api_key("sk_live_abc123")
        >>> print(len(key_hash))
        64

    Notes:
        - Never store API keys in plaintext.
        - Use this hash for database storage and comparison.
    """
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """
    Verify a plain API key against its stored hash.

    Args:
        plain_key (str): Plain text API key from request.
        hashed_key (str): Hashed API key from database.

    Returns:
        bool: True if keys match, False otherwise.

    Examples:
        >>> is_valid = verify_api_key("sk_live_abc123", stored_hash)
        >>> if is_valid:
        >>>     print("Key is valid")
    """
    computed_hash = hash_api_key(plain_key)
    return hmac.compare_digest(computed_hash, hashed_key)


def parse_expiry_to_datetime(expiry: str) -> datetime:
    """
    Convert expiry string to datetime object.

    Args:
        expiry (str): Expiry string in format: "1H", "1D", "1M", "1Y".

    Returns:
        datetime: Expiration datetime in UTC.

    Raises:
        ValueError: If expiry format is invalid.

    Examples:
        >>> expires_at = parse_expiry_to_datetime("1M")
        >>> print(expires_at > datetime.now(timezone.utc))
        True
        >>> parse_expiry_to_datetime("2W")  # Invalid
        ValueError: Invalid expiry format. Use: 1H, 1D, 1M, 1Y
    """
    valid_formats = {"H": "hours", "D": "days", "M": "months", "Y": "years"}
    
    if len(expiry) < 2 or expiry[-1] not in valid_formats:
        raise ValueError("Invalid expiry format. Use: 1H, 1D, 1M, 1Y")
    
    try:
        quantity = int(expiry[:-1])
        unit = expiry[-1]
    except ValueError:
        raise ValueError("Invalid expiry format. Use: 1H, 1D, 1M, 1Y")
    
    now = datetime.now(timezone.utc)
    
    if unit == "H":
        return now + timedelta(hours=quantity)
    elif unit == "D":
        return now + timedelta(days=quantity)
    elif unit == "M":
        return now + timedelta(days=quantity * 30)  # Approximate month
    elif unit == "Y":
        return now + timedelta(days=quantity * 365)  # Approximate year
    
    raise ValueError("Invalid expiry format. Use: 1H, 1D, 1M, 1Y")


def verify_paystack_signature(payload: bytes, signature: str) -> bool:
    """
    Verify Paystack webhook signature.

    Args:
        payload (bytes): Raw request body bytes.
        signature (str): x-paystack-signature header value.

    Returns:
        bool: True if signature is valid, False otherwise.

    Examples:
        >>> is_valid = verify_paystack_signature(request.body, request.headers["x-paystack-signature"])
        >>> if not is_valid:
        >>>     raise HTTPException(status_code=400, detail="Invalid signature")

    Notes:
        - Always validate webhooks to prevent spoofing attacks.
        - Use constant-time comparison to prevent timing attacks.
    """
    computed_signature = hmac.new(
        settings.PAYSTACK_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha512
    ).hexdigest()
    
    return hmac.compare_digest(computed_signature, signature)