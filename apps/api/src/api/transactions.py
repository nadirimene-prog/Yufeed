"""
Transaction Monitoring API Endpoints
Handles transaction ingestion, querying, and risk assessment.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_
from typing import List, Optional
from datetime import datetime, timedelta, timezone
import uuid
import logging
import os

from src.database import get_db


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)
from src.tenancy.queries import get_tenant_filtered_query, set_tenant_on_create, ensure_tenant_match, require_tenant

logger = logging.getLogger(__name__)
from src.models.transaction_models import (
    Transaction, Alert, Case, MonitoringRule,
    UserRiskProfile, FeatureValue
)
from src.schemas.transaction_schemas import (
    TransactionCreate, TransactionUpdate, TransactionResponse,
    AlertResponse, UserRiskProfileResponse,
    TransactionStatistics
)
from src.audit.recorders import record_event

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


# ============================================================================
# TRANSACTION INGESTION
# ============================================================================

@router.post("/ingest", response_model=TransactionResponse, status_code=201)
def ingest_transaction(
    transaction: TransactionCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Ingest a new transaction for monitoring.

    This endpoint:
    1. Stores the transaction
    2. Triggers risk scoring (background)
    3. Evaluates monitoring rules (background)
    4. Updates user risk profile (background)
    """
    # Phase 4C: Check for duplicate transaction_id (tenant-filtered)
    existing = get_tenant_filtered_query(Transaction, db).filter(
        Transaction.transaction_id == transaction.transaction_id
    ).first()

    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Transaction {transaction.transaction_id} already exists"
        )

    # Create transaction record
    db_transaction = Transaction(**transaction.dict())

    # Phase 4C: Set tenant context on new transaction
    set_tenant_on_create(db_transaction)

    db.add(db_transaction)

    tx_type = (transaction.transaction_type or "").lower()
    event_type = "txn_crypto" if "crypto" in tx_type or "onchain" in tx_type else "txn_fiat"
    record_event(
        db,
        event_type=event_type,
        entity_type="transaction",
        entity_id=transaction.transaction_id,
        payload={
            "user_id": transaction.user_id,
            "amount": float(transaction.amount),
            "currency": transaction.currency,
            "transaction_type": transaction.transaction_type,
        },
    )
    db.commit()
    db.refresh(db_transaction)

    # Trigger async processing via Celery (never pass request-scoped DB sessions to background tasks)
    from src.tasks.transaction_processing import process_transaction_task, process_transaction_sync

    if os.getenv("ENVIRONMENT", "").lower() in {"test", "testing"}:
        process_transaction_sync(db, db_transaction.id, db_transaction.tenant_id)
    else:
        process_transaction_task.delay(db_transaction.id, db_transaction.tenant_id)

    return db_transaction


@router.post("/", response_model=TransactionResponse, status_code=201)
def ingest_transaction_compat(
    transaction: TransactionCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Backwards-compatible transaction ingestion endpoint.

    Alias for /api/transactions/ingest.
    """
    return ingest_transaction(transaction, background_tasks, db)


@router.post("/ingest/batch", response_model=List[TransactionResponse], status_code=201)
def ingest_transactions_batch(
    transactions: List[TransactionCreate],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Batch ingest multiple transactions.

    Optimized for high-volume ingestion with bulk insert.
    """
    if len(transactions) > 1000:
        raise HTTPException(
            status_code=400,
            detail="Batch size exceeds maximum of 1000 transactions"
        )

    # Phase 4C: Check for duplicates (tenant-filtered)
    transaction_ids = [t.transaction_id for t in transactions]
    existing_ids = get_tenant_filtered_query(Transaction, db).with_entities(
        Transaction.transaction_id
    ).filter(
        Transaction.transaction_id.in_(transaction_ids)
    ).all()
    existing_ids_set = {row[0] for row in existing_ids}

    # Filter out duplicates
    new_transactions = [
        t for t in transactions
        if t.transaction_id not in existing_ids_set
    ]

    if not new_transactions:
        raise HTTPException(
            status_code=409,
            detail="All transactions already exist"
        )

    # Bulk insert
    db_transactions = [Transaction(**t.dict()) for t in new_transactions]

    # Phase 4C: Set tenant context on all new transactions
    for db_tx in db_transactions:
        set_tenant_on_create(db_tx)

    db.bulk_save_objects(db_transactions, return_defaults=True)
    db.commit()

    # Record immutable events
    for tx in new_transactions:
        tx_type = (tx.transaction_type or "").lower()
        event_type = "txn_crypto" if "crypto" in tx_type or "onchain" in tx_type else "txn_fiat"
        record_event(
            db,
            event_type=event_type,
            entity_type="transaction",
            entity_id=tx.transaction_id,
            payload={
                "user_id": tx.user_id,
                "amount": float(tx.amount),
                "currency": tx.currency,
                "transaction_type": tx.transaction_type,
            },
        )
    db.commit()

    # Trigger background processing for each transaction
    from src.tasks.transaction_processing import process_transaction_task, process_transaction_sync
    for db_transaction in db_transactions:
        if os.getenv("ENVIRONMENT", "").lower() in {"test", "testing"}:
            process_transaction_sync(db, db_transaction.id, db_transaction.tenant_id)
        else:
            process_transaction_task.delay(db_transaction.id, db_transaction.tenant_id)

    # Phase 4C: Refresh to get all fields (tenant-filtered)
    created_ids = [t.id for t in db_transactions]
    results = get_tenant_filtered_query(Transaction, db).filter(
        Transaction.id.in_(created_ids)
    ).all()

    return results


# ============================================================================
# TRANSACTION QUERIES
# ============================================================================

@router.get("/", response_model=List[TransactionResponse])
def list_transactions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    user_id: Optional[str] = None,
    risk_level: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    country_code: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List transactions with filtering options.

    Supports pagination and multiple filter criteria.
    Uses eager loading to prevent N+1 queries when accessing alerts.
    """
    # Phase 4C: Tenant-filtered query
    query = get_tenant_filtered_query(Transaction, db).options(
        joinedload(Transaction.alerts)
    )

    # Apply filters
    if user_id:
        query = query.filter(Transaction.user_id == user_id)

    if risk_level:
        query = query.filter(Transaction.risk_level == risk_level)

    if status:
        query = query.filter(Transaction.status == status)

    if start_date:
        query = query.filter(Transaction.timestamp >= start_date)

    if end_date:
        query = query.filter(Transaction.timestamp <= end_date)

    if min_amount is not None:
        query = query.filter(Transaction.amount >= min_amount)

    if max_amount is not None:
        query = query.filter(Transaction.amount <= max_amount)

    if country_code:
        query = query.filter(Transaction.country_code == country_code)

    # Order by timestamp descending (most recent first)
    query = query.order_by(Transaction.timestamp.desc())

    # Pagination
    transactions = query.offset(skip).limit(limit).all()

    return transactions


@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(
    transaction_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant)
):
    """
    Get a single transaction by ID.

    Uses eager loading to prevent N+1 queries when accessing alerts.
    """
    # Phase 4C: Tenant-filtered query
    transaction = get_tenant_filtered_query(Transaction, db).options(
        joinedload(Transaction.alerts)
    ).filter(
        Transaction.transaction_id == transaction_id
    ).first()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Phase 4C: Ensure tenant match
    ensure_tenant_match(transaction, tenant_id)

    return transaction


@router.get("/internal/{id}", response_model=TransactionResponse)
def get_transaction_by_internal_id(
    id: int,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant)
):
    """Get a single transaction by internal database ID."""
    # Phase 4C: Tenant-filtered query
    transaction = get_tenant_filtered_query(Transaction, db).filter(
        Transaction.id == id
    ).first()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Phase 4C: Ensure tenant match
    ensure_tenant_match(transaction, tenant_id)

    return transaction


@router.patch("/{transaction_id}", response_model=TransactionResponse)
def update_transaction(
    transaction_id: str,
    update_data: TransactionUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant)
):
    """
    Update transaction fields (typically status or risk assessment).
    """
    # Phase 4C: Tenant-filtered query
    transaction = get_tenant_filtered_query(Transaction, db).filter(
        Transaction.transaction_id == transaction_id
    ).first()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Phase 4C: Ensure tenant match
    ensure_tenant_match(transaction, tenant_id)

    # Update fields
    update_dict = update_data.dict(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(transaction, field, value)

    transaction.updated_at = utc_now()
    record_event(
        db,
        event_type="transaction.updated",
        entity_type="transaction",
        entity_id=transaction.transaction_id,
        payload={"changes": update_dict},
    )
    db.commit()
    db.refresh(transaction)

    return transaction


# ============================================================================
# TRANSACTION ANALYTICS
# ============================================================================

@router.get("/user/{user_id}/history", response_model=List[TransactionResponse])
def get_user_transaction_history(
    user_id: str,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Get transaction history for a specific user.

    Uses eager loading to prevent N+1 queries when accessing alerts.
    """
    start_date = utc_now() - timedelta(days=days)

    # Phase 4C: Tenant-filtered query
    transactions = get_tenant_filtered_query(Transaction, db).options(
        joinedload(Transaction.alerts)
    ).filter(
        and_(
            Transaction.user_id == user_id,
            Transaction.timestamp >= start_date
        )
    ).order_by(Transaction.timestamp.desc()).all()

    return transactions


@router.get("/user/{user_id}/alerts", response_model=List[AlertResponse])
def get_user_alerts(
    user_id: str,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get all alerts for a specific user.

    Uses eager loading to prevent N+1 queries when accessing transactions.
    """
    # Phase 4C: Tenant-filtered query
    query = get_tenant_filtered_query(Alert, db).options(
        joinedload(Alert.transaction)
    ).filter(Alert.user_id == user_id)

    if status:
        query = query.filter(Alert.status == status)

    alerts = query.order_by(Alert.created_at.desc()).all()

    return alerts


@router.get("/statistics/overview", response_model=TransactionStatistics)
def get_transaction_statistics(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Get transaction statistics for the monitoring dashboard.
    """
    start_date = utc_now() - timedelta(days=days)

    # Phase 4C: Use tenant-filtered queries for all statistics
    base_query = get_tenant_filtered_query(Transaction, db)

    # Total transactions and volume
    total_result = base_query.with_entities(
        func.count(Transaction.id).label('count'),
        func.sum(Transaction.amount).label('volume'),
        func.avg(Transaction.amount).label('avg_amount')
    ).filter(Transaction.timestamp >= start_date).first()

    # Transactions by status
    flagged_count = get_tenant_filtered_query(Transaction, db).filter(
        and_(
            Transaction.timestamp >= start_date,
            Transaction.status == 'flagged'
        )
    ).count()

    blocked_count = get_tenant_filtered_query(Transaction, db).filter(
        and_(
            Transaction.timestamp >= start_date,
            Transaction.status == 'blocked'
        )
    ).count()

    high_risk_count = get_tenant_filtered_query(Transaction, db).filter(
        and_(
            Transaction.timestamp >= start_date,
            Transaction.risk_level == 'high'
        )
    ).count()

    # Transactions by country
    country_results = get_tenant_filtered_query(Transaction, db).with_entities(
        Transaction.country_code,
        func.count(Transaction.id).label('count')
    ).filter(
        and_(
            Transaction.timestamp >= start_date,
            Transaction.country_code.isnot(None)
        )
    ).group_by(Transaction.country_code).all()

    transactions_by_country = {
        row.country_code: row.count for row in country_results
    }

    # Transactions by type
    type_results = get_tenant_filtered_query(Transaction, db).with_entities(
        Transaction.transaction_type,
        func.count(Transaction.id).label('count')
    ).filter(
        and_(
            Transaction.timestamp >= start_date,
            Transaction.transaction_type.isnot(None)
        )
    ).group_by(Transaction.transaction_type).all()

    transactions_by_type = {
        row.transaction_type: row.count for row in type_results
    }

    return TransactionStatistics(
        total_transactions=total_result.count or 0,
        total_volume=total_result.volume or 0,
        flagged_transactions=flagged_count or 0,
        blocked_transactions=blocked_count or 0,
        high_risk_transactions=high_risk_count or 0,
        transactions_by_country=transactions_by_country,
        transactions_by_type=transactions_by_type,
        average_transaction_amount=total_result.avg_amount or 0
    )


def calculate_basic_risk_score(transaction: Transaction) -> float:
    """
    Basic risk scoring placeholder.

    Real implementation will use ML models and feature store.
    """
    score = 0.0

    # Amount-based scoring
    if transaction.amount > 10000:
        score += 30
    elif transaction.amount > 5000:
        score += 20
    elif transaction.amount > 1000:
        score += 10

    # Country-based scoring (placeholder)
    high_risk_countries = ['KP', 'IR', 'SY']
    if transaction.country_code in high_risk_countries:
        score += 40

    # Transaction type scoring
    if transaction.transaction_type in ['withdrawal', 'transfer']:
        score += 10

    return min(score, 100.0)
