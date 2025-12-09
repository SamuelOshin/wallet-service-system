"""
Wallet operation routes.

Endpoints:
- GET /wallet/me: Get user profile and wallet details
- POST /wallet/deposit: Initialize Paystack deposit
- POST /wallet/paystack/webhook: Handle Paystack webhooks
- GET /wallet/deposit/{reference}/status: Check deposit status
- GET /wallet/balance: Get wallet balance
- POST /wallet/transfer: Transfer to another wallet
- GET /wallet/transactions: Get transaction history
"""


from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.orm import Session

from app.api.core.database import get_db
from app.api.models.user import APIKey, User
from app.api.schemas.wallet import (
    DepositRequest,
    TransactionResponse,
    TransferRequest,
    UserDetailsResponse,
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


@router.get("/me")
async def get_user_details(
    auth: tuple[User, APIKey | None] = Depends(get_current_user),
    _: None = Depends(require_permission("read")),
    db: Session = Depends(get_db),
):
    """
    Get authenticated user's profile and wallet details.

    Args:
        auth (tuple): Authenticated user and optional API key.
        db (Session): Database session.

    Returns:
        JSONResponse: User profile with wallet information.


    Notes:
        - Returns authenticated user's profile and wallet balance.
        - Requires valid authentication token.
    """
    user, _ = auth

    wallet = WalletService.get_wallet_by_user_id(db, user.id)

    if not wallet:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Wallet not found",
            error="WALLET_NOT_FOUND",
        )

    user_details = UserDetailsResponse(
        name=user.name,
        email=user.email,
        wallet_number=wallet.wallet_number,
        balance=wallet.balance,
    )

    return success_response(
        status_code=status.HTTP_200_OK,
        message="User details retrieved",
        data=user_details,
    )


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
        result = WalletService.initialize_paystack_deposit(
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


@router.post("/deposit/{reference}/verify", responses=check_deposit_status_responses)
async def verify_deposit_with_paystack(
    reference: str,
    auth: tuple[User, APIKey | None] = Depends(get_current_user),
    _: None = Depends(require_permission("deposit")),
    db: Session = Depends(get_db),
):
    """
    Manually verify a deposit transaction with Paystack and update status.

    Args:
        reference (str): Transaction reference from your system.
        auth (tuple): Authenticated user and optional API key.
        db (Session): Database session.

    Returns:
        JSONResponse: Transaction status from Paystack.

    Raises:
        HTTPException: 404 if transaction not found, 400 if Paystack verification fails.

    Notes:
        - Use this endpoint if webhook fails and payment is pending.
        - Queries Paystack API to verify actual payment status.
        - Updates local transaction status if Paystack confirms success.
    """
    user, _ = auth

    # Get transaction from database
    transaction = WalletService.get_transaction_by_reference(db, reference)

    if not transaction:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Transaction not found",
            error="TRANSACTION_NOT_FOUND",
        )

    # Verify with Paystack
    try:
        paystack_status = WalletService.verify_paystack_transaction(reference)

        # If Paystack says success and our record is pending, process it
        if paystack_status["status"] == "success" and transaction.status == "pending":
            WalletService.process_successful_deposit(db, reference)
            transaction = WalletService.get_transaction_by_reference(db, reference)

        return success_response(
            status_code=status.HTTP_200_OK,
            message="Deposit verified",
            data={
                "reference": reference,
                "status": transaction.status,
                "amount": str(transaction.amount),
                "paystack_confirmed": paystack_status["status"] == "success",
            },
        )
    except Exception as e:
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=f"Paystack verification failed: {str(e)}",
            error="PAYSTACK_ERROR",
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
            user_id=user.id,
            idempotency_key=request.idempotency_key,
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

    transactions_data = [TransactionResponse.from_orm(txn) for txn in transactions]

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Transaction history retrieved",
        data={"transactions": transactions_data, "total": len(transactions_data)},
    )
