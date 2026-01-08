"""
Transaction Monitoring API Endpoints
Handles transaction ingestion, querying, and risk assessment.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_
from typing import List, Optional
from datetime import datetime, timedelta
import uuid

from src.database import get_db
from src.models.transaction_models import (
    Transaction, Alert, Case, MonitoringRule,
    UserRiskProfile, FeatureValue
)
from src.schemas.transaction_schemas import (
    TransactionCreate, TransactionUpdate, TransactionResponse,
    AlertResponse, UserRiskProfileResponse,
    TransactionStatistics
)

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
    # Check for duplicate transaction_id
    existing = db.query(Transaction).filter(
        Transaction.transaction_id == transaction.transaction_id
    ).first()

    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Transaction {transaction.transaction_id} already exists"
        )

    # Create transaction record
    db_transaction = Transaction(**transaction.dict())
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)

    # Trigger background processing
    background_tasks.add_task(process_transaction, db_transaction.id, db)

    return db_transaction


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

    # Check for duplicates
    transaction_ids = [t.transaction_id for t in transactions]
    existing_ids = db.query(Transaction.transaction_id).filter(
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
    db.bulk_save_objects(db_transactions, return_defaults=True)
    db.commit()

    # Trigger background processing for each transaction
    for db_transaction in db_transactions:
        background_tasks.add_task(process_transaction, db_transaction.id, db)

    # Refresh to get all fields
    created_ids = [t.id for t in db_transactions]
    results = db.query(Transaction).filter(Transaction.id.in_(created_ids)).all()

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
    """
    query = db.query(Transaction)

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
    db: Session = Depends(get_db)
):
    """Get a single transaction by ID."""
    transaction = db.query(Transaction).filter(
        Transaction.transaction_id == transaction_id
    ).first()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return transaction


@router.get("/internal/{id}", response_model=TransactionResponse)
def get_transaction_by_internal_id(
    id: int,
    db: Session = Depends(get_db)
):
    """Get a single transaction by internal database ID."""
    transaction = db.query(Transaction).filter(Transaction.id == id).first()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return transaction


@router.patch("/{transaction_id}", response_model=TransactionResponse)
def update_transaction(
    transaction_id: str,
    update_data: TransactionUpdate,
    db: Session = Depends(get_db)
):
    """
    Update transaction fields (typically status or risk assessment).
    """
    transaction = db.query(Transaction).filter(
        Transaction.transaction_id == transaction_id
    ).first()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Update fields
    update_dict = update_data.dict(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(transaction, field, value)

    transaction.updated_at = datetime.utcnow()
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
    """
    start_date = datetime.utcnow() - timedelta(days=days)

    transactions = db.query(Transaction).filter(
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
    """
    query = db.query(Alert).filter(Alert.user_id == user_id)

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
    start_date = datetime.utcnow() - timedelta(days=days)

    # Total transactions and volume
    total_result = db.query(
        func.count(Transaction.id).label('count'),
        func.sum(Transaction.amount).label('volume'),
        func.avg(Transaction.amount).label('avg_amount')
    ).filter(Transaction.timestamp >= start_date).first()

    # Transactions by status
    flagged_count = db.query(func.count(Transaction.id)).filter(
        and_(
            Transaction.timestamp >= start_date,
            Transaction.status == 'flagged'
        )
    ).scalar()

    blocked_count = db.query(func.count(Transaction.id)).filter(
        and_(
            Transaction.timestamp >= start_date,
            Transaction.status == 'blocked'
        )
    ).scalar()

    high_risk_count = db.query(func.count(Transaction.id)).filter(
        and_(
            Transaction.timestamp >= start_date,
            Transaction.risk_level == 'high'
        )
    ).scalar()

    # Transactions by country
    country_results = db.query(
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
    type_results = db.query(
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


# ============================================================================
# BACKGROUND PROCESSING
# ============================================================================

def process_transaction(transaction_id: int, db: Session):
    """
    Background task to process a transaction:
    1. Calculate risk score
    2. Evaluate monitoring rules
    3. Update user risk profile
    4. Generate alerts if needed

    NOTE: This is a placeholder. Full implementation will be in the
    rules engine and risk scoring services.
    """
    transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id
    ).first()

    if not transaction:
        return

    # Placeholder: Basic risk scoring
    # TODO: Implement full risk scoring service
    risk_score = calculate_basic_risk_score(transaction)
    transaction.risk_score = risk_score

    if risk_score < 30:
        transaction.risk_level = 'low'
    elif risk_score < 60:
        transaction.risk_level = 'medium'
    elif risk_score < 80:
        transaction.risk_level = 'high'
    else:
        transaction.risk_level = 'critical'

    db.commit()

    # TODO: Evaluate monitoring rules
    # TODO: Update user risk profile
    # TODO: Generate alerts


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
