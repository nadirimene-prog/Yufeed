# Performance Investigation Runbook

**Last Updated:** 2026-02-06
**Owner:** Platform Engineering Team

---

## Performance SLOs

Reference these targets during investigation:

- API Availability: > 99.9%
- API Latency p95: < 500ms
- Transaction Processing Success: > 99%
- Feature Extraction p95: < 50ms
- Feature Cache Hit Rate: > 95%

---

## Quick Diagnosis

### Step 1: Identify the Symptom

```bash
# Check current SLO status
open https://grafana.yufeed.com/d/slo-overview

# Query current metrics
curl 'http://prometheus.yufeed.com/api/v1/query?query=histogram_quantile(0.95,rate(api_request_duration_seconds_bucket[5m]))' | jq

# Top slow endpoints
kubectl logs -l app=yufeed-api --tail=1000 | grep "duration" | sort -k5 -rn | head -20
```

### Step 2: Identify the Bottleneck

**Database Queries:**
```bash
psql $DATABASE_URL -c "
  SELECT query, calls, total_time, mean_time, max_time
  FROM pg_stat_statements
  WHERE mean_time > 100  -- Queries averaging >100ms
  ORDER BY total_time DESC
  LIMIT 20;"
```

**Cache Performance:**
```bash
# Check hit rate
curl https://api.yufeed.com/metrics | grep -E "cache_hits|cache_misses"

# Redis memory usage
redis-cli -h prod-redis.yufeed.com INFO memory
```

**Feature Extraction:**
```bash
# Check latency
curl 'http://prometheus.yufeed.com/api/v1/query?query=histogram_quantile(0.95,rate(feature_extraction_duration_seconds_bucket[5m]))' | jq

# Check which features are slow
kubectl logs -l app=yufeed-api --tail=1000 | grep "feature_extraction" | grep "duration" | sort -k6 -rn
```

---

## Database Performance

### Identify Slow Queries

```bash
# Current active slow queries
psql $DATABASE_URL -c "
  SELECT pid, now() - query_start AS duration, query, state
  FROM pg_stat_activity
  WHERE state != 'idle'
    AND now() - query_start > interval '1 second'
  ORDER BY duration DESC;"

# Historical slow queries (requires pg_stat_statements)
psql $DATABASE_URL -c "
  SELECT
    substring(query, 1, 100) AS short_query,
    calls,
    total_time::numeric(10,2) AS total_ms,
    mean_time::numeric(10,2) AS mean_ms,
    max_time::numeric(10,2) AS max_ms
  FROM pg_stat_statements
  WHERE mean_time > 50
  ORDER BY mean_time DESC
  LIMIT 20;"
```

### Check Index Usage

```bash
# Missing indexes (sequential scans)
psql $DATABASE_URL -c "
  SELECT schemaname, tablename, seq_scan, seq_tup_read, idx_scan, idx_tup_fetch
  FROM pg_stat_user_tables
  WHERE seq_scan > 1000  -- Table scanned >1000 times
    AND seq_tup_read > 0
  ORDER BY seq_tup_read DESC
  LIMIT 10;"

# Unused indexes (candidates for removal)
psql $DATABASE_URL -c "
  SELECT schemaname, tablename, indexname, idx_scan
  FROM pg_stat_user_indexes
  WHERE idx_scan = 0
  ORDER BY pg_relation_size(indexrelid) DESC;"
```

### Verify Critical Indexes Exist

```bash
# Check transactions table indexes
psql $DATABASE_URL -c "
  SELECT indexname, indexdef
  FROM pg_indexes
  WHERE tablename = 'transactions'
  ORDER BY indexname;"

# Expected indexes:
# - ix_transactions_tenant_user_timestamp (tenant_id, user_id, timestamp)
# - ix_transactions_tenant_timestamp (tenant_id, timestamp)

# If missing, create immediately:
psql $DATABASE_URL -c "
  CREATE INDEX CONCURRENTLY ix_transactions_tenant_user_timestamp
  ON transactions (tenant_id, user_id, timestamp);"
```

### Analyze Query Plans

```bash
# Explain specific slow query
psql $DATABASE_URL -c "
  EXPLAIN ANALYZE
  SELECT COUNT(id) FROM transactions
  WHERE tenant_id = 'test_tenant'
    AND user_id = 'user123'
    AND timestamp >= NOW() - INTERVAL '24 hours';"

# Look for:
# - "Seq Scan" instead of "Index Scan" (BAD)
# - "Index Scan using ix_transactions_tenant_user_timestamp" (GOOD)
# - High "actual time" values
```

---

## Cache Performance

### Check Redis Health

```bash
# Connection test
redis-cli -h prod-redis.yufeed.com ping

# Memory usage
redis-cli -h prod-redis.yufeed.com INFO memory | grep -E "used_memory|maxmemory|evicted_keys"

# Key count
redis-cli -h prod-redis.yufeed.com DBSIZE

# Check for key evictions (cache too small)
redis-cli -h prod-redis.yufeed.com INFO stats | grep evicted_keys
```

### Analyze Cache Hit Rates

```bash
# Feature cache hit rate
curl 'http://prometheus.yufeed.com/api/v1/query?query=sum(rate(cache_hits_total{cache_type="features"}[5m]))/(sum(rate(cache_hits_total{cache_type="features"}[5m]))+sum(rate(cache_misses_total{cache_type="features"}[5m])))' | jq

# If hit rate < 95%:
# 1. Check cache TTL (default 60s)
# 2. Check Redis memory (may be evicting)
# 3. Consider cache warming for active users
```

### Cache Warming Strategy

```bash
# Identify most active users (last 24h)
psql $DATABASE_URL -c "
  SELECT user_id, COUNT(*) as txn_count
  FROM transactions
  WHERE timestamp >= NOW() - INTERVAL '24 hours'
  GROUP BY user_id
  ORDER BY txn_count DESC
  LIMIT 100;"

# Warm cache for top users (run via admin endpoint)
curl -X POST https://api.yufeed.com/admin/cache/warm \
  -H "Content-Type: application/json" \
  -d '{"user_ids": ["user1", "user2", ...], "tenant_id": "tenant123"}'
```

---

## Feature Extraction Performance

### Identify Slow Feature Types

```bash
# Check which features are slow
kubectl logs -l app=yufeed-api --tail=5000 | \
  grep "feature_extraction" | \
  awk '{print $5, $7}' | \
  sort | uniq -c | sort -rn

# Common slow features:
# - velocity calculations (time-windowed aggregates)
# - unique country counts (DISTINCT operations)
```

### Optimize Velocity Calculations

```bash
# Check if indexes exist
psql $DATABASE_URL -c "
  SELECT indexname
  FROM pg_indexes
  WHERE tablename = 'transactions'
    AND indexname LIKE '%tenant%user%timestamp%';"

# If not, create:
psql $DATABASE_URL -c "
  CREATE INDEX CONCURRENTLY ix_transactions_tenant_user_timestamp
  ON transactions (tenant_id, user_id, timestamp);"

# Test query performance after index
psql $DATABASE_URL -c "
  EXPLAIN ANALYZE
  SELECT COUNT(id)
  FROM transactions
  WHERE tenant_id = 'test'
    AND user_id = 'user123'
    AND timestamp >= NOW() - INTERVAL '24 hours';"
```

---

## API Latency Investigation

### Profile Endpoint Performance

```bash
# Check slowest endpoints
curl https://api.yufeed.com/metrics | grep api_request_duration_seconds | sort -k3 -rn | head -20

# Check specific endpoint
curl -w "@curl-format.txt" -o /dev/null -s https://api.yufeed.com/api/transactions

# Where curl-format.txt contains:
# time_namelookup:  %{time_namelookup}s\n
# time_connect:  %{time_connect}s\n
# time_appconnect:  %{time_appconnect}s\n
# time_pretransfer:  %{time_pretransfer}s\n
# time_redirect:  %{time_redirect}s\n
# time_starttransfer:  %{time_starttransfer}s\n
# time_total:  %{time_total}s\n
```

### Check for N+1 Queries

```bash
# Enable query logging temporarily
psql $DATABASE_URL -c "ALTER SYSTEM SET log_min_duration_statement = 10;"  # Log queries > 10ms
psql $DATABASE_URL -c "SELECT pg_reload_conf();"

# Make API request
curl https://api.yufeed.com/api/transactions?limit=10

# Check logs for repeated similar queries
tail -100 /var/log/postgresql/postgresql.log | grep "SELECT" | sort | uniq -c | sort -rn

# Disable logging
psql $DATABASE_URL -c "ALTER SYSTEM RESET log_min_duration_statement;"
psql $DATABASE_URL -c "SELECT pg_reload_conf();"
```

---

## System Resources

### Check CPU/Memory

```bash
# Kubernetes pod resources
kubectl top pods -l app=yufeed-api

# Node resources
kubectl top nodes

# If high CPU:
# - Check for inefficient queries
# - Consider horizontal scaling
# - Profile application (py-spy for Python)

# If high memory:
# - Check for memory leaks
# - Review object caching strategies
# - Check Celery task memory usage
```

### Check Database Connections

```bash
# Active connections by state
psql $DATABASE_URL -c "
  SELECT state, COUNT(*)
  FROM pg_stat_activity
  GROUP BY state;"

# If too many connections:
# 1. Check connection pooling config
# 2. Look for connection leaks (not properly closed)
# 3. Increase max_connections (with caution)
```

---

## Quick Fixes

### Immediate Actions (0-5 minutes)

1. **Scale Horizontally**
   ```bash
   kubectl scale deployment/yufeed-api --replicas=10
   ```

2. **Restart Redis** (if high memory/evictions)
   ```bash
   kubectl rollout restart deployment/yufeed-redis
   ```

3. **Kill Long-Running Queries**
   ```bash
   psql $DATABASE_URL -c "
     SELECT pg_terminate_backend(pid)
     FROM pg_stat_activity
     WHERE state = 'active'
       AND now() - query_start > interval '5 minutes';"
   ```

### Short-Term Actions (5-30 minutes)

1. **Add Missing Indexes**
   ```bash
   psql $DATABASE_URL -c "
     CREATE INDEX CONCURRENTLY idx_name
     ON table_name (column1, column2);"
   ```

2. **Increase Cache TTL** (if high churn)
   ```bash
   # Update FeatureStoreService.CACHE_TTL_SECONDS from 60 to 300
   kubectl set env deployment/yufeed-api FEATURE_CACHE_TTL=300
   ```

3. **Warm Cache**
   ```bash
   curl -X POST https://api.yufeed.com/admin/cache/warm
   ```

### Medium-Term Actions (hours-days)

1. **Query Optimization**
   - Rewrite slow queries with better JOINs
   - Add computed columns for frequently aggregated data
   - Consider materialized views

2. **Application Profiling**
   ```bash
   # Profile with py-spy
   py-spy top --pid <python-process-pid>
   py-spy record -o profile.svg --pid <python-process-pid> --duration 60
   ```

3. **Database Tuning**
   - Review `shared_buffers`, `work_mem`, `effective_cache_size`
   - Enable query plan caching
   - Consider read replicas for analytics queries

---

## References

- [Database Index Documentation](../../docs/engineering/api/DATABASE_INDEXES.md)
- [N+1 Query Optimization](../../docs/engineering/api/N1_QUERY_OPTIMIZATION.md)
- [SLO Definitions](../../monitoring/slos.yml)
- [Incident Response](./incident-response.md)
