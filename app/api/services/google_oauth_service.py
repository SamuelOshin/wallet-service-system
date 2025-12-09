"""
Google OAuth authentication service.

Handles Google sign-in flow:
- Redirect to Google OAuth
- Exchange authorization code for user info
- Create/retrieve user and wallet
"""

from typing import Dict, Optional
from urllib.parse import urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.core.config import get_settings
from app.api.models.user import User, Wallet
from app.api.schemas.auth import UserCreate

settings = get_settings()


class GoogleAuthService:
    """Service for handling Google OAuth authentication."""

    GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

    @staticmethod
    def get_authorization_url(state: Optional[str] = None) -> str:
        """
        Generate Google OAuth authorization URL.

        Args:
            state (Optional[str]): CSRF protection state parameter.

        Returns:
            str: Google OAuth authorization URL.

        Examples:
            >>> url = GoogleAuthService.get_authorization_url()
            >>> print(url.startswith("https://accounts.google.com"))
            True
        """
        # Validate Google credentials
        if not settings.GOOGLE_CLIENT_ID or settings.GOOGLE_CLIENT_ID in (
            "your-google-client-id.apps.googleusercontent.com",
            "your-client-id.apps.googleusercontent.com",
        ) or settings.GOOGLE_CLIENT_ID.startswith("your-"):
            raise ValueError(
                "GOOGLE_CLIENT_ID is not configured. Please set your real Google OAuth client ID in .env or environment variables."
            )

        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "consent",
        }

        if state:
            params["state"] = state

        # Use URL encoding for safety
        query_string = urlencode(params)
        return f"{GoogleAuthService.GOOGLE_AUTH_URL}?{query_string}"

    @staticmethod
    async def exchange_code_for_token(code: str) -> Dict[str, str]:
        """
        Exchange Google authorization code for access token.

        Args:
            code (str): Authorization code from Google callback.

        Returns:
            Dict[str, str]: Token response containing access_token.

        Raises:
            httpx.HTTPStatusError: If token exchange fails.

        Examples:
            >>> token_data = await GoogleAuthService.exchange_code_for_token("auth_code_123")
            >>> print("access_token" in token_data)
            True
        """
        # Validate credentials
        if not settings.GOOGLE_CLIENT_SECRET or settings.GOOGLE_CLIENT_SECRET in (
            "your-google-client-secret",
            "your-client-secret",
        ) or settings.GOOGLE_CLIENT_SECRET.startswith("your-"):
            raise ValueError(
                "GOOGLE_CLIENT_SECRET is not configured. Please set your real Google OAuth client secret in .env or environment variables."
            )

        data = {
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(GoogleAuthService.GOOGLE_TOKEN_URL, data=data)
            response.raise_for_status()
            return response.json()

    @staticmethod
    async def get_user_info(access_token: str) -> Dict[str, str]:
        """
        Fetch user information from Google using access token.

        Args:
            access_token (str): Google access token.

        Returns:
            Dict[str, str]: User info containing email, name, and id.

        Raises:
            httpx.HTTPStatusError: If user info request fails.

        Examples:
            >>> user_info = await GoogleAuthService.get_user_info(access_token)
            >>> print(user_info["email"])
            'user@example.com'
        """
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient() as client:
            response = await client.get(GoogleAuthService.GOOGLE_USERINFO_URL, headers=headers)
            response.raise_for_status()
            return response.json()

    @staticmethod
    def get_or_create_user(db: Session, user_data: UserCreate) -> User:
        """
        Get existing user or create new user with wallet.

        Args:
            db (Session): Database session.
            user_data (UserCreate): User creation data from Google.

        Returns:
            User: Existing or newly created user with wallet.

        Examples:
            >>> user_data = UserCreate(email="john@example.com", google_id="123", name="John")
            >>> user = GoogleAuthService.get_or_create_user(db, user_data)
            >>> print(user.wallet.balance)
            0.00

        Notes:
            - Creates wallet automatically for new users.
            - Wallet number is a unique 13-digit string.
        """
        # Check if user exists
        user = db.query(User).filter(User.google_id == user_data.google_id).first()

        if user:
            return user

        # Generate unique wallet number first (before user creation)
        wallet_number = Wallet.generate_wallet_number()
        while db.query(Wallet).filter(Wallet.wallet_number == wallet_number).first():
            wallet_number = Wallet.generate_wallet_number()

        # Create new user and wallet together
        new_user = User(
            email=user_data.email,
            google_id=user_data.google_id,
            name=user_data.name,
        )

        db.add(new_user)
        db.flush()  # Get the user ID

        # Create wallet with the user ID
        wallet = Wallet(
            user_id=new_user.id,
            wallet_number=wallet_number,
            balance=0.00,
        )

        db.add(wallet)

        return new_user