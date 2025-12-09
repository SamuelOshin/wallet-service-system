"""
Authentication routes for Google OAuth.

Endpoints:
- GET /auth/google: Redirect to Google sign-in
- GET /auth/google/callback: Handle OAuth callback
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.core.config import get_settings
from app.api.core.database import get_db
from app.api.schemas.auth import UserCreate
from app.api.services.google_oauth_service import GoogleAuthService
from app.api.utils.response_payload import auth_response, error_response
from app.api.utils.security import create_access_token
from app.api.routes.docs.auth_docs import (
    google_login_responses,
    google_callback_responses,
)

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/google", responses=google_login_responses)
async def google_login():
    """
    Initiate Google OAuth sign-in flow.

    Returns:
        RedirectResponse: Redirects user to Google sign-in page.

    Examples:
        >>> # User visits: GET /auth/google
        >>> # Gets redirected to: https://accounts.google.com/o/oauth2/v2/auth?...

    Notes:
        - User will be prompted to sign in with Google.
        - After authentication, Google redirects to /auth/google/callback.
    """
    auth_url = GoogleAuthService.get_authorization_url()
    return RedirectResponse(url=auth_url)


@router.get("/google/callback", responses=google_callback_responses)
async def google_callback(
    code: str = Query(..., description="Authorization code from Google"),
    db: Session = Depends(get_db),
):
    """
    Handle Google OAuth callback.

    Creates or retrieves user, generates JWT token.

    Args:
        code (str): Authorization code from Google.
        db (Session): Database session.

    Returns:
        JSONResponse: Standard auth response with JWT token and user data.

    Raises:
        HTTPException: 400 if code exchange fails or user info retrieval fails.

    Examples:
        >>> # Google redirects to: GET /auth/google/callback?code=abc123
        >>> # Response:
        >>> {
        >>>   "status": "SUCCESS",
        >>>   "status_code": 200,
        >>>   "message": "Authentication successful",
        >>>   "data": {
        >>>     "access_token": "eyJhbGc...",
        >>>     "user": {
        >>>       "id": 1,
        >>>       "email": "user@example.com",
        >>>       "name": "John Doe",
        >>>       "wallet_number": "1234567890123"
        >>>     }
        >>>   }
        >>> }

    Notes:
        - Creates user and wallet if first time sign-in.
        - Returns JWT token for subsequent API requests.
    """
    try:
        # Exchange code for access token
        token_data = await GoogleAuthService.exchange_code_for_token(code)
        access_token = token_data.get("access_token")

        if not access_token:
            return error_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Failed to obtain access token from Google",
                error="GOOGLE_AUTH_ERROR",
            )

        
        user_info = await GoogleAuthService.get_user_info(access_token)

       
        user_data = UserCreate(
            email=user_info["email"],
            google_id=user_info["id"],
            name=user_info.get("name", user_info["email"]),
        )

        user = GoogleAuthService.get_or_create_user(db, user_data)

       
        jwt_token = create_access_token(
            data={"sub": user.email, "user_id": user.id}
        )

        user_response = {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "wallet_number": user.wallet.wallet_number if user.wallet else None,
        }

        return auth_response(
            status_code=status.HTTP_200_OK,
            message="Authentication successful",
            access_token=jwt_token,
            data={"user": user_response},
        )

    except Exception as e:
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Authentication failed",
            error="GOOGLE_AUTH_ERROR",
            errors={"detail": [str(e)]},
        )