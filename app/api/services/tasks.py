from celery import shared_task
from decimal import Decimal
from sqlalchemy.orm import Session
from app.api.core.celery_config import celery_app
from app.api.core.database import async_session
from app.api.models.user import Wallet, Transaction, IdempotencyKey
from sqlalchemy import update


@shared_task(bind=True, name="transfer_funds_task")
def process_transfer_task(
    self,
    sender_wallet_id: int,
    recipient_wallet_number: str,
    amount: float,
    user_id: int,
    idempotency_key: str,
):
    """
    Celery task to process wallet transfer in background.

    Args:
        sender_wallet_id (int): ID of sender's wallet.
        recipient_wallet_number (str): Recipient's wallet number.
        amount (float): Transfer amount.
        user_id (int): ID of user initiating transfer.
        idempotency_key (str): Unique key for idempotency.

    Returns:
        dict: Task result with status, reference, and metadata.

    Raises:
        Exception: If transfer fails.

    Notes:
        - Runs in background via Celery.
        - Idempotency prevents duplicate processing.
        - Updates transaction status from "processing" to "completed" or "failed".
    """
    # Create synchronous session for this task
    db = Session()
    
    try:
        # Get sender and recipient wallets
        sender_wallet = db.query(Wallet).filter(Wallet.id == sender_wallet_id).first()
        recipient_wallet = db.query(Wallet).filter(
            Wallet.wallet_number == recipient_wallet_number
        ).first()
        
        if not sender_wallet:
            raise ValueError("Sender wallet not found")
        if not recipient_wallet:
            raise ValueError(f"Recipient wallet {recipient_wallet_number} not found")
        
        # Check idempotency
        existing_key = db.query(IdempotencyKey).filter(
            IdempotencyKey.key == idempotency_key,
            IdempotencyKey.operation == "transfer"
        ).first()
        if existing_key:
            raise ValueError("Duplicate transfer request")
        
        # Convert amount
        amount_decimal = Decimal(str(amount))
        
        # Check sufficient balance
        if sender_wallet.balance < amount_decimal:
            raise ValueError("Insufficient balance")
        
        # Check self-transfer
        if sender_wallet.id == recipient_wallet.id:
            raise ValueError("Cannot transfer to own wallet")
        
        # Atomic transfer operation
        db.begin_nested()
        
        # Debit sender
        sender_wallet.balance -= amount_decimal
        db.add(sender_wallet)
        
        # Credit recipient
        recipient_wallet.balance += amount_decimal
        db.add(recipient_wallet)
        
        # Create transaction records
        transfer_out = Transaction(
            wallet_id=sender_wallet.id,
            type="transfer_out",
            amount=amount_decimal,
            status="success",
            reference=f"TRF_{self.request.id}",
            metadata={
                "recipient_wallet": recipient_wallet_number,
                "idempotency_key": idempotency_key,
            }
        )
        transfer_in = Transaction(
            wallet_id=recipient_wallet.id,
            type="transfer_in",
            amount=amount_decimal,
            status="success",
            reference=f"TRF_{self.request.id}",
            metadata={
                "sender_wallet": sender_wallet.wallet_number,
                "idempotency_key": idempotency_key,
            }
        )
        
        db.add(transfer_out)
        db.add(transfer_in)
        
        # Store idempotency key
        idempotency = IdempotencyKey(
            key=idempotency_key,
            user_id=user_id,
            operation="transfer",
            result={
                "reference": f"TRF_{self.request.id}",
                "status": "success",
                "amount": str(amount_decimal),
                "recipient": recipient_wallet_number
            }
        )
        db.add(idempotency)
        
        db.commit()
        
        return {
            "status": "success",
            "reference": f"TRF_{self.request.id}",
            "amount": str(amount_decimal),
            "recipient_wallet": recipient_wallet_number,
            "idempotency_key": idempotency_key,
        }
    
    except Exception as e:
        db.rollback()
        self.update_state(
            state="FAILURE",
            meta={"error": str(e)}
        )
        raise
    
    finally:
        db.close()