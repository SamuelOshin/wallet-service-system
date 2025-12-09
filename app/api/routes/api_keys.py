"""
API Key management routes.

Endpoints:
- POST /keys/create: Create new API key
- POST /keys/rollover: Rollover expired key
- GET /keys: List user's API keys
- DELETE /keys/{key_id}: Revoke API key
"""

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from app.api.core.database import get_db
from app.api.models.user import APIKey, User
from app.api.schemas.api_key import (
    APIKeyCreateRequest,
    APIKeyListItem,
    APIKeyResponse,
    APIKeyRolloverRequest,
)
from app.api.services.api_key_service import APIKeyService
from app.api.utils.auth_middleware import get_current_user
from app.api.utils.response_payload import error_response, success_response
from app.api.routes.docs.api_keys_docs import (
    create_api_key_responses,
    rollover_api_key_responses,
    list_api_keys_responses,
    revoke_api_key_responses,
)

router = APIRouter(prefix="/keys", tags=["API Keys"])


@router.post("/create", status_code=status.HTTP_201_CREATED, responses=create_api_key_responses)
async def create_api_key(
    request: APIKeyCreateRequest,
    auth: tuple[User, APIKey | None] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new API key with specific permissions.

    Args:
        request (APIKeyCreateRequest): Key creation request with name, permissions, expiry.
        auth (tuple): Authenticated user and optional API key.
        db (Session): Database session.

    Returns:
        JSONResponse: Success response with API key details.

    Raises:
        HTTPException: 400 if maximum keys reached or invalid expiry format.

    Examples:
        >>> # Request:
        >>> POST /keys/create
        >>> {
        >>>   "name": "trading-bot",
        >>>   "permissions": ["read", "deposit"],
        >>>   "expiry": "1M"
        >>> }
        >>> # Response:
        >>> {
        >>>   "status": "SUCCESS",
        >>>   "status_code": 201,
        >>>   "message": "API key created successfully",
        >>>   "data": {
        >>>     "api_key": "sk_live_abc123...",
        >>>     "name": "trading-bot",
        >>>     "permissions": ["read", "deposit"],
        >>>     "expires_at": "2025-02-09T12:00:00Z"
        >>>   }
        >>> }

    Notes:
        - API key is shown only once.
        - Store it securely; cannot be retrieved later.
        - Maximum 5 active keys per user.
    """
    user, _ = auth

    try:
        api_key, plain_key = APIKeyService.create_api_key(
            db=db,
            user_id=user.id,
            name=request.name,
            permissions=request.permissions,
            expiry=request.expiry,
        )

        response_data = {
            "api_key": plain_key,
            "name": api_key.name,
            "permissions": api_key.permissions,
            "expires_at": api_key.expires_at.isoformat(),
            "created_at": api_key.created_at.isoformat(),
        }

        return success_response(
            status_code=status.HTTP_201_CREATED,
            message="API key created successfully",
            data=response_data,
        )

    except ValueError as e:
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=str(e),
            error="API_KEY_CREATION_ERROR",
        )


@router.post("/rollover", responses=rollover_api_key_responses)
async def rollover_api_key(
    request: APIKeyRolloverRequest,
    auth: tuple[User, APIKey | None] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create new API key from an expired key with same permissions.

    Args:
        request (APIKeyRolloverRequest): Rollover request with expired key ID and new expiry.
        auth (tuple): Authenticated user and optional API key.
        db (Session): Database session.

    Returns:
        JSONResponse: Success response with new API key details.

    Raises:
        HTTPException: 400 if key not found, not expired, or unauthorized.

    Examples:
        >>> # Request:
        >>> POST /keys/rollover
        >>> {
        >>>   "expired_key_id": 5,
        >>>   "expiry": "1M"
        >>> }
        >>> # Response:
        >>> {
        >>>   "status": "SUCCESS",
        >>>   "status_code": 201,
        >>>   "message": "API key rolled over successfully",
        >>>   "data": {
        >>>     "api_key": "sk_live_xyz789...",
        >>>     "name": "trading-bot",
        >>>     "permissions": ["read", "deposit"],
        >>>     "expires_at": "2025-02-09T12:00:00Z"
        >>>   }
        >>> }

    Notes:
        - Original key must be expired or revoked.
        - New key inherits same permissions and name.
        - Old key is marked as revoked.
    """
    user, _ = auth

    try:
        new_key, plain_key = APIKeyService.rollover_expired_key(
            db=db,
            expired_key_id=request.expired_key_id,
            user_id=user.id,
            new_expiry=request.expiry,
        )

        response_data = {
            "api_key": plain_key,
            "name": new_key.name,
            "permissions": new_key.permissions,
            "expires_at": new_key.expires_at.isoformat(),
            "created_at": new_key.created_at.isoformat(),
        }

        return success_response(
            status_code=status.HTTP_201_CREATED,
            message="API key rolled over successfully",
            data=response_data,
        )

    except ValueError as e:
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=str(e),
            error="API_KEY_ROLLOVER_ERROR",
        )


@router.get("", responses=list_api_keys_responses)
async def list_api_keys(
    auth: tuple[User, APIKey | None] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all API keys for authenticated user.

    Args:
        auth (tuple): Authenticated user and optional API key.
        db (Session): Database session.

    Returns:
        JSONResponse: Success response with list of API keys.

    Examples:
        >>> # Request: GET /keys
        >>> # Response:
        >>> {
        >>>   "status": "SUCCESS",
        >>>   "status_code": 200,
        >>>   "message": "API keys retrieved successfully",
        >>>   "data": {
        >>>     "keys": [
        >>>       {
        >>>         "id": 1,
        >>>         "name": "trading-bot",
        >>>         "permissions": ["read", "deposit"],
        >>>         "expires_at": "2025-02-09T12:00:00Z",
        >>>         "is_revoked": false,
        >>>         "created_at": "2025-01-09T12:00:00Z"
        >>>       }
        >>>     ],
        >>>     "total": 1
        >>>   }
        >>> }

    Notes:
        - Does not show actual API key values.
        - Shows all keys (active, expired, and revoked).
    """
    user, _ = auth

    keys = APIKeyService.list_user_keys(db, user.id)

    keys_data = [
        {
            "id": key.id,
            "name": key.name,
            "permissions": key.permissions,
            "expires_at": key.expires_at.isoformat(),
            "is_revoked": key.is_revoked,
            "created_at": key.created_at.isoformat(),
        }
        for key in keys
    ]

    return success_response(
        status_code=status.HTTP_200_OK,
        message="API keys retrieved successfully",
        data={"keys": keys_data, "total": len(keys_data)},
    )


@router.delete("/{key_id}", responses=revoke_api_key_responses)
async def revoke_api_key(
    key_id: int = Path(..., description="API key ID to revoke"),
    auth: tuple[User, APIKey | None] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Revoke an API key.

    Args:
        key_id (int): ID of API key to revoke.
        auth (tuple): Authenticated user and optional API key.
        db (Session): Database session.

    Returns:
        JSONResponse: Success response confirming revocation.

    Raises:
        HTTPException: 404 if key not found or unauthorized.

    Examples:
        >>> # Request: DELETE /keys/5
        >>> # Response:
        >>> {
        >>>   "status": "SUCCESS",
        >>>   "status_code": 200,
        >>>   "message": "API key revoked successfully",
        >>>   "data": {}
        >>> }

    Notes:
        - Revoked keys cannot be used for authentication.
        - Revoked keys remain in database for audit purposes.
    """
    user, _ = auth

    success = APIKeyService.revoke_api_key(db, key_id, user.id)

    if not success:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="API key not found or unauthorized",
            error="API_KEY_NOT_FOUND",
        )

    return success_response(
        status_code=status.HTTP_200_OK,
        message="API key revoked successfully",
        data={},
    )