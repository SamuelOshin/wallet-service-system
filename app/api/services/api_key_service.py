"""
API Key management service.

Handles:
- Creating API keys with permissions and expiry
- Validating API keys
- Revoking API keys
- Rolling over expired keys
"""

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.api.core.config import get_settings
from app.api.models.user import APIKey
from app.api.utils.security import (
    generate_api_key,
    hash_api_key,
    parse_expiry_to_datetime,
)

settings = get_settings()


class APIKeyService:
    """Service for managing API keys."""

    @staticmethod
    def count_active_keys(db: Session, user_id: int) -> int:
        """
        Count active (non-expired, non-revoked) API keys for a user.

        Args:
            db (Session): Database session.
            user_id (int): User ID.

        Returns:
            int: Number of active API keys.

        Examples:
            >>> count = APIKeyService.count_active_keys(db, user_id=1)
            >>> print(count)
            3
        """
        now = datetime.now(timezone.utc)
        return (
            db.query(APIKey)
            .filter(
                and_(
                    APIKey.user_id == user_id,
                    APIKey.is_revoked == False,
                    APIKey.expires_at > now,
                )
            )
            .count()
        )

    @staticmethod
    def create_api_key(
        db: Session, user_id: int, name: str, permissions: List[str], expiry: str
    ) -> tuple[APIKey, str]:
        """
        Create a new API key for a user.

        Args:
            db (Session): Database session.
            user_id (int): User ID.
            name (str): Human-readable key name.
            permissions (List[str]): List of permissions: ['deposit', 'transfer', 'read'].
            expiry (str): Expiry format: "1H", "1D", "1M", "1Y".

        Returns:
            tuple[APIKey, str]: Created API key object and plain text key.

        Raises:
            ValueError: If user has reached maximum API key limit.

        Examples:
            >>> api_key, plain_key = APIKeyService.create_api_key(
            >>>     db, user_id=1, name="trading-bot",
            >>>     permissions=["read", "deposit"], expiry="1M"
            >>> )
            >>> print(plain_key[:8])
            'sk_live_'

        Notes:
            - Returns plain text key only once (not stored).
            - Only hashed version is stored in database.
            - User can have maximum 5 active keys.
        """
        # Check key limit
        active_count = APIKeyService.count_active_keys(db, user_id)
        if active_count >= settings.MAX_API_KEYS_PER_USER:
            raise ValueError(
                f"Maximum {settings.MAX_API_KEYS_PER_USER} active API keys allowed per user"
            )

        # Generate API key
        plain_key = generate_api_key()
        key_hash = hash_api_key(plain_key)

        # Parse expiry
        expires_at = parse_expiry_to_datetime(expiry)

        # Create API key record
        api_key = APIKey(
            user_id=user_id,
            key_hash=key_hash,
            name=name,
            permissions=permissions,
            expires_at=expires_at,
            is_revoked=False,
        )

        db.add(api_key)
        db.commit()
        db.refresh(api_key)

        return api_key, plain_key

    @staticmethod
    def get_api_key_by_value(db: Session, plain_key: str) -> Optional[APIKey]:
        """
        Retrieve API key by its plain text value.

        Args:
            db (Session): Database session.
            plain_key (str): Plain text API key from request.

        Returns:
            Optional[APIKey]: API key object or None if not found.

        Examples:
            >>> api_key = APIKeyService.get_api_key_by_value(db, "sk_live_abc123")
            >>> if api_key and api_key.is_valid():
            >>>     print("Valid key")

        Notes:
            - Compares hash of plain_key with stored hashes.
            - Use constant-time comparison to prevent timing attacks.
        """
        key_hash = hash_api_key(plain_key)
        return db.query(APIKey).filter(APIKey.key_hash == key_hash).first()

    @staticmethod
    def validate_api_key(db: Session, plain_key: str) -> Optional[APIKey]:
        """
        Validate API key and check if it's active.

        Args:
            db (Session): Database session.
            plain_key (str): Plain text API key from request.

        Returns:
            Optional[APIKey]: Valid API key or None if invalid/expired/revoked.

        Examples:
            >>> api_key = APIKeyService.validate_api_key(db, request_key)
            >>> if not api_key:
            >>>     raise HTTPException(status_code=401, detail="Invalid API key")
        """
        api_key = APIKeyService.get_api_key_by_value(db, plain_key)

        if not api_key:
            return None

        if not api_key.is_valid():
            return None

        return api_key

    @staticmethod
    def revoke_api_key(db: Session, key_id: int, user_id: int) -> bool:
        """
        Revoke an API key.

        Args:
            db (Session): Database session.
            key_id (int): API key ID to revoke.
            user_id (int): User ID (for authorization check).

        Returns:
            bool: True if revoked successfully, False if not found or unauthorized.

        Examples:
            >>> success = APIKeyService.revoke_api_key(db, key_id=5, user_id=1)
            >>> print(success)
            True
        """
        api_key = (
            db.query(APIKey)
            .filter(and_(APIKey.id == key_id, APIKey.user_id == user_id))
            .first()
        )

        if not api_key:
            return False

        api_key.is_revoked = True
        db.commit()
        return True

    @staticmethod
    def rollover_expired_key(
        db: Session, expired_key_id: int, user_id: int, new_expiry: str
    ) -> tuple[APIKey, str]:
        """
        Create new API key using permissions from an expired key.

        Args:
            db (Session): Database session.
            expired_key_id (int): ID of expired key to rollover.
            user_id (int): User ID (for authorization check).
            new_expiry (str): New expiry format: "1H", "1D", "1M", "1Y".

        Returns:
            tuple[APIKey, str]: New API key object and plain text key.

        Raises:
            ValueError: If key not found, not expired, or not owned by user.

        Examples:
            >>> new_key, plain_key = APIKeyService.rollover_expired_key(
            >>>     db, expired_key_id=3, user_id=1, new_expiry="1M"
            >>> )
            >>> print(new_key.permissions)
            ['read', 'deposit']

        Notes:
            - Original key must be expired.
            - New key inherits same permissions.
            - Old key remains in database but is marked revoked.
        """
        # Get expired key
        expired_key = (
            db.query(APIKey)
            .filter(and_(APIKey.id == expired_key_id, APIKey.user_id == user_id))
            .first()
        )

        if not expired_key:
            raise ValueError("API key not found or unauthorized")

        # Check if key is actually expired
        now = datetime.now(timezone.utc)
        if expired_key.expires_at > now and not expired_key.is_revoked:
            raise ValueError("Can only rollover expired or revoked keys")

        # Mark old key as revoked (if not already)
        if not expired_key.is_revoked:
            expired_key.is_revoked = True

        # Create new key with same permissions
        new_key, plain_key = APIKeyService.create_api_key(
            db=db,
            user_id=user_id,
            name=expired_key.name,
            permissions=expired_key.permissions,
            expiry=new_expiry,
        )

        db.commit()
        return new_key, plain_key

    @staticmethod
    def list_user_keys(db: Session, user_id: int) -> List[APIKey]:
        """
        List all API keys for a user.

        Args:
            db (Session): Database session.
            user_id (int): User ID.

        Returns:
            List[APIKey]: List of user's API keys.

        Examples:
            >>> keys = APIKeyService.list_user_keys(db, user_id=1)
            >>> for key in keys:
            >>>     print(f"{key.name}: {'active' if key.is_valid() else 'inactive'}")
        """
        return (
            db.query(APIKey)
            .filter(APIKey.user_id == user_id)
            .order_by(APIKey.created_at.desc())
            .all()
        )

    @staticmethod
    def check_permission(api_key: APIKey, required_permission: str) -> bool:
        """
        Check if API key has a specific permission.

        Args:
            api_key (APIKey): API key object.
            required_permission (str): Permission to check ('deposit', 'transfer', 'read').

        Returns:
            bool: True if key has permission.

        Examples:
            >>> if APIKeyService.check_permission(api_key, "transfer"):
            >>>     # Allow transfer operation
            >>>     pass
        """
        return api_key.has_permission(required_permission)
