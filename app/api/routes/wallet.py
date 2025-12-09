"""
Wallet operation routes.

Endpoints:
- POST /wallet/deposit: Initialize Paystack deposit
- POST /wallet/paystack/webhook: Handle Paystack webhooks
- GET /wallet/deposit/{reference}/status: Check deposit status
- GET /wallet/balance: Get wallet balance
- POST /wallet/transfer: Transfer to another wallet
- GET /wallet/transactions: Get transaction history
"""

from decimal import Decimal

from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.orm import Session

from app.api.core.database import get_db
from app.api.models.user import APIKey, User
from app.api.schemas.wallet import (
    DepositRequest,
    DepositStatusResponse,
    TransactionHistoryResponse,
    TransactionResponse,
    TransferRequest,
    WalletBalanceResponse,
)
from app.api.services.wallet_service import WalletService
from app.api.utils.auth_middleware import get_current_user, require_permission
from app.api.utils.response_payload import error_response, success_response
from app.api.utils.security import verify_paystack_signature
from app.api.routes.docs.wallet_docs import (
    deposit_funds_responses,
    paystack_webhook_responses,
    check_deposit_status_responses,
    get_wallet_balance_responses,
    transfer_funds_responses,
    get_transaction_history_responses,
)

router = APIRouter(prefix="/wallet", tags=["Wallet"])


@router.post("/deposit", responses=deposit_funds_responses)
async def deposit_funds(
    request: DepositRequest,
    auth: tuple[User, APIKey | None] = Depends(get_current_user),
    _: None = Depends(require_permission("deposit")),
    db: Session = Depends(get_db),
):
    """
    Initialize a Paystack deposit transaction.

    Args:
        request (DepositRequest): Deposit amount.
        auth (tuple): Authenticated user and optional API key.
        db (Session): Database session.

    Returns:
        JSONResponse: Success response with Paystack payment URL.

    Raises:
        HTTPException: 400 if Paystack API call fails or wallet not found.

    Examples:
        >>> # Request:
        >>> POST /wallet/deposit
        >>> {
        >>>   "amount": 5000.00
        >>> }
        >>> # Response:
        >>> {
        >>>   "status": "SUCCESS",
        >>>   "status_code": 200,
        >>>   "message": "Deposit initialized successfully",
        >>>   "data": {
        >>>     "reference": "DEP_1234567890_abc123",
        >>>     "authorization_url": "https://checkout.paystack.com/...",
        >>>     "amount": "5000.00"
        >>>   }
        >>> }

    Notes:
        - Creates pending transaction in database.
        - User completes payment on Paystack URL.
        - Webhook updates transaction and credits wallet.
    """
    user, _ = auth

    wallet = WalletService.get_wallet_by_user_id(db, user.id)

    if not wallet:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Wallet not found",
            error="WALLET_NOT_FOUND",
        )

    try:
        result = await WalletService.initialize_paystack_deposit(
            db=db,
            wallet=wallet,
            amount=request.amount,
            user_email=user.email,
        )

        return success_response(
            status_code=status.HTTP_200_OK,
            message="Deposit initialized successfully",
            data=result,
        )

    except Exception as e:
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Failed to initialize deposit",
            error="PAYSTACK_ERROR",
            errors={"detail": [str(e)]},
        )


@router.post("/paystack/webhook", responses=paystack_webhook_responses)
async def paystack_webhook(
    request: Request,
    x_paystack_signature: str = Header(..., alias="x-paystack-signature"),
    db: Session = Depends(get_db),
):
    """
    Handle Paystack webhook events (MANDATORY for wallet credits).

    Args:
        request (Request): Raw FastAPI request object.
        x_paystack_signature (str): Paystack signature header for verification.
        db (Session): Database session.

    Returns:
        JSONResponse: Simple success confirmation for Paystack.

    Examples:
        >>> # Paystack sends:
        >>> POST /wallet/paystack/webhook
        >>> Headers: x-paystack-signature: abc123...
        >>> Body:
        >>> {
        >>>   "event": "charge.success",
        >>>   "data": {
        >>>     "reference": "DEP_1234567890_abc123",
        >>>     "amount": 500000,
        >>>     "status": "success"
        >>>   }
        >>> }
        >>> # Response:
        >>> {
        >>>   "status": "SUCCESS",
        >>>   "status_code": 200,
        >>>   "message": "Webhook processed successfully",
        >>>   "data": {}
        >>> }

    Notes:
        - CRITICAL: Verifies Paystack signature to prevent spoofing.
        - Idempotent: won't double-credit if webhook is resent.
        - Only "charge.success" events credit wallets.
        - This is the ONLY endpoint that should credit wallets for deposits.
    """
    # Get raw request body for signature verification
    body = await request.body()

    # Verify webhook signature
    if not verify_paystack_signature(body, x_paystack_signature):
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Invalid webhook signature",
            error="INVALID_SIGNATURE",
        )

    # Parse webhook data
    data = await request.json()
    event = data.get("event")

    # Only process successful charge events
    if event == "charge.success":
        reference = data["data"]["reference"]
        
        # Process the deposit (idempotent)
        WalletService.process_successful_deposit(db, reference)

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Webhook processed successfully",
        data={},
    )


@router.get("/deposit/{reference}/status", responses=check_deposit_status_responses)
async def check_deposit_status(
    reference: str,
    auth: tuple[User, APIKey | None] = Depends(get_current_user),
    _: None = Depends(require_permission("read")),
    db: Session = Depends(get_db),
):
    """
    Check status of a deposit transaction (manual verification).

    Args:
        reference (str): Transaction reference.
        auth (tuple): Authenticated user and optional API key.
        db (Session): Database session.

    Returns:
        JSONResponse: Success response with transaction status.

    Raises:
        HTTPException: 404 if transaction not found.

    Examples:
        >>> # Request: GET /wallet/deposit/DEP_1234567890_abc123/status
        >>> # Response:
        >>> {
        >>>   "status": "SUCCESS",
        >>>   "status_code": 200,
        >>>   "message": "Transaction status retrieved",
        >>>   "data": {
        >>>     "reference": "DEP_1234567890_abc123",
        >>>     "status": "success",
        >>>     "amount": "5000.00",
        >>>     "created_at": "2025-01-09T12:00:00Z"
        >>>   }
        >>> }

    Notes:
        - This endpoint does NOT credit wallets.
        - Only shows transaction status for manual verification.
        - Webhooks are the only way wallets are credited.
    """
    user, _ = auth

    wallet = WalletService.get_wallet_by_user_id(db, user.id)

    if not wallet:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Wallet not found",
            error="WALLET_NOT_FOUND",
        )

    transaction = WalletService.get_transaction_by_reference(db, reference)

    if not transaction or transaction.wallet_id != wallet.id:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Transaction not found",
            error="TRANSACTION_NOT_FOUND",
        )

    response_data = {
        "reference": transaction.reference,
        "status": transaction.status,
        "amount": str(transaction.amount),
        "created_at": transaction.created_at.isoformat(),
    }

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Transaction status retrieved",
        data=response_data,
    )


@router.get("/balance", responses=get_wallet_balance_responses)
async def get_wallet_balance(
    auth: tuple[User, APIKey | None] = Depends(get_current_user),
    _: None = Depends(require_permission("read")),
    db: Session = Depends(get_db),
):
    """
    Get current wallet balance.

    Args:
        auth (tuple): Authenticated user and optional API key.
        db (Session): Database session.

    Returns:
        JSONResponse: Success response with wallet balance.

    Raises:
        HTTPException: 404 if wallet not found.

    Examples:
        >>> # Request: GET /wallet/balance
        >>> # Response:
        >>> {
        >>>   "status": "SUCCESS",
        >>>   "status_code": 200,
        >>>   "message": "Wallet balance retrieved",
        >>>   "data": {
        >>>     "balance": "15000.00",
        >>>     "wallet_number": "1234567890123"
        >>>   }
        >>> }

    Notes:
        - Requires 'read' permission if using API key.
        - JWT users always have access.
    """
    user, _ = auth

    wallet = WalletService.get_wallet_by_user_id(db, user.id)

    if not wallet:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Wallet not found",
            error="WALLET_NOT_FOUND",
        )

    response_data = {
        "balance": str(wallet.balance),
        "wallet_number": wallet.wallet_number,
    }

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Wallet balance retrieved",
        data=response_data,
    )


@router.post("/transfer", responses=transfer_funds_responses)
async def transfer_funds(
    request: TransferRequest,
    auth: tuple[User, APIKey | None] = Depends(get_current_user),
    _: None = Depends(require_permission("transfer")),
    db: Session = Depends(get_db),
):
    """
    Transfer funds to another wallet.

    Args:
        request (TransferRequest): Transfer details (wallet_number, amount).
        auth (tuple): Authenticated user and optional API key.
        db (Session): Database session.

    Returns:
        JSONResponse: Success response with transfer confirmation.

    Raises:
        HTTPException: 400 if insufficient balance, 404 if wallet not found.

    Examples:
        >>> # Request:
        >>> POST /wallet/transfer
        >>> {
        >>>   "wallet_number": "9876543210123",
        >>>   "amount": 3000.00
        >>> }
        >>> # Response:
        >>> {
        >>>   "status": "SUCCESS",
        >>>   "status_code": 200,
        >>>   "message": "Transfer completed successfully",
        >>>   "data": {
        >>>     "status": "success",
        >>>     "message": "Transfer completed successfully",
        >>>     "reference": "TRF_1234567890_xyz",
        >>>     "amount": "3000.00",
        >>>     "recipient_wallet": "9876543210123"
        >>>   }
        >>> }

    Notes:
        - Atomic operation: both debit and credit succeed or both fail.
        - Creates two transaction records (transfer_out, transfer_in).
        - Requires 'transfer' permission if using API key.
    """
    user, _ = auth

    sender_wallet = WalletService.get_wallet_by_user_id(db, user.id)

    if not sender_wallet:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Wallet not found",
            error="WALLET_NOT_FOUND",
        )

    try:
        result = WalletService.transfer_funds(
            db=db,
            sender_wallet=sender_wallet,
            recipient_wallet_number=request.wallet_number,
            amount=request.amount,
        )

        return success_response(
            status_code=status.HTTP_200_OK,
            message="Transfer completed successfully",
            data=result,
        )

    except ValueError as e:
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=str(e),
            error="TRANSFER_ERROR",
        )


@router.get("/transactions", responses=get_transaction_history_responses)
async def get_transaction_history(
    auth: tuple[User, APIKey | None] = Depends(get_current_user),
    _: None = Depends(require_permission("read")),
    db: Session = Depends(get_db),
):
    """
    Get transaction history for user's wallet.

    Args:
        auth (tuple): Authenticated user and optional API key.
        db (Session): Database session.

    Returns:
        JSONResponse: Success response with list of transactions.

    Raises:
        HTTPException: 404 if wallet not found.

    Examples:
        >>> # Request: GET /wallet/transactions
        >>> # Response:
        >>> {
        >>>   "status": "SUCCESS",
        >>>   "status_code": 200,
        >>>   "message": "Transaction history retrieved",
        >>>   "data": {
        >>>     "transactions": [
        >>>       {
        >>>         "id": 1,
        >>>         "type": "deposit",
        >>>         "amount": "5000.00",
        >>>         "status": "success",
        >>>         "reference": "DEP_123",
        >>>         "metadata": {},
        >>>         "created_at": "2025-01-09T12:00:00Z"
        >>>       }
        >>>     ],
        >>>     "total": 1
        >>>   }
        >>> }

    Notes:
        - Returns transactions ordered by most recent first.
        - Limited to 50 transactions per request.
        - Requires 'read' permission if using API key.
    """
    user, _ = auth

    wallet = WalletService.get_wallet_by_user_id(db, user.id)

    if not wallet:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Wallet not found",
            error="WALLET_NOT_FOUND",
        )

    transactions = WalletService.get_transactions(db, wallet.id, limit=50)

    transactions_data = [
        {
            "id": txn.id,
            "type": txn.type,
            "amount": str(txn.amount),
            "status": txn.status,
            "reference": txn.reference,
            "metadata": txn.metadata,
            "created_at": txn.created_at.isoformat(),
        }
        for txn in transactions
    ]

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Transaction history retrieved",
        data={"transactions": transactions_data, "total": len(transactions_data)},
    )