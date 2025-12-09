"""
Base model and common mixins for all database models.

Provides timestamp tracking and declarative base for SQLAlchemy ORM models.
"""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class TimestampMixin:
    """
    Mixin that adds created_at and updated_at timestamp columns.

    Attributes:
        created_at (datetime): Record creation timestamp (auto-set).
        updated_at (datetime): Record last update timestamp (auto-updated).

    Examples:
        >>> class User(Base, TimestampMixin):
        >>>     __tablename__ = "users"
        >>>     id = Column(Integer, primary_key=True)
    """

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )