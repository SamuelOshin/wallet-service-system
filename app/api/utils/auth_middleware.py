"""
Authentication middleware for JWT and API key validation.

Provides dependency injection functions for FastAPI routes to:
- Validate JWT tokens
- Validate API keys
- Check API key permissions
"""

from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.api.core.database import get_db
from app.api.models.user import APIKey, User
from app.api.services.api_key_service import APIKeyService
from app.api.utils.security import verify_access_token

# HTTP Bearer scheme for JWT
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user_from_jwt(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    Extract and validate JWT token, return user if valid.

    Args:
        credentials (Optional[HTTPAuthorizationCredentials]): Bearer token from header.
        db (Session): Database session.

    Returns:
        Optional[User]: Authenticated user or None if no valid JWT.

    Examples:
        >>> # In a route:
        >>> @router.get("/profile")
        >>> async def get_profile(user: User = Depends(get_current_user_from_jwt)):
        >>>     return user

    Notes:
        - Does not raise error if no JWT present (allows API key fallback).
        - Returns None if JWT is invalid or user not found.
    """
    if not credentials:
        return None

    token = credentials.credentials
    payload = verify_access_token(token)

    if not payload:
        return None

    user_id = payload.get("user_id")
    if not user_id:
        return None

    user = db.query(User).filter(User.id == user_id).first()
    return user


async def get_current_user_from_api_key(
    x_api_key: Optional[str] = Header(None, alias="x-api-key"),
    db: Session = Depends(get_db),
) -> Optional[tuple[User, APIKey]]:
    """
    Extract and validate API key, return user and key if valid.

    Args:
        x_api_key (Optional[str]): API key from x-api-key header.
        db (Session): Database session.

    Returns:
        Optional[tuple[User, APIKey]]: User and API key, or None if invalid.

    Examples:
        >>> # In a route:
        >>> @router.get("/data")
        >>> async def get_data(auth: tuple = Depends(get_current_user_from_api_key)):
        >>>     user, api_key = auth
        >>>     return {"user": user.email}

    Notes:
        - Does not raise error if no API key present.
        - Returns None if API key is invalid, expired, or revoked.
    """
    if not x_api_key:
        return None

    api_key = APIKeyService.validate_api_key(db, x_api_key)

    if not api_key:
        return None

    user = db.query(User).filter(User.id == api_key.user_id).first()
    
    if not user:
        return None

    return user, api_key


async def get_current_user(
    jwt_user: Optional[User] = Depends(get_current_user_from_jwt),
    api_key_auth: Optional[tuple[User, APIKey]] = Depends(get_current_user_from_api_key),
) -> tuple[User, Optional[APIKey]]:
    """
    Get authenticated user from either JWT or API key.

    Args:
        jwt_user (Optional[User]): User from JWT token.
        api_key_auth (Optional[tuple]): User and API key from x-api-key header.

    Returns:
        tuple[User, Optional[APIKey]]: Authenticated user and API key (if used).

    Raises:
        HTTPException: 401 if neither JWT nor valid API key provided.

    Examples:
        >>> @router.get("/wallet/balance")
        >>> async def get_balance(auth: tuple = Depends(get_current_user)):
        >>>     user, api_key = auth
        >>>     if api_key:
        >>>         print("Authenticated with API key")
        >>>     return {"balance": user.wallet.balance}

    Notes:
        - Prioritizes JWT if both JWT and API key are present.
        - Raises 401 if no valid authentication method found.
    """
    # Try JWT first
    if jwt_user:
        return jwt_user, None

    # Try API key
    if api_key_auth:
        user, api_key = api_key_auth
        return user, api_key

    # No valid authentication
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide valid JWT token or API key.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_permission(required_permission: str):
    """
    Dependency factory to check API key permissions.

    Args:
        required_permission (str): Required permission ('deposit', 'transfer', 'read').

    Returns:
        Callable: Dependency function that validates permission.

    Examples:
        >>> @router.post("/wallet/transfer")
        >>> async def transfer(
        >>>     auth: tuple = Depends(get_current_user),
        >>>     _: None = Depends(require_permission("transfer"))
        >>> ):
        >>>     user, api_key = auth
        >>>     # Perform transfer
        >>>     pass

    Raises:
        HTTPException: 403 if API key lacks required permission.

    Notes:
        - JWT users always have all permissions.
        - Only checks permission if authenticated with API key.
    """
    async def permission_checker(
        auth: tuple[User, Optional[APIKey]] = Depends(get_current_user),
    ):
        user, api_key = auth

        # JWT users have all permissions
        if api_key is None:
            return

        # Check API key permission
        if not APIKeyService.check_permission(api_key, required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"API key lacks '{required_permission}' permission",
            )

    return permission_checker