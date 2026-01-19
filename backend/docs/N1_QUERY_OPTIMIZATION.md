# N+1 Query Optimization Guide

## Overview

N+1 query problems occur when an application makes one query to fetch a list of entities, then makes additional queries for each entity to fetch related data. This can severely impact performance, especially with large datasets.

**Example N+1 Problem:**
```python
# Query 1: Fetch 100 alerts
alerts = db.query(Alert).limit(100).all()

# Queries 2-101: For each alert, fetch its transaction (100 additional queries!)
for alert in alerts:
    print(alert.transaction.amount)  # Lazy loads transaction
```

**Total: 101 queries instead of 1 or 2!**

## Solution: Eager Loading with `joinedload()`

SQLAlchemy's `joinedload()` uses SQL JOINs to fetch related data in a single query:

```python
from sqlalchemy.orm import joinedload

# Single query using LEFT OUTER JOIN
alerts = db.query(Alert).options(
    joinedload(Alert.transaction)
).limit(100).all()

# Now accessing transactions doesn't trigger additional queries
for alert in alerts:
    print(alert.transaction.amount)  # Already loaded!
```

**Total: 1 query!**

## Optimizations Implemented

### Alerts API (`backend/src/api/alerts.py`)

#### 1. `list_alerts()` - Line 60
**Before:**
```python
query = db.query(Alert)
alerts = query.offset(skip).limit(limit).all()
# N+1 problem when accessing alert.transaction
```

**After:**
```python
query = db.query(Alert).options(
    joinedload(Alert.transaction)
)
alerts = query.offset(skip).limit(limit).all()
# All transactions loaded in single query
```

**Impact:** Reduces queries from **1 + N** to **1** (where N = number of alerts)

#### 2. `list_pending_alerts()` - Line 118
Eager loads `transaction` relationship for pending alerts.

#### 3. `list_critical_alerts()` - Line 142
Eager loads `transaction` relationship for critical alerts.

#### 4. `list_sar_filed_alerts()` - Line 361
Eager loads `transaction` relationship for SAR-filed alerts.

### Transactions API (`backend/src/api/transactions.py`)

#### 1. `list_transactions()` - Line 127
**Before:**
```python
query = db.query(Transaction)
transactions = query.offset(skip).limit(limit).all()
# N+1 problem when accessing transaction.alerts
```

**After:**
```python
query = db.query(Transaction).options(
    joinedload(Transaction.alerts)
)
transactions = query.offset(skip).limit(limit).all()
# All alerts loaded in single query
```

**Impact:** For 100 transactions with avg 2 alerts each: **201 queries → 1 query**

#### 2. `get_transaction()` - Line 185
Eager loads `alerts` relationship for single transaction lookup.

#### 3. `get_user_transaction_history()` - Line 244
Eager loads `alerts` for user's transaction history.

#### 4. `get_user_alerts()` - Line 269
Eager loads `transaction` relationship for user's alerts.

### Cases API (`backend/src/api/cases.py`)

#### 1. `get_case_alerts()` - Line 319
Eager loads `transaction` relationship when fetching alerts for a case.

#### 2. `get_case_transactions()` - Line 346
Eager loads `alerts` relationship when fetching transactions for a case.

## Performance Impact

### Example Scenario: Dashboard Loading 100 Alerts

**Before Optimization:**
```
Query 1: SELECT * FROM alerts LIMIT 100                 (1 query)
Query 2-101: SELECT * FROM transactions WHERE id = ?    (100 queries)
---
Total: 101 queries
Estimated time (20ms per query): 2,020ms (2 seconds)
```

**After Optimization:**
```
Query 1: SELECT * FROM alerts
         LEFT OUTER JOIN transactions ON ...
         LIMIT 100                                      (1 query)
---
Total: 1 query
Estimated time: 50ms
```

**Performance Gain: 40x faster (2000ms → 50ms)**

### Example Scenario: User Transaction History (50 transactions, 3 alerts each)

**Before:**
```
Query 1: SELECT * FROM transactions WHERE user_id = ?   (1 query)
Query 2-51: SELECT * FROM alerts WHERE transaction_id = ? (50 queries)
---
Total: 51 queries
Estimated time: 1,020ms
```

**After:**
```
Query 1: SELECT * FROM transactions
         LEFT OUTER JOIN alerts ON ...
         WHERE user_id = ?                              (1 query)
---
Total: 1 query
Estimated time: 80ms
```

**Performance Gain: 12.75x faster**

## When to Use Eager Loading

### ✅ Use `joinedload()` when:
- You **know** you'll access the related data
- The relationship is **one-to-one** or **one-to-few** (e.g., alert → transaction)
- You're loading a **limited number** of parent entities (pagination applied)
- The related data is **small to medium** in size

### ✅ Use `selectinload()` when:
- The relationship is **one-to-many** with **many** children
- You want to avoid cartesian products from JOINs
- You're okay with 2 queries instead of N+1

```python
# Better for one-to-many with many children
query = db.query(Transaction).options(
    selectinload(Transaction.alerts)  # Uses separate IN query
)
```

### ❌ Avoid eager loading when:
- You're **not sure** if related data will be accessed
- Loading **unbounded** collections (could load GBs of data)
- The relationship data is **rarely needed**

## Best Practices

### 1. Always Profile First
Use SQLAlchemy's query logging to identify N+1 issues:

```python
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

### 2. Combine Multiple Relationships
```python
# Load multiple relationships at once
query = db.query(Alert).options(
    joinedload(Alert.transaction),
    joinedload(Alert.rule_hits)
)
```

### 3. Use Pagination
Even with eager loading, limit result sets:

```python
query = db.query(Alert).options(
    joinedload(Alert.transaction)
).limit(100)  # Don't load thousands at once!
```

### 4. Be Aware of Cartesian Products
When eager loading multiple one-to-many relationships, consider `selectinload()`:

```python
# This could create a large cartesian product
query = db.query(Case).options(
    joinedload(Case.related_alerts),    # Many alerts
    joinedload(Case.related_transactions)  # Many transactions
)

# Better approach
query = db.query(Case).options(
    selectinload(Case.related_alerts),
    selectinload(Case.related_transactions)
)
```

### 5. Avoid Over-Fetching
Only load what you need:

```python
# Bad: Loading everything when you only need basic info
alerts = db.query(Alert).options(
    joinedload(Alert.transaction),
    joinedload(Alert.rule_hits),
    joinedload(Alert.regulatory_docs)  # Not needed!
).all()

# Good: Only load what's used
alerts = db.query(Alert).options(
    joinedload(Alert.transaction)  # Only load transaction
).all()
```

## Testing for N+1 Queries

### Manual Testing
```python
from sqlalchemy import event
from sqlalchemy.engine import Engine

query_count = 0

@event.listens_for(Engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, params, context, executemany):
    global query_count
    query_count += 1
    print(f"Query {query_count}: {statement}")

# Test your endpoint
query_count = 0
result = list_alerts(skip=0, limit=10, db=session)
print(f"Total queries: {query_count}")
```

### Expected Results
- **list_alerts(limit=10)**: 1 query (not 11)
- **list_transactions(limit=100)**: 1 query (not 101+)
- **get_user_alerts(user_id)**: 1 query regardless of alert count

## Monitoring in Production

### Add Query Timing Middleware
```python
@app.middleware("http")
async def log_slow_queries(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    if duration > 1.0:  # Log queries taking > 1 second
        logger.warning(
            f"Slow request: {request.url.path} took {duration:.2f}s"
        )

    return response
```

### Database Query Logging
Enable PostgreSQL's `log_min_duration_statement`:

```sql
-- In postgresql.conf
log_min_duration_statement = 100  # Log queries > 100ms
```

## Related Models & Relationships

### Current Relationships
```
Transaction (1) ←→ (N) Alert
    ↓ joinedload(Alert.transaction)
    ↓ joinedload(Transaction.alerts) [use selectinload if many alerts]

Alert (N) ←→ (N) RuleHit
    ↓ selectinload(Alert.rule_hits)

MonitoringRule (1) ←→ (N) RuleHit
    ↓ selectinload(MonitoringRule.hits)
```

## Future Optimizations

- [ ] Add database indexes on foreign keys (Alert.transaction_id, etc.)
- [ ] Implement query result caching for frequently accessed data
- [ ] Add APM (Application Performance Monitoring) for query analysis
- [ ] Consider read replicas for heavy read workloads
- [ ] Implement GraphQL with DataLoader for complex nested queries
- [ ] Add database connection pooling optimization
- [ ] Profile and optimize aggregation queries in statistics endpoints

## References

- [SQLAlchemy Eager Loading](https://docs.sqlalchemy.org/en/14/orm/loading_relationships.html)
- [N+1 Query Problem Explained](https://stackoverflow.com/questions/97197/what-is-the-n1-selects-problem-in-orm-object-relational-mapping)
- [Performance Best Practices](https://docs.sqlalchemy.org/en/14/faq/performance.html)
