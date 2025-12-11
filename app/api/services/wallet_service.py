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
from sqlalchemy.orm import Session

from app.api.core.config import get_settings
from app.api.models.user import IdempotencyKey, Transaction, Wallet

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
    def initialize_paystack_deposit(
        db: Session, wallet: Wallet, amount: Decimal, user_email: str
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
            extra_data={"email": user_email},
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

        response = httpx.post(paystack_url, json=payload, headers=headers)
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
        transaction = (
            db.query(Transaction)
            .filter(Transaction.reference == reference)
            .with_for_update()
            .first()
        )

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
        amount: Decimal,
        user_id: int,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Transfer funds between wallets (atomic operation).

        Args:
            db (Session): Database session.
            sender_wallet (Wallet): Sender's wallet.
            recipient_wallet_number (str): Recipient's wallet number.
            amount (Decimal): Transfer amount.
            user_id (int): ID of the user initiating the transfer.
            idempotency_key (Optional[str]): Unique key to prevent duplicate transfers.

        Returns:
            Dict[str, any]: Transfer result with status and reference.

        Raises:
            ValueError: If insufficient balance, invalid recipient, self-transfer, or duplicate idempotency key.

        Examples:
            >>> result = WalletService.transfer_funds(
            >>>     db, sender_wallet, "9876543210123", Decimal("3000.00"), user_id=1, idempotency_key="uuid-123"
            >>> )
            >>> print(result["status"])
            'success'

        Notes:
            - Atomic transaction: either both debit and credit succeed, or both fail.
            - Creates two transaction records: transfer_out and transfer_in.
            - Prevents self-transfers and duplicate operations via idempotency key.
        """
        # Check idempotency key if provided
        if idempotency_key:
            existing_key = db.query(IdempotencyKey).filter(
                IdempotencyKey.key == idempotency_key,
                IdempotencyKey.operation == "transfer"
            ).first()
            if existing_key:
                raise ValueError("Duplicate transfer request")

        # Validate sender balance
        if sender_wallet.balance < amount:
            raise ValueError("Insufficient balance")

        # Get recipient wallet
        recipient_wallet = WalletService.get_wallet_by_number(
            db, recipient_wallet_number
        )

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
                extra_data={
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
                extra_data={
                    "sender_wallet": sender_wallet.wallet_number,
                    "sender_user_id": sender_wallet.user_id,
                },
            )

            db.add(sender_txn)
            db.add(recipient_txn)
            
            # Store idempotency key if provided
            if idempotency_key:
                db.add(IdempotencyKey(
                    key=idempotency_key,
                    operation="transfer",
                    user_id=user_id
                ))
            
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
        db: Session, wallet_id: int, limit: int = 50, offset: int = 0
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
    def get_transaction_by_reference(
        db: Session, reference: str
    ) -> Optional[Transaction]:
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

    @staticmethod
    def verify_paystack_transaction(reference: str) -> Dict[str, str]:
        """
        Verify transaction status with Paystack API.

        Args:
            reference (str): Transaction reference.

        Returns:
            Dict[str, str]: Transaction details from Paystack.

        Raises:
            httpx.HTTPStatusError: If Paystack API call fails.

        Examples:
            >>> result = WalletService.verify_paystack_transaction("DEP_123_abc")
            >>> print(result["status"])
            'success'

        Notes:
            - Queries Paystack to check actual payment status.
            - Useful for manual verification if webhook fails.
        """
        paystack_url = f"{settings.PAYSTACK_BASE_URL}/transaction/verify/{reference}"
        headers = {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        }

        response = httpx.get(paystack_url, headers=headers)
        response.raise_for_status()
        data = response.json()

        return {
            "status": data["data"]["status"],
            "amount": str(data["data"]["amount"] / 100),  # Convert from kobo
            "reference": data["data"]["reference"],
        }

    @staticmethod
    def recover_failed_transfer(db: Session, transfer_reference: str) -> bool:
        """
        Recover a failed transfer by rolling back the debit and marking transactions as failed.

        Args:
            db (Session): Database session.
            transfer_reference (str): Transfer reference to recover.

        Returns:
            bool: True if recovery was successful, False if no recovery needed.

        Raises:
            ValueError: If transfer reference is invalid or recovery fails.

        Examples:
            >>> success = WalletService.recover_failed_transfer(db, "TRF_123_abc")
            >>> print(success)
            True

        Notes:
            - Only recovers transfers where sender was debited but recipient wasn't credited.
            - Marks both transactions as 'failed' and refunds sender.
            - Idempotent: safe to call multiple times.
        """
        # Find the transfer_out transaction
        transfer_out_txn = db.query(Transaction).filter(
            Transaction.reference == transfer_reference,
            Transaction.type == "transfer_out",
            Transaction.status == "success"
        ).first()

        if not transfer_out_txn:
            raise ValueError("Transfer reference not found or not in recoverable state")

        # Check if there's a corresponding transfer_in transaction
        transfer_in_reference = f"{transfer_reference}_IN"
        transfer_in_txn = db.query(Transaction).filter(
            Transaction.reference == transfer_in_reference,
            Transaction.type == "transfer_in"
        ).first()

        # If transfer_in exists and is successful, this transfer completed successfully
        if transfer_in_txn and transfer_in_txn.status == "success":
            return False 

        try:
            # Get sender wallet and refund the amount
            sender_wallet = transfer_out_txn.wallet
            amount = transfer_out_txn.amount

            # Refund sender
            sender_wallet.balance += amount

            # Mark transfer_out as failed
            transfer_out_txn.status = "failed"
            transfer_out_txn.extra_data["recovery_reason"] = "transfer_incomplete"

            # If transfer_in exists but failed, update it too
            if transfer_in_txn:
                transfer_in_txn.status = "failed"
                transfer_in_txn.extra_data["recovery_reason"] = "transfer_incomplete"

            db.commit()
            return True

        except Exception as e:
            db.rollback()
            raise ValueError(f"Recovery failed: {str(e)}")

    @staticmethod
    def mark_stale_pending_transactions_as_failed(db: Session, timeout_minutes: int = 30) -> int:
        """
        Mark stale pending deposit transactions as failed after timeout.

        Args:
            db (Session): Database session.
            timeout_minutes (int): Minutes after which pending transactions are considered stale.

        Returns:
            int: Number of transactions marked as failed.

        Examples:
            >>> count = WalletService.mark_stale_pending_transactions_as_failed(db, timeout_minutes=60)
            >>> print(f"Marked {count} transactions as failed")

        Notes:
            - Only affects 'pending' deposit transactions older than timeout.
            - Should be run periodically (e.g., every 5-10 minutes).
        """
        from datetime import datetime, timedelta

        cutoff_time = datetime.utcnow() - timedelta(minutes=timeout_minutes)

        stale_transactions = db.query(Transaction).filter(
            Transaction.status == "pending",
            Transaction.type == "deposit",
            Transaction.created_at < cutoff_time
        ).all()

        updated_count = 0
        for txn in stale_transactions:
            txn.status = "failed"
            txn.extra_data["failure_reason"] = "timeout"
            updated_count += 1

        if updated_count > 0:
            db.commit()

        return updated_count

