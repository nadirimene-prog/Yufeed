# Database Indexes Guide

## Overview

Database indexes are critical for query performance. They allow the database to quickly locate rows without scanning the entire table. This guide documents all indexes in the Yufeed application and explains their purpose.

## Index Strategy

### When to Add Indexes

✅ **Add indexes on columns that are:**
- Used in WHERE clauses frequently
- Used in JOIN conditions
- Used in ORDER BY clauses
- Used in GROUP BY clauses
- Foreign keys (for referential integrity and joins)
- Columns with high cardinality (many unique values)

❌ **Avoid indexes on:**
- Columns rarely used in queries
- Columns with low cardinality (few unique values, like boolean)
- Small tables (<1000 rows)
- Columns that are frequently updated (indexes slow down writes)

### Composite Indexes

Composite (multi-column) indexes are used for queries that filter on multiple columns:

```sql
-- Composite index on (user_id, status)
CREATE INDEX ix_alerts_user_status ON alerts(user_id, status);

-- Benefits query:
SELECT * FROM alerts WHERE user_id = 'user123' AND status = 'pending';
```

**Important:** Column order matters! Put the most selective column first.

## Transactions Table Indexes

### Single-Column Indexes

| Column | Index Name | Purpose | Example Query |
|--------|-----------|---------|---------------|
| `id` | PRIMARY KEY | Auto-indexed (primary key) | - |
| `transaction_id` | `ix_transactions_transaction_id` | Unique lookups by transaction ID | `WHERE transaction_id = 'TXN-001'` |
| `user_id` | `ix_transactions_user_id` | Filter transactions by user | `WHERE user_id = 'user123'` |
| `timestamp` | `ix_transactions_timestamp` | Date range queries, sorting | `WHERE timestamp >= '2024-01-01'` |
| `country_code` | `ix_transactions_country_code` | Geographic filtering | `WHERE country_code = 'US'` |
| `risk_level` | `ix_transactions_risk_level` | Risk-based filtering | `WHERE risk_level = 'high'` |

### Composite Indexes

| Columns | Index Name | Purpose | Example Query |
|---------|-----------|---------|---------------|
| `user_id, timestamp` | `ix_transactions_user_timestamp` | User transaction history queries | `WHERE user_id = 'user123' AND timestamp >= '2024-01-01' ORDER BY timestamp DESC` |

### Query Examples

```python
# Uses ix_transactions_user_id
transactions = db.query(Transaction).filter(
    Transaction.user_id == 'user123'
).all()

# Uses ix_transactions_user_timestamp (composite index)
transactions = db.query(Transaction).filter(
    and_(
        Transaction.user_id == 'user123',
        Transaction.timestamp >= start_date
    )
).order_by(Transaction.timestamp.desc()).all()

# Uses ix_transactions_risk_level
high_risk_txns = db.query(Transaction).filter(
    Transaction.risk_level == 'high'
).all()
```

## Alerts Table Indexes

### Single-Column Indexes

| Column | Index Name | Purpose | Example Query |
|--------|-----------|---------|---------------|
| `id` | PRIMARY KEY | Auto-indexed (primary key) | - |
| `alert_id` | `ix_alerts_alert_id` | Unique lookups by alert ID | `WHERE alert_id = 'ALT-001'` |
| `user_id` | `ix_alerts_user_id` | Filter alerts by user | `WHERE user_id = 'user123'` |
| `transaction_id` | `ix_alerts_transaction_id` | **Foreign key join optimization** | `JOIN transactions ON...` |
| `status` | `ix_alerts_status` | Status filtering (pending, resolved, etc.) | `WHERE status = 'pending'` |
| `assigned_to` | `ix_alerts_assigned_to` | Assignment queries | `WHERE assigned_to = 'analyst@example.com'` |
| `sar_filed` | `ix_alerts_sar_filed` | SAR filing queries | `WHERE sar_filed = true` |
| `created_at` | `ix_alerts_created_at` | Date range queries, sorting | `WHERE created_at >= '2024-01-01'` |

### Composite Indexes

| Columns | Index Name | Purpose | Example Query |
|---------|-----------|---------|---------------|
| `status, severity` | `ix_alerts_status_severity` | Status + severity filtering | `WHERE status = 'pending' AND severity = 'critical'` |
| `user_id, status` | `ix_alerts_user_status` | User's alerts by status | `WHERE user_id = 'user123' AND status = 'pending'` |

### Query Examples

```python
# Uses ix_alerts_status
pending_alerts = db.query(Alert).filter(
    Alert.status == 'pending'
).all()

# Uses ix_alerts_status_severity (composite index)
critical_pending = db.query(Alert).filter(
    and_(
        Alert.status == 'pending',
        Alert.severity == 'critical'
    )
).all()

# Uses ix_alerts_user_status (composite index)
user_pending_alerts = db.query(Alert).filter(
    and_(
        Alert.user_id == 'user123',
        Alert.status == 'pending'
    )
).all()

# Uses ix_alerts_transaction_id (for join)
alert_with_txn = db.query(Alert).options(
    joinedload(Alert.transaction)  # Uses ix_alerts_transaction_id
).filter(Alert.alert_id == 'ALT-001').first()
```

## Cases Table Indexes

### Single-Column Indexes

| Column | Index Name | Purpose | Example Query |
|--------|-----------|---------|---------------|
| `id` | PRIMARY KEY | Auto-indexed (primary key) | - |
| `case_id` | `ix_cases_case_id` | Unique lookups by case ID | `WHERE case_id = 'CASE-001'` |
| `subject_id` | `ix_cases_subject_id` | Filter cases by subject | `WHERE subject_id = 'user123'` |
| `status` | `ix_cases_status` | Status filtering | `WHERE status = 'open'` |
| `priority` | `ix_cases_priority` | Priority filtering and sorting | `WHERE priority = 'high' ORDER BY priority` |
| `assigned_to` | `ix_cases_assigned_to` | Assignment queries | `WHERE assigned_to = 'analyst@example.com'` |

### Query Examples

```python
# Uses ix_cases_status
open_cases = db.query(Case).filter(
    Case.status == 'open'
).all()

# Uses ix_cases_assigned_to
my_cases = db.query(Case).filter(
    Case.assigned_to == 'analyst@example.com'
).all()

# Uses ix_cases_priority (for sorting)
high_priority_cases = db.query(Case).filter(
    Case.status == 'open'
).order_by(Case.priority.desc()).all()
```

## Performance Impact

### Before Indexes
```sql
-- Query: Find pending alerts for user (sequential scan)
EXPLAIN SELECT * FROM alerts WHERE user_id = 'user123' AND status = 'pending';

Seq Scan on alerts  (cost=0.00..1875.00 rows=10 width=...)
  Filter: ((user_id = 'user123') AND (status = 'pending'))
  Rows Removed by Filter: 49990
Planning Time: 0.123 ms
Execution Time: 45.678 ms  ← Slow!
```

### After Composite Index
```sql
-- Query: Find pending alerts for user (index scan)
EXPLAIN SELECT * FROM alerts WHERE user_id = 'user123' AND status = 'pending';

Index Scan using ix_alerts_user_status on alerts  (cost=0.29..8.31 rows=10 width=...)
  Index Cond: ((user_id = 'user123') AND (status = 'pending'))
Planning Time: 0.098 ms
Execution Time: 0.234 ms  ← 195x faster!
```

## Index Maintenance

### Creating Indexes (via Alembic Migration)

```bash
# Run migration to create indexes
cd backend
alembic upgrade head
```

### Checking Index Usage (PostgreSQL)

```sql
-- See all indexes on a table
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'alerts';

-- Check index size
SELECT
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE tablename IN ('transactions', 'alerts', 'cases')
ORDER BY pg_relation_size(indexrelid) DESC;

-- Check index usage statistics
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan AS index_scans,
    idx_tup_read AS tuples_read,
    idx_tup_fetch AS tuples_fetched
FROM pg_stat_user_indexes
WHERE tablename IN ('transactions', 'alerts', 'cases')
ORDER BY idx_scan DESC;
```

### Finding Unused Indexes

```sql
-- Find indexes that are never used
SELECT
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE idx_scan = 0  -- Never used
  AND indexrelname NOT LIKE '%_pkey'  -- Exclude primary keys
  AND tablename IN ('transactions', 'alerts', 'cases');
```

### Rebuilding Indexes (if corrupted or bloated)

```sql
-- Rebuild a specific index
REINDEX INDEX CONCURRENTLY ix_alerts_status;

-- Rebuild all indexes on a table
REINDEX TABLE CONCURRENTLY alerts;
```

## Index Cost Analysis

### Storage Cost
Each index requires disk space. Estimate:
- **Single-column index**: ~10-30% of table size
- **Composite index**: ~15-40% of table size
- **JSONB index (GIN)**: ~50-100% of table size

### Write Cost
Indexes slow down INSERT, UPDATE, and DELETE operations because the index must be updated.

**Rule of Thumb:**
- **Heavy reads, light writes** (monitoring dashboards): Add more indexes
- **Heavy writes** (transaction ingestion): Be selective with indexes

## Index Best Practices

### 1. Index Selectivity
Prefer columns with high selectivity (many unique values):

```python
# Good: user_id has high selectivity
# Index is effective
SELECT * FROM transactions WHERE user_id = 'user123';

# Bad: status has low selectivity (only 3-5 values)
# Index on status alone is less effective
SELECT * FROM transactions WHERE status = 'completed';
```

### 2. Composite Index Column Order

**Most selective column first:**

```sql
-- Good: user_id is more selective than status
CREATE INDEX ix_alerts_user_status ON alerts(user_id, status);

-- Benefits:
SELECT * FROM alerts WHERE user_id = 'user123';  ✓ Uses index
SELECT * FROM alerts WHERE user_id = 'user123' AND status = 'pending';  ✓ Uses index

-- Less effective for:
SELECT * FROM alerts WHERE status = 'pending';  ? May not use index
```

### 3. Covering Indexes
Include all columns needed by the query to avoid table lookups:

```sql
-- Query needs: alert_id, status, severity, created_at
CREATE INDEX ix_alerts_covering ON alerts(status, severity, alert_id, created_at);

-- Database can satisfy query entirely from index (index-only scan)
SELECT alert_id, severity, created_at
FROM alerts
WHERE status = 'pending' AND severity = 'critical';
```

### 4. Partial Indexes
Index only a subset of rows:

```sql
-- Only index pending alerts (most frequently queried)
CREATE INDEX ix_alerts_pending ON alerts(user_id, created_at)
WHERE status = 'pending';
```

## Monitoring Query Performance

### Enable Query Logging (Development)

```python
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

### EXPLAIN ANALYZE

```python
from sqlalchemy import text

# Get query plan
result = db.execute(text("""
    EXPLAIN ANALYZE
    SELECT * FROM alerts
    WHERE user_id = :user_id AND status = :status
"""), {"user_id": "user123", "status": "pending"})

for row in result:
    print(row)
```

### Slow Query Detection

```python
import time
from sqlalchemy import event
from sqlalchemy.engine import Engine

@event.listens_for(Engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, params, context, executemany):
    context._query_start_time = time.time()

@event.listens_for(Engine, "after_cursor_execute")
def receive_after_cursor_execute(conn, cursor, statement, params, context, executemany):
    total = time.time() - context._query_start_time
    if total > 0.1:  # Log queries > 100ms
        logger.warning(f"Slow query ({total:.2f}s): {statement}")
```

## Migration History

| Migration ID | Description | Date |
|-------------|-------------|------|
| `b059980f41d9` | Critical performance indexes for legal_documents | 2026-01-08 |
| `d123abc45678` | Transaction monitoring indexes | 2026-01-19 |

## Related Documentation

- [N+1 Query Optimization](./N1_QUERY_OPTIMIZATION.md)
- [Database Schema](./DATABASE_SCHEMA.md)
- [Performance Tuning Guide](./PERFORMANCE_TUNING.md)

## References

- [PostgreSQL Index Types](https://www.postgresql.org/docs/current/indexes-types.html)
- [SQLAlchemy Indexing](https://docs.sqlalchemy.org/en/14/core/constraints.html#indexes)
- [Index Monitoring](https://www.postgresql.org/docs/current/pgstatstatements.html)
