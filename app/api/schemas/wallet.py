"""
Pydantic schemas for wallet-related requests and responses.

Defines schemas for:
- Wallet deposits (Paystack)
- Wallet transfers
- Wallet balance
- Transaction history
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DepositRequest(BaseModel):
    """
    Schema for initiating a wallet deposit via Paystack.

    Attributes:
        amount (Decimal): Amount to deposit (must be positive).

    Examples:
        >>> deposit = DepositRequest(amount=5000.00)
    """

    amount: Decimal = Field(
        ..., gt=0, description="Deposit amount (must be greater than 0)"
    )

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        """Ensure amount has at most 2 decimal places."""
        if v.as_tuple().exponent < -2:
            raise ValueError("Amount cannot have more than 2 decimal places")
        return v


class DepositResponse(BaseModel):
    """
    Schema for deposit initialization response.

    Attributes:
        reference (str): Unique transaction reference.
        authorization_url (str): Paystack payment URL for user.
        amount (Decimal): Deposit amount.
    """

    reference: str
    authorization_url: str
    amount: Decimal


class TransferRequest(BaseModel):
    """
    Schema for wallet-to-wallet transfer request.

    Attributes:
        wallet_number (str): Recipient's 13-digit wallet number.
        amount (Decimal): Transfer amount (must be positive).
        idempotency_key (str, optional): Unique key to prevent duplicate transfers.

    Examples:
        >>> transfer = TransferRequest(
        >>>     wallet_number="1234567890123",
        >>>     amount=3000.00,
        >>>     idempotency_key="uuid-1234"
        >>> )
    """

    wallet_number: str = Field(
        ..., min_length=13, max_length=13, description="Recipient's wallet number"
    )
    amount: Decimal = Field(
        ..., gt=0, description="Transfer amount (must be greater than 0)"
    )
    idempotency_key: Optional[str] = Field(
        None, description="Unique key to prevent duplicate transfers"
    )

    @field_validator("wallet_number")
    @classmethod
    def validate_wallet_number(cls, v: str) -> str:
        """Ensure wallet number contains only digits."""
        if not v.isdigit():
            raise ValueError("Wallet number must contain only digits")
        return v

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        """Ensure amount has at most 2 decimal places."""
        if v.as_tuple().exponent < -2:
            raise ValueError("Amount cannot have more than 2 decimal places")
        return v


class TransferResponse(BaseModel):
    """
    Schema for successful transfer response.

    Attributes:
        status (str): Transfer status (always "success" for successful transfers).
        message (str): Human-readable result message.
        reference (str): Unique transaction reference.
        amount (Decimal): Transfer amount.
        recipient_wallet (str): Recipient's wallet number.
    """

    status: str = "success"
    message: str
    reference: str
    amount: Decimal
    recipient_wallet: str


class WalletBalanceResponse(BaseModel):
    """
    Schema for wallet balance response.

    Attributes:
        balance (Decimal): Current wallet balance.
        wallet_number (str): User's wallet number.
    """

    balance: Decimal
    wallet_number: str


class TransactionResponse(BaseModel):
    """
    Schema for individual transaction in history.

    Attributes:
        id (int): Transaction ID.
        type (str): Transaction type: 'deposit', 'transfer_in', 'transfer_out'.
        amount (Decimal): Transaction amount.
        status (str): Transaction status: 'pending', 'success', 'failed'.
        reference (str): Unique transaction reference.
        metadata (Dict[str, Any]): Additional transaction information.
        created_at (datetime): Transaction timestamp.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    amount: Decimal
    status: str
    reference: str
    metadata: Dict[str, Any] = Field(default_factory=dict, alias="extra_data")
    created_at: datetime


class TransactionHistoryResponse(BaseModel):
    """
    Schema for transaction history list response.

    Attributes:
        transactions (List[TransactionResponse]): List of user transactions.
        total (int): Total number of transactions.
    """

    transactions: List[TransactionResponse]
    total: int


class DepositStatusResponse(BaseModel):
    """
    Schema for checking deposit status (manual verification).

    Attributes:
        reference (str): Transaction reference.
        status (str): Current status: 'pending', 'success', 'failed'.
        amount (Decimal): Deposit amount.
        created_at (datetime): Transaction creation time.



    Notes:
        - This endpoint does NOT credit wallets.
        - Only webhooks should credit wallets.
    """

    reference: str
    status: str
    amount: Decimal
    created_at: datetime


class UserDetailsResponse(BaseModel):
    """
    Schema for user profile and wallet details.

    Attributes:
        name (str): User's full name.
        email (str): User's email address.
        wallet_number (str): User's 13-digit wallet number.
        balance (Decimal): Current wallet balance.

    Examples:
        >>> details = UserDetailsResponse(
        >>>     name="John Doe",
        >>>     email="john@example.com",
        >>>     wallet_number="1234567890123",
        >>>     balance=50000.00
        >>> )
    """

    name: str
    email: str
    wallet_number: str
    balance: Decimal
