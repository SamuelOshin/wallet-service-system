"""
Background tasks for periodic maintenance and recovery operations.

This module contains tasks that should run periodically to maintain system health,
handle failed operations, and recover from partial transaction failures.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.api.core.database import SessionLocal
from app.api.services.wallet_service import WalletService

logger = logging.getLogger(__name__)


async def mark_stale_pending_transactions_task():
    """
    Background task to mark stale pending transactions as failed.

    Runs every 5 minutes to clean up transactions that have been pending too long.
    This prevents accumulation of stuck transactions and ensures users get feedback.
    """
    while True:
        try:
            with SessionLocal() as db:
                count = WalletService.mark_stale_pending_transactions_as_failed(
                    db, timeout_minutes=30
                )
                if count > 0:
                    logger.info(f"Marked {count} stale pending transactions as failed")
        except Exception as e:
            logger.error(f"Error in mark_stale_pending_transactions_task: {e}")

        # Run every 5 minutes
        await asyncio.sleep(300)


async def detect_and_recover_failed_transfers_task():
    """
    Background task to detect and recover failed transfer operations.

    Runs every 10 minutes to find transfers where sender was debited but recipient
    wasn't credited, then automatically recovers them.
    """
    while True:
        try:
            with SessionLocal() as db:
                # Find successful transfer_out transactions
                transfer_out_txns = db.query(Transaction).filter(
                    Transaction.type == "transfer_out",
                    Transaction.status == "success"
                ).all()

                recovered_count = 0
                for txn in transfer_out_txns:
                    try:
                        # Check if corresponding transfer_in exists and is successful
                        transfer_in_ref = f"{txn.reference}_IN"
                        transfer_in_txn = db.query(Transaction).filter(
                            Transaction.reference == transfer_in_ref
                        ).first()

                        # If transfer_in doesn't exist or failed, recover
                        if not transfer_in_txn or transfer_in_txn.status != "success":
                            success = WalletService.recover_failed_transfer(
                                db, txn.reference
                            )
                            if success:
                                recovered_count += 1
                                logger.info(f"Recovered failed transfer: {txn.reference}")

                    except Exception as e:
                        logger.error(f"Error recovering transfer {txn.reference}: {e}")
                        continue

                if recovered_count > 0:
                    logger.info(f"Recovered {recovered_count} failed transfers")

        except Exception as e:
            logger.error(f"Error in detect_and_recover_failed_transfers_task: {e}")

        # Run every 10 minutes
        await asyncio.sleep(600)


async def start_background_tasks():
    """
    Start all background maintenance tasks.

    This function creates and starts all background tasks that run continuously
    to maintain system health and handle recovery operations.
    """
    logger.info("Starting background tasks...")

    # Create tasks
    task1 = asyncio.create_task(mark_stale_pending_transactions_task())
    task2 = asyncio.create_task(detect_and_recover_failed_transfers_task())

    # Wait for tasks to complete (they run indefinitely)
    await asyncio.gather(task1, task2)


# Import here to avoid circular imports
from app.api.models.user import Transaction