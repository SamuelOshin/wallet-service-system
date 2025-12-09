"""
Database connection and session management.

Provides SQLAlchemy engine, session maker, and dependency injection for FastAPI routes.
"""

import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.api.core.config import get_settings

settings = get_settings()


def get_db_url(test_mode: bool = False, sync: bool = False) -> str:
    """
    Constructs and returns the database URL for SQLAlchemy engines.

    Args:
        test_mode (bool): If True, uses test database.
        sync (bool): If True, returns sync driver URL (for Celery tasks).

    Returns:
        str: Database connection URL.

    Examples:
        >>> url = get_db_url()
        >>> print(url)
        'postgresql://user:pass@localhost:5432/wallet_service'
    """
    base_dir = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )

    # SQLite for testing or if explicitly configured
    if test_mode:
        return f"sqlite:///{base_dir}/test.db"

    # PostgreSQL (synchronous driver)
    db_url = settings.DATABASE_URL

    # If DATABASE_URL contains async driver, convert to sync
    if "postgresql+asyncpg://" in db_url:
        return db_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    elif "postgresql://" in db_url:
        return db_url

    # Fallback
    return db_url


# Sync engine for FastAPI endpoints
DATABASE_URL = get_db_url()

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before using
    echo=settings.DEBUG,  # Log SQL queries in debug mode
    future=True,
)

# Sync session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """
    Create and yield a database session for dependency injection.

    Yields:
        Session: SQLAlchemy database session.

    Examples:
        >>> # In a FastAPI route
        >>> @app.get("/users")
        >>> async def get_users(db: Session = Depends(get_db)):
        >>>     users = db.query(User).all()
        >>>     return users

    Notes:
        - Session is automatically closed after the request completes.
        - Use this as a FastAPI dependency.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
