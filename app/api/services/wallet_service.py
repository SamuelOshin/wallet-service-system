"""
Wallet service for deposit, transfer, and balance operations.

Handles:
- Paystack deposit initialization
- Wallet-to-wallet transfers
- Balance retrieval
- Transaction history
"""

import secrets
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional

import httpx
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.api.core.config import get_settings
from app.api.models.user import Transaction, Wallet

settings = get_settings()


class WalletService:
    """Service for wallet operations and Paystack integration."""

    @staticmethod
    def get_wallet_by_user_id(db: Session, user_id: int) -> Optional[Wallet]:
        """
        Get wallet for a specific user.

        Args:
            db (Session): Database session.
            user_id (int): User ID.

        Returns:
            Optional[Wallet]: User's wallet or None if not found.

        Examples:
            >>> wallet = WalletService.get_wallet_by_user_id(db, user_id=1)
            >>> print(wallet.balance)
            5000.00
        """
        return db.query(Wallet).filter(Wallet.user_id == user_id).first()

    @staticmethod
    def get_wallet_by_number(db: Session, wallet_number: str) -> Optional[Wallet]:
        """
        Get wallet by wallet number.

        Args:
            db (Session): Database session.
            wallet_number (str): 13-digit wallet number.

        Returns:
            Optional[Wallet]: Wallet or None if not found.

        Examples:
            >>> wallet = WalletService.get_wallet_by_number(db, "1234567890123")
        """
        return db.query(Wallet).filter(Wallet.wallet_number == wallet_number).first()

    @staticmethod
    def generate_transaction_reference(prefix: str = "DEP") -> str:
        """
        Generate unique transaction reference.

        Args:
            prefix (str): Reference prefix (e.g., "DEP", "TRF").

        Returns:
            str: Unique transaction reference.

        Examples:
            >>> ref = WalletService.generate_transaction_reference("DEP")
            >>> print(ref.startswith("DEP_"))
            True
        """
        timestamp = int(datetime.now(timezone.utc).timestamp())
        random_str = secrets.token_hex(8)
        return f"{prefix}_{timestamp}_{random_str}"

    @staticmethod
    async def initialize_paystack_deposit(
        db: Session,
        wallet: Wallet,
        amount: Decimal,
        user_email: str
    ) -> Dict[str, str]:
        """
        Initialize Paystack deposit transaction.

        Args:
            db (Session): Database session.
            wallet (Wallet): User's wallet.
            amount (Decimal): Deposit amount in Naira.
            user_email (str): User's email for Paystack.

        Returns:
            Dict[str, str]: Contains reference and authorization_url.

        Raises:
            httpx.HTTPStatusError: If Paystack API call fails.

        Examples:
            >>> result = await WalletService.initialize_paystack_deposit(
            >>>     db, wallet, Decimal("5000.00"), "user@example.com"
            >>> )
            >>> print(result["authorization_url"])
            'https://checkout.paystack.com/...'

        Notes:
            - Creates pending transaction in database.
            - Converts amount to kobo (multiply by 100).
            - Webhook will update transaction status and credit wallet.
        """
        # Generate unique reference
        reference = WalletService.generate_transaction_reference("DEP")

        # Create pending transaction
        transaction = Transaction(
            wallet_id=wallet.id,
            type="deposit",
            amount=amount,
            reference=reference,
            status="pending",
            metadata={"email": user_email},
        )

        db.add(transaction)
        db.commit()

        # Initialize Paystack transaction
        paystack_url = f"{settings.PAYSTACK_BASE_URL}/transaction/initialize"
        headers = {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json",
        }

        # Convert to kobo (Paystack uses smallest currency unit)
        amount_in_kobo = int(amount * 100)

        payload = {
            "email": user_email,
            "amount": amount_in_kobo,
            "reference": reference,
            "callback_url": f"{settings.FRONTEND_URL}/payment/callback",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(paystack_url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        return {
            "reference": reference,
            "authorization_url": data["data"]["authorization_url"],
            "amount": str(amount),
        }

    @staticmethod
    def process_successful_deposit(db: Session, reference: str) -> bool:
        """
        Process successful deposit from webhook (idempotent).

        Args:
            db (Session): Database session.
            reference (str): Transaction reference from Paystack.

        Returns:
            bool: True if processed successfully, False if already processed.

        Examples:
            >>> success = WalletService.process_successful_deposit(db, "DEP_123_abc")
            >>> print(success)
            True

        Notes:
            - Idempotent: won't double-credit if called multiple times.
            - Updates transaction status and wallet balance atomically.
        """
        # Get transaction
        transaction = db.query(Transaction).filter(
            Transaction.reference == reference
        ).with_for_update().first()

        if not transaction:
            return False

        # Already processed (idempotency check)
        if transaction.status == "success":
            return False

        # Update transaction status
        transaction.status = "success"

        # Credit wallet
        wallet = db.query(Wallet).filter(Wallet.id == transaction.wallet_id).first()
        wallet.balance += transaction.amount

        db.commit()
        return True

    @staticmethod
    def transfer_funds(
        db: Session,
        sender_wallet: Wallet,
        recipient_wallet_number: str,
        amount: Decimal
    ) -> Dict[str, any]:
        """
        Transfer funds between wallets (atomic operation).

        Args:
            db (Session): Database session.
            sender_wallet (Wallet): Sender's wallet.
            recipient_wallet_number (str): Recipient's wallet number.
            amount (Decimal): Transfer amount.

        Returns:
            Dict[str, any]: Transfer result with status and reference.

        Raises:
            ValueError: If insufficient balance, invalid recipient, or self-transfer.

        Examples:
            >>> result = WalletService.transfer_funds(
            >>>     db, sender_wallet, "9876543210123", Decimal("3000.00")
            >>> )
            >>> print(result["status"])
            'success'

        Notes:
            - Atomic transaction: either both debit and credit succeed, or both fail.
            - Creates two transaction records: transfer_out and transfer_in.
            - Prevents self-transfers.
        """
        # Validate sender balance
        if sender_wallet.balance < amount:
            raise ValueError("Insufficient balance")

        # Get recipient wallet
        recipient_wallet = WalletService.get_wallet_by_number(db, recipient_wallet_number)
        
        if not recipient_wallet:
            raise ValueError("Recipient wallet not found")

        # Prevent self-transfer
        if sender_wallet.id == recipient_wallet.id:
            raise ValueError("Cannot transfer to your own wallet")

        # Generate reference
        reference = WalletService.generate_transaction_reference("TRF")

        try:
            # Deduct from sender
            sender_wallet.balance -= amount

            # Add to recipient
            recipient_wallet.balance += amount

            # Record sender transaction
            sender_txn = Transaction(
                wallet_id=sender_wallet.id,
                type="transfer_out",
                amount=amount,
                reference=reference,
                status="success",
                metadata={
                    "recipient_wallet": recipient_wallet_number,
                    "recipient_user_id": recipient_wallet.user_id,
                },
            )

            # Record recipient transaction
            recipient_txn = Transaction(
                wallet_id=recipient_wallet.id,
                type="transfer_in",
                amount=amount,
                reference=f"{reference}_IN",
                status="success",
                metadata={
                    "sender_wallet": sender_wallet.wallet_number,
                    "sender_user_id": sender_wallet.user_id,
                },
            )

            db.add(sender_txn)
            db.add(recipient_txn)
            db.commit()

            return {
                "status": "success",
                "message": "Transfer completed successfully",
                "reference": reference,
                "amount": str(amount),
                "recipient_wallet": recipient_wallet_number,
            }

        except Exception as e:
            db.rollback()
            raise e

    @staticmethod
    def get_transactions(
        db: Session,
        wallet_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[Transaction]:
        """
        Get transaction history for a wallet.

        Args:
            db (Session): Database session.
            wallet_id (int): Wallet ID.
            limit (int): Maximum number of transactions to return.
            offset (int): Number of transactions to skip.

        Returns:
            List[Transaction]: List of transactions ordered by most recent.

        Examples:
            >>> transactions = WalletService.get_transactions(db, wallet_id=1, limit=10)
            >>> for txn in transactions:
            >>>     print(f"{txn.type}: {txn.amount}")
        """
        return (
            db.query(Transaction)
            .filter(Transaction.wallet_id == wallet_id)
            .order_by(Transaction.created_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    @staticmethod
    def get_transaction_by_reference(db: Session, reference: str) -> Optional[Transaction]:
        """
        Get transaction by reference.

        Args:
            db (Session): Database session.
            reference (str): Transaction reference.

        Returns:
            Optional[Transaction]: Transaction or None if not found.

        Examples:
            >>> txn = WalletService.get_transaction_by_reference(db, "DEP_123_abc")
            >>> print(txn.status)
            'success'
        """
        return db.query(Transaction).filter(Transaction.reference == reference).first()