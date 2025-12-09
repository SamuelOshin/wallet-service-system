"""
Database models for the wallet service.

This module defines all SQLAlchemy ORM models:
- User: User accounts from Google OAuth
- Wallet: User wallet with balance and unique wallet number
- Transaction: Deposit, transfer_in, transfer_out records
- APIKey: Service-to-service authentication keys
"""

import secrets
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.api.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    """
    User model representing authenticated users via Google OAuth.

    Attributes:
        id (int): Primary key.
        email (str): User's email from Google (unique).
        google_id (str): Google's unique user identifier.
        name (str): User's full name.
        wallet (Wallet): One-to-one relationship with user's wallet.
        api_keys (List[APIKey]): User's generated API keys.

    Examples:
        >>> user = User(email="john@example.com", google_id="123456", name="John Doe")
        >>> db.add(user)
        >>> db.commit()
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    google_id = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)

    # Relationships
    wallet = relationship(
        "Wallet", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    api_keys = relationship(
        "APIKey", back_populates="user", cascade="all, delete-orphan"
    )


class Wallet(Base, TimestampMixin):
    """
    Wallet model for storing user balances.

    Attributes:
        id (int): Primary key.
        user_id (int): Foreign key to users table.
        wallet_number (str): Unique 13-digit wallet identifier.
        balance (Decimal): Current wallet balance (default 0.00).
        user (User): Relationship to wallet owner.
        transactions (List[Transaction]): All transactions for this wallet.

    Examples:
        >>> wallet = Wallet(user_id=1, wallet_number="4566678954356", balance=0)
        >>> db.add(wallet)
        >>> db.commit()
    """

    __tablename__ = "wallets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    wallet_number = Column(String(13), unique=True, nullable=False, index=True)
    balance = Column(Numeric(15, 2), default=0.00, nullable=False)

    # Relationships
    user = relationship("User", back_populates="wallet")
    transactions = relationship(
        "Transaction", back_populates="wallet", cascade="all, delete-orphan"
    )

    @staticmethod
    def generate_wallet_number() -> str:
        """
        Generate a unique 13-digit wallet number.

        Returns:
            str: Random 13-digit wallet number.

        Examples:
            >>> wallet_num = Wallet.generate_wallet_number()
            >>> print(len(wallet_num))
            13
        """
        return "".join([str(secrets.randbelow(10)) for _ in range(13)])


class Transaction(Base, TimestampMixin):
    """
    Transaction model for tracking all wallet activities.

    Attributes:
        id (int): Primary key.
        wallet_id (int): Foreign key to wallets table.
        type (str): Transaction type: 'deposit', 'transfer_in', 'transfer_out'.
        amount (Decimal): Transaction amount.
        reference (str): Unique transaction reference (especially for Paystack).
        status (str): Transaction status: 'pending', 'success', 'failed'.
        extra_data (dict): Additional transaction data (JSON).
        wallet (Wallet): Relationship to associated wallet.

    Examples:
        >>> txn = Transaction(
        >>>     wallet_id=1,
        >>>     type="deposit",
        >>>     amount=5000.00,
        >>>     reference="DEP_123456",
        >>>     status="pending"
        >>> )
    """

    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    wallet_id = Column(
        Integer, ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False
    )
    type = Column(
        Enum("deposit", "transfer_in", "transfer_out", name="transaction_type"),
        nullable=False,
    )
    amount = Column(Numeric(15, 2), nullable=False)
    reference = Column(String, unique=True, nullable=False, index=True)
    status = Column(
        Enum("pending", "success", "failed", name="transaction_status"), nullable=False
    )
    extra_data = Column(JSON, default=dict)

    # Relationships
    wallet = relationship("Wallet", back_populates="transactions")

    # Indexes
    __table_args__ = (Index("idx_wallet_created", "wallet_id", "created_at"),)


class APIKey(Base, TimestampMixin):
    """
    API Key model for service-to-service authentication.

    Attributes:
        id (int): Primary key.
        user_id (int): Foreign key to users table (key owner).
        key_hash (str): Hashed API key value (never store plaintext).
        name (str): Human-readable key name (e.g., "trading-bot").
        permissions (list): Array of permission strings: ['deposit', 'transfer', 'read'].
        expires_at (datetime): Key expiration timestamp.
        is_revoked (bool): Whether key has been manually revoked.
        user (User): Relationship to key owner.

    Examples:
        >>> from app.api.utils.security import hash_api_key
        >>> key_hash = hash_api_key("sk_live_abc123")
        >>> api_key = APIKey(
        >>>     user_id=1,
        >>>     key_hash=key_hash,
        >>>     name="my-service",
        >>>     permissions=["read", "deposit"],
        >>>     expires_at=datetime.now(timezone.utc) + timedelta(days=30)
        >>> )
    """

    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    key_hash = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    permissions = Column(JSON, nullable=False)  # ["deposit", "transfer", "read"]
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)

    # Relationships
    user = relationship("User", back_populates="api_keys")

    # Indexes
    __table_args__ = (
        Index("idx_user_active_keys", "user_id", "is_revoked", "expires_at"),
        UniqueConstraint("user_id", "name", name="uq_user_key_name"),
    )

    def is_valid(self) -> bool:
        """
        Check if API key is currently valid (not expired and not revoked).

        Returns:
            bool: True if key is valid, False otherwise.

        Examples:
            >>> if api_key.is_valid():
            >>>     print("Key is active")
        """
        now = datetime.now(timezone.utc)
        return not self.is_revoked and self.expires_at > now

    def has_permission(self, permission: str) -> bool:
        """
        Check if API key has a specific permission.

        Args:
            permission (str): Permission to check ('deposit', 'transfer', 'read').

        Returns:
            bool: True if key has the permission.

        Examples:
            >>> if api_key.has_permission("transfer"):
            >>>     # Allow transfer operation
            >>>     pass
        """
        return permission in self.permissions


class IdempotencyKey(Base, TimestampMixin):
    """
    Model for storing used idempotency keys to prevent duplicate operations.

    Attributes:
        id (int): Primary key.
        key (str): The idempotency key (unique).
        operation (str): Type of operation ('transfer', 'deposit', etc.).
        user_id (int): User who initiated the operation.

    Examples:
        >>> key = IdempotencyKey(key="uuid-123", operation="transfer", user_id=1)
        >>> db.add(key)
        >>> db.commit()
    """

    __tablename__ = "idempotency_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(255), nullable=False, unique=True, index=True)
    operation = Column(String(50), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Relationship
    user = relationship("User", backref="idempotency_keys")

    __table_args__ = (
        Index("ix_idempotency_keys_key_operation", "key", "operation"),
    )
