import pytest
from datetime import datetime, timezone
from fastapi import BackgroundTasks

from src.api import transactions as tx_api
from src.schemas.transaction_schemas import TransactionCreate, TransactionUpdate
from src.models.transaction_models import Alert
from src.tenancy.context import set_current_tenant, clear_current_tenant


@pytest.mark.unit
def test_transactions_endpoints(db_session, monkeypatch):
    set_current_tenant("default")
    try:
        from src.tasks import transaction_processing as tx_tasks

        monkeypatch.setattr(tx_tasks, "process_transaction_sync", lambda *args, **kwargs: None)

        payload = TransactionCreate(
            transaction_id="txn_test_1",
            user_id="user_txn",
            amount=100.00,
            currency="usd",
            transaction_type="deposit",
            timestamp=datetime.now(timezone.utc),
            country_code="US",
        )

        created = tx_api.ingest_transaction(payload, BackgroundTasks(), db_session)
        assert created.transaction_id == "txn_test_1"

        batch_payload = TransactionCreate(
            transaction_id="txn_test_2",
            user_id="user_txn",
            amount=150.00,
            currency="usd",
            transaction_type="deposit",
            timestamp=datetime.now(timezone.utc),
            country_code="US",
        )
        batch = tx_api.ingest_transactions_batch([batch_payload], BackgroundTasks(), db_session)
        assert batch

        transactions = tx_api.list_transactions(skip=0, limit=100, db=db_session)
        assert transactions

        fetched = tx_api.get_transaction("txn_test_1", db_session, tenant_id="default")
        assert fetched.transaction_id == "txn_test_1"

        updated = tx_api.update_transaction(
            "txn_test_1",
            TransactionUpdate(risk_level="high"),
            db_session,
            tenant_id="default",
        )
        assert updated.risk_level == "high"

        db_session.add(
            Alert(
                tenant_id="default",
                alert_id="alert_txn_user",
                alert_type="velocity",
                severity="medium",
                user_id="user_txn",
                status="pending",
            )
        )
        db_session.commit()

        history = tx_api.get_user_transaction_history("user_txn", days=30, db=db_session)
        assert history

        alerts = tx_api.get_user_alerts("user_txn", db=db_session)
        assert alerts

        stats = tx_api.get_transaction_statistics(days=30, db=db_session)
        assert stats.total_transactions >= 1
    finally:
        clear_current_tenant()
