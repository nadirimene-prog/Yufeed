from datetime import datetime, timezone
import uuid

import pytest
from sqlalchemy.orm import sessionmaker

from src.models.transaction_models import Transaction, FailedTransactionProcessingItem
from src.tasks import transaction_processing


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@pytest.mark.integration
def test_process_transaction_task_writes_dlq_on_non_retryable_error(db_session, test_db_engine, monkeypatch):
    # Patch Celery task SessionLocal to use the test DB engine.
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
    monkeypatch.setattr(transaction_processing, "SessionLocal", TestSessionLocal)

    transaction_id = f"dlq-{uuid.uuid4().hex[:12]}"
    user_id = f"user-{uuid.uuid4().hex[:8]}"

    tx = Transaction(
        tenant_id="tenant-a",
        transaction_id=transaction_id,
        user_id=user_id,
        amount=10,
        currency="USD",
        transaction_type="deposit",
        timestamp=utc_now(),
        status="completed",
    )
    db_session.add(tx)
    db_session.commit()

    def boom(*args, **kwargs):
        raise ValueError("boom")

    monkeypatch.setattr(transaction_processing, "process_transaction_sync", boom)

    result = transaction_processing.process_transaction_task(tx.id, "tenant-a")
    assert result["status"] == "dlq"
    assert result.get("dlq_item_id") is not None

    db_session.expire_all()
    item = (
        db_session.query(FailedTransactionProcessingItem)
        .filter(FailedTransactionProcessingItem.id == result["dlq_item_id"])
        .first()
    )
    assert item is not None
    assert item.tenant_id == "tenant-a"
    assert item.transaction_db_id == tx.id
    assert "boom" in (item.error_message or "")

