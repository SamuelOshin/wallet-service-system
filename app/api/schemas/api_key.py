"""
Pydantic schemas for API key management.

Defines schemas for:
- Creating API keys
- Rolling over expired keys
- API key responses
"""

from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict, Field, field_validator


class APIKeyCreateRequest(BaseModel):
    """
    Schema for creating a new API key.

    Attributes:
        name (str): Human-readable key name (e.g., "trading-bot").
        permissions (List[str]): List of permissions: 'deposit', 'transfer', 'read'.
        expiry (str): Expiry format: "1H", "1D", "1M", "1Y".

    Examples:
        >>> request = APIKeyCreateRequest(
        >>>     name="my-service",
        >>>     permissions=["read", "deposit"],
        >>>     expiry="1M"
        >>> )
    """

    name: str = Field(..., min_length=1, max_length=100, description="API key name")
    permissions: List[str] = Field(..., min_items=1, description="List of permissions")
    expiry: str = Field(
        ..., pattern=r"^\d+[HDMY]$", description="Expiry: 1H, 1D, 1M, 1Y"
    )

    @field_validator("permissions")
    @classmethod
    def validate_permissions(cls, v: List[str]) -> List[str]:
        """Ensure only valid permissions are provided."""
        valid_permissions = {"deposit", "transfer", "read"}
        for perm in v:
            if perm not in valid_permissions:
                raise ValueError(
                    f"Invalid permission: {perm}. Must be one of: {valid_permissions}"
                )
        # Remove duplicates
        return list(set(v))

    @field_validator("expiry")
    @classmethod
    def validate_expiry(cls, v: str) -> str:
        """Ensure expiry format is valid."""
        if not v or len(v) < 2:
            raise ValueError("Invalid expiry format. Use: 1H, 1D, 1M, 1Y")

        unit = v[-1]
        if unit not in ["H", "D", "M", "Y"]:
            raise ValueError(
                "Invalid expiry unit. Use: H (hour), D (day), M (month), Y (year)"
            )

        try:
            int(v[:-1])
        except ValueError:
            raise ValueError("Invalid expiry format. Use: 1H, 1D, 1M, 1Y")

        return v


class APIKeyResponse(BaseModel):
    """
    Schema for API key creation response.

    Attributes:
        api_key (str): The generated API key (shown only once).
        name (str): Key name.
        permissions (List[str]): Assigned permissions.
        expires_at (datetime): Expiration timestamp.
        created_at (datetime): Creation timestamp.

    Notes:
        - API key is shown only once during creation.
        - Store it securely; it cannot be retrieved later.
    """

    api_key: str
    name: str
    permissions: List[str]
    expires_at: datetime
    created_at: datetime


class APIKeyListItem(BaseModel):
    """
    Schema for individual API key in list (without showing the key).

    Attributes:
        id (int): Key ID.
        name (str): Key name.
        permissions (List[str]): Assigned permissions.
        expires_at (datetime): Expiration timestamp.
        is_revoked (bool): Whether key is revoked.
        created_at (datetime): Creation timestamp.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    permissions: List[str]
    expires_at: datetime
    is_revoked: bool
    created_at: datetime


class APIKeyRolloverRequest(BaseModel):
    """
    Schema for rolling over an expired API key.

    Attributes:
        expired_key_id (int): ID of the expired key to rollover.
        expiry (str): New expiry format: "1H", "1D", "1M", "1Y".

    Examples:
        >>> request = APIKeyRolloverRequest(expired_key_id=5, expiry="1M")
    """

    expired_key_id: int = Field(..., gt=0, description="ID of expired API key")
    expiry: str = Field(
        ..., pattern=r"^\d+[HDMY]$", description="New expiry: 1H, 1D, 1M, 1Y"
    )

    @field_validator("expiry")
    @classmethod
    def validate_expiry(cls, v: str) -> str:
        """Ensure expiry format is valid."""
        if not v or len(v) < 2:
            raise ValueError("Invalid expiry format. Use: 1H, 1D, 1M, 1Y")

        unit = v[-1]
        if unit not in ["H", "D", "M", "Y"]:
            raise ValueError(
                "Invalid expiry unit. Use: H (hour), D (day), M (month), Y (year)"
            )

        try:
            int(v[:-1])
        except ValueError:
            raise ValueError("Invalid expiry format. Use: 1H, 1D, 1M, 1Y")

        return v
