"""
Pydantic schemas for authentication and user-related requests/responses.

Defines request and response models for:
- Google OAuth callbacks
- User information
- JWT token responses
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr


class UserBase(BaseModel):
    """
    Base user schema with common fields.

    Attributes:
        email (EmailStr): User's email address.
        name (str): User's full name.
    """

    email: EmailStr
    name: str


class UserCreate(UserBase):
    """
    Schema for creating a new user.

    Attributes:
        google_id (str): Google's unique user identifier.
    """

    google_id: str


class UserResponse(UserBase):
    """
    Schema for user data in responses.

    Attributes:
        id (int): User's database ID.
        wallet_number (Optional[str]): User's wallet number if wallet exists.
        created_at (datetime): Account creation timestamp.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    wallet_number: Optional[str] = None
    created_at: datetime


class TokenResponse(BaseModel):
    """
    Schema for JWT token response after authentication.

    Attributes:
        access_token (str): JWT token string.
        token_type (str): Token type (always "bearer").
    """

    access_token: str
    token_type: str = "bearer"


class GoogleCallbackData(BaseModel):
    """
    Schema for Google OAuth callback data.

    Attributes:
        code (str): Authorization code from Google.
        state (Optional[str]): CSRF protection state parameter.
    """

    code: str
    state: Optional[str] = None
