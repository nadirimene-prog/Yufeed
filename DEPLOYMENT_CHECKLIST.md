# YuFeed Production Deployment Checklist

**Version:** 2.0.0
**Date:** 2026-02-06
**Purpose:** Production deployment of 9-week hardening program improvements

---

## Pre-Deployment Requirements

### 1. Code Review & Testing ✅

- [x] All code changes reviewed and approved
- [x] Integration tests passing (80%+ coverage)
- [x] Security audit script passing
- [x] No TypeScript errors in frontend
- [x] Linting passing (backend + frontend)

### 2. Database Migrations Ready

- [ ] **Migration 1: AI Usage Tracking**
  ```bash
  # File: alembic/versions/20260206_add_ai_usage_tracking.py
  # Creates: ai_usage_logs, ai_budgets tables
  alembic upgrade 20260206_ai_usage
  ```

- [ ] **Migration 2: Performance Indexes**
  ```bash
  # File: alembic/versions/20260206_add_performance_indexes.py
  # Creates: Composite indexes for transactions, alerts, rules, features
  alembic upgrade 20260206_indexes
  ```

### 3. Configuration Updates

- [ ] **Environment Variables**
  ```bash
  # AI Cost Tracking
  AI_DAILY_COST_THRESHOLD_USD=100.0
  AI_MONTHLY_BUDGET_USD=3000.0

  # Feature Store
  REDIS_URL=redis://localhost:6379/0
  FEATURE_CACHE_TTL_SECONDS=60

  # Monitoring
  PROMETHEUS_URL=http://localhost:9090
  GRAFANA_URL=http://localhost:3000
  ```

- [ ] **AI Cost Config Updated**
  ```python
  # src/ai/cost_tracker.py - AI_COST_CONFIG
  # Verify pricing is current for OpenAI, Anthropic, Azure
  ```

### 4. Monitoring Setup

- [ ] **Prometheus Alert Rules**
  ```bash
  # File: monitoring/prometheus/alerts.yml
  # Verify SLO-based alerts configured
  curl -X POST http://localhost:9090/-/reload
  ```

- [ ] **Grafana Dashboards**
  - [ ] AI Costs dashboard configured
  - [ ] Feature extraction performance dashboard
  - [ ] SLO compliance dashboard
  - [ ] Alert burn rate dashboard

### 5. Documentation Review

- [ ] `/docs/runbooks/deployment.md` reviewed
- [ ] `/docs/runbooks/rollback.md` tested in staging
- [ ] `/docs/runbooks/incident-response.md` team trained
- [ ] `/docs/runbooks/performance.md` bookmarked

---

## Staging Deployment (Required)

### 1. Deploy to Staging

```bash
# 1. Pull latest code
cd /path/to/yufeed
git checkout main
git pull origin main

# 2. Backend deployment
cd apps/api

# 3. Run database migrations
alembic upgrade head

# 4. Verify migrations
alembic current
alembic history | head -10

# 5. Restart API
docker-compose -f docker-compose.staging.yml up -d api

# 6. Frontend deployment
cd ../web
npm install
npm run build
docker-compose -f docker-compose.staging.yml up -d web
```

### 2. Staging Verification (30 minutes)

#### Database Verification
```bash
# Connect to staging database
psql -h staging-db.yufeed.com -U yufeed -d yufeed_staging

# Verify tables exist
\dt ai_usage_logs
\dt ai_budgets

# Verify indexes
\di idx_txn_tenant_user_timestamp
\di idx_feature_tenant_entity

# Check query performance
EXPLAIN ANALYZE
SELECT COUNT(id) FROM transactions
WHERE tenant_id = 'test_tenant'
  AND user_id = 'user_123'
  AND timestamp >= NOW() - INTERVAL '24 hours';

# Should use index scan, not seq scan
```

#### API Health Checks
```bash
# Health endpoint
curl https://staging-api.yufeed.com/health

# API version info
curl https://staging-api.yufeed.com/ | jq '.'

# Metrics endpoint
curl https://staging-api.yufeed.com/metrics | grep -E "(feature_extraction|cache_hit|ai_api)"

# AI cost endpoint (requires auth)
curl -H "Authorization: Bearer $TOKEN" \
  https://staging-api.yufeed.com/api/ai-costs/budget | jq '.'
```

#### Feature Extraction Performance
```bash
# Trigger feature computation via API
curl -X POST https://staging-api.yufeed.com/api/features/compute \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "user_id": "test_user",
    "event_type": "transaction",
    "payload": {"amount": 1000}
  }'

# Check metrics
curl https://staging-api.yufeed.com/metrics | grep feature_extraction_duration_seconds

# Verify p95 < 50ms
curl -s http://staging-prometheus:9090/api/v1/query \
  --data-urlencode 'query=histogram_quantile(0.95, rate(feature_extraction_duration_seconds_bucket[5m]))' | jq '.data.result[0].value[1]'
```

#### Cache Verification
```bash
# Check Redis connection
redis-cli -h staging-redis.yufeed.com ping

# Check cache hit rate
curl -s https://staging-api.yufeed.com/metrics | grep cache_hit

# Verify cache keys
redis-cli -h staging-redis.yufeed.com KEYS "feat:*" | head -5
```

#### AI Cost Tracking Test
```bash
# Trigger AI API call (document analysis)
curl -X POST https://staging-api.yufeed.com/api/documents/analyze \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"document_id": 123}'

# Verify usage logged
psql -h staging-db.yufeed.com -U yufeed -d yufeed_staging -c \
  "SELECT * FROM ai_usage_logs ORDER BY created_at DESC LIMIT 5;"

# Check budget tracking
curl -H "Authorization: Bearer $TOKEN" \
  https://staging-api.yufeed.com/api/ai-costs/budget | jq '.daily'
```

#### Integration Tests
```bash
# Run integration test suite
cd apps/api
pytest tests/integration/ -v

# Verify all pass
pytest tests/integration/ --maxfail=1
```

#### Frontend Verification
```bash
# Check React Query DevTools visible (development mode)
open https://staging-web.yufeed.com/alerts

# Verify pages load without errors
# - /alerts (React Query migration)
# - /monitoring (useMonitoringDashboard)
# - /watchlists (React Query)
# - /compliance/aml-scope (React Query)

# Check browser console for errors
# Verify StatusBadge, RiskLevelBar, LoadingBoundary render correctly

# Lighthouse audit
npm run lighthouse -- --url=https://staging-web.yufeed.com
# Target: Performance >90, Accessibility >95
```

### 3. Staging Sign-Off

- [ ] All database migrations applied successfully
- [ ] All indexes created and used (verified with EXPLAIN)
- [ ] API health checks passing
- [ ] Feature extraction p95 < 50ms
- [ ] Cache hit rate > 50% (will improve to 80% after warm-up)
- [ ] AI cost tracking persisting to database
- [ ] Integration tests passing
- [ ] Frontend pages loading without errors
- [ ] No console errors in browser
- [ ] Prometheus scraping metrics
- [ ] Alert rules loaded

**Sign-off:** _______________ **Date:** ___________

---

## Production Deployment

### Pre-Flight Checklist

- [ ] Staging deployment successful and stable for 24+ hours
- [ ] On-call engineer identified and available
- [ ] Rollback plan reviewed and understood
- [ ] Stakeholders notified of deployment window
- [ ] Maintenance window scheduled (if required)
- [ ] Database backup completed within last hour
- [ ] Production credentials ready and tested

### Deployment Window

**Recommended:** 2-4 AM UTC (low traffic)
**Duration:** 45-60 minutes
**Team:** Minimum 2 engineers

### Step-by-Step Deployment

#### 1. Pre-Deployment Snapshot (t-15 minutes)

```bash
# Take metrics snapshot
curl -s http://production-prometheus:9090/api/v1/query \
  --data-urlencode 'query=rate(http_requests_total[5m])' > /tmp/pre_deploy_metrics.json

# Check current error rate
curl -s http://production-prometheus:9090/api/v1/query \
  --data-urlencode 'query=rate(http_requests_total{status=~"5.."}[5m])'

# Record baseline
echo "Baseline recorded at $(date)" >> /tmp/deployment_log.txt
```

#### 2. Enable Read-Only Mode (t-10 minutes)

```bash
# Optional: Enable read-only mode during migration
curl -X POST http://production-api:8000/admin/read-only-mode \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Verify
curl http://production-api:8000/health | jq '.read_only'
```

#### 3. Database Migrations (t-5 minutes)

```bash
# Connect to production database
cd /path/to/yufeed/apps/api

# CRITICAL: Verify current migration state
alembic current

# Run migrations
alembic upgrade head

# Verify success
alembic current
# Should show: 20260206_indexes (current)

# Verify indexes created
psql -h production-db -U yufeed -d yufeed_production -c "
SELECT indexname, tablename
FROM pg_indexes
WHERE indexname LIKE 'idx_%'
ORDER BY tablename, indexname;
"

# Should see:
# - idx_txn_tenant_user_timestamp
# - idx_ai_usage_tenant_created
# - idx_feature_tenant_entity
# etc.
```

#### 4. Deploy API (t0 - Rolling Restart)

```bash
# Tag release
git tag -a v2.0.0 -m "Release 2.0.0: Hardening program complete"
git push origin v2.0.0

# Build production image
docker build -t yufeed-api:v2.0.0 .
docker tag yufeed-api:v2.0.0 yufeed-api:latest
docker push yufeed-api:v2.0.0
docker push yufeed-api:latest

# Rolling restart (zero downtime)
for i in {1..3}; do
  kubectl set image deployment/yufeed-api api=yufeed-api:v2.0.0
  kubectl rollout status deployment/yufeed-api
  sleep 30

  # Health check
  curl -f http://production-api:8000/health || exit 1
done

# Disable read-only mode
curl -X POST http://production-api:8000/admin/read-only-mode/disable \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

#### 5. Deploy Frontend (t+10 minutes)

```bash
cd apps/web

# Build production bundle
npm run build

# Deploy
docker build -t yufeed-web:v2.0.0 .
docker tag yufeed-web:v2.0.0 yufeed-web:latest
docker push yufeed-web:v2.0.0

# Rolling restart
kubectl set image deployment/yufeed-web web=yufeed-web:v2.0.0
kubectl rollout status deployment/yufeed-web
```

#### 6. Reload Prometheus (t+15 minutes)

```bash
# Reload alert rules
curl -X POST http://production-prometheus:9090/-/reload

# Verify new alerts loaded
curl http://production-prometheus:9090/api/v1/rules | jq '.data.groups[].rules[].name' | grep -i "slo"

# Should see:
# - "APIAvailabilitySLOBreach"
# - "FeatureExtractionLatencySLOBreach"
# etc.
```

### Post-Deployment Verification (t+20 to t+60 minutes)

#### Immediate Checks (First 5 minutes)

```bash
# API health
curl https://api.yufeed.com/health | jq '.'

# Version verification
curl https://api.yufeed.com/ | jq '.api_versions'
# Should show v1 and current

# Metrics scraping
curl https://api.yufeed.com/metrics | grep -E "(feature_extraction|ai_api_cost|cache_hit)" | head -10

# Error rate
curl -s http://production-prometheus:9090/api/v1/query \
  --data-urlencode 'query=rate(http_requests_total{status=~"5.."}[5m])'
# Should be <0.001 (0.1%)

# Latency p95
curl -s http://production-prometheus:9090/api/v1/query \
  --data-urlencode 'query=histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))'
# Should be <0.5s
```

#### Feature Store Verification (10 minutes)

```bash
# Trigger feature computation
curl -X POST https://api.yufeed.com/api/features/compute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "prod_user_1", "event_type": "transaction", "payload": {}}'

# Check metrics
curl https://api.yufeed.com/metrics | grep feature_extraction_duration_seconds

# Verify cache working
curl https://api.yufeed.com/metrics | grep feature_cache_hits_total

# Check performance in Grafana
open https://grafana.yufeed.com/d/features-dashboard
```

#### AI Cost Tracking Verification (15 minutes)

```bash
# Check budget status
curl -H "Authorization: Bearer $TOKEN" \
  https://api.yufeed.com/api/ai-costs/budget | jq '.'

# Verify database persistence
psql -h production-db -U yufeed -d yufeed_production -c \
  "SELECT COUNT(*) FROM ai_usage_logs WHERE created_at > NOW() - INTERVAL '1 hour';"

# Trigger AI API call
curl -X POST https://api.yufeed.com/api/documents/analyze \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"document_id": 456}'

# Verify logged
psql -h production-db -U yufeed -d yufeed_production -c \
  "SELECT provider, model, estimated_cost_usd FROM ai_usage_logs ORDER BY created_at DESC LIMIT 3;"

# Check Prometheus metric
curl https://api.yufeed.com/metrics | grep ai_api_cost_usd
```

#### Integration Test (20 minutes)

```bash
# Run production smoke tests
cd apps/api
pytest tests/smoke/ --base-url=https://api.yufeed.com -v

# Should all pass
```

#### Frontend Verification (25 minutes)

```bash
# Test key pages
open https://app.yufeed.com/alerts
open https://app.yufeed.com/monitoring
open https://app.yufeed.com/watchlists

# Check browser console - no errors expected

# React Query DevTools (if in dev mode)
# Verify queries cached correctly

# Lighthouse audit
npm run lighthouse -- --url=https://app.yufeed.com
```

#### SLO Compliance Check (30 minutes)

```bash
# Check SLO dashboard
open https://grafana.yufeed.com/d/slo-dashboard

# API Availability (99.9% target)
curl -s http://production-prometheus:9090/api/v1/query \
  --data-urlencode 'query=(sum(rate(http_requests_total{status!~"5.."}[5m])) / sum(rate(http_requests_total[5m])))' | jq '.data.result[0].value[1]'

# Should be >0.999

# API Latency p95 (<500ms target)
curl -s http://production-prometheus:9090/api/v1/query \
  --data-urlencode 'query=histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))' | jq '.data.result[0].value[1]'

# Should be <0.5

# Transaction Processing Success (99% target)
curl -s http://production-prometheus:9090/api/v1/query \
  --data-urlencode 'query=(sum(rate(transaction_processing_total{status="success"}[5m])) / sum(rate(transaction_processing_total[5m])))' | jq '.data.result[0].value[1]'

# Should be >0.99
```

### Monitoring Period (1 hour)

#### Key Metrics to Watch

```bash
# Watch error rate (should stay <0.1%)
watch -n 30 'curl -s http://production-prometheus:9090/api/v1/query \
  --data-urlencode "query=rate(http_requests_total{status=~\"5..\"}[5m])" | jq ".data.result[0].value[1]"'

# Watch latency (should stay <500ms p95)
watch -n 30 'curl -s http://production-prometheus:9090/api/v1/query \
  --data-urlencode "query=histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))" | jq ".data.result[0].value[1]"'

# Watch feature extraction performance (should stay <50ms p95)
watch -n 30 'curl -s http://production-prometheus:9090/api/v1/query \
  --data-urlencode "query=histogram_quantile(0.95, rate(feature_extraction_duration_seconds_bucket[5m]))" | jq ".data.result[0].value[1]"'

# Watch cache hit rate (should reach >80% after warm-up)
watch -n 60 'curl https://api.yufeed.com/metrics | grep cache_hit_rate'
```

#### Alert Dashboard

```bash
# Check firing alerts
curl http://production-prometheus:9090/api/v1/alerts | jq '.data.alerts[] | select(.state=="firing")'

# Should be empty or only informational alerts
```

#### Log Monitoring

```bash
# Watch API logs
kubectl logs -f deployment/yufeed-api --tail=100 | grep -E "(ERROR|WARN)"

# Watch for specific issues
kubectl logs -f deployment/yufeed-api | grep -i "tenant"
kubectl logs -f deployment/yufeed-api | grep -i "feature"
kubectl logs -f deployment/yufeed-api | grep -i "cost"
```

---

## Post-Deployment

### 1-Hour Post-Deployment Checklist

- [ ] Error rate <0.1% consistently
- [ ] API latency p95 <500ms
- [ ] Feature extraction p95 <50ms
- [ ] Cache hit rate increasing (target 80% after 24h)
- [ ] No critical alerts firing
- [ ] Transaction processing success >99%
- [ ] AI cost tracking recording usage
- [ ] Frontend pages loading without errors
- [ ] User reports: No major issues

### 24-Hour Monitoring Plan

**Hours 1-4:** Active monitoring (engineer on-call)
- Check metrics every 30 minutes
- Review error logs hourly
- Verify SLO compliance

**Hours 4-24:** Passive monitoring
- Rely on Prometheus alerts
- Review dashboards every 4 hours
- On-call engineer available

### 7-Day Follow-Up

- [ ] Review all alerts triggered
- [ ] Analyze performance trends
- [ ] Check AI cost against budget
- [ ] Review cache effectiveness
- [ ] Collect user feedback
- [ ] Schedule retrospective

### Success Criteria

✅ **Deployment Successful If:**
- Error rate <0.1% for 24 hours
- No critical alerts for 24 hours
- All SLOs met continuously
- Feature extraction p95 <50ms
- Cache hit rate >70% (target 80% by day 7)
- AI costs tracked accurately
- No user-reported critical bugs

---

## Rollback Procedure

### Immediate Rollback Triggers

**ROLLBACK IMMEDIATELY IF:**
- Error rate >5% for 5+ minutes
- API latency p95 >2s for 10+ minutes
- Database corruption detected
- Critical security vulnerability discovered
- SLO burn rate >14.4x (fast burn)

### Rollback Steps

See `/docs/runbooks/rollback.md` for complete procedure.

**Quick Rollback:**
```bash
# 1. Revert API
kubectl rollout undo deployment/yufeed-api

# 2. Revert frontend
kubectl rollout undo deployment/yufeed-web

# 3. Revert database migrations (if needed)
alembic downgrade -1

# 4. Verify
curl https://api.yufeed.com/health
curl https://api.yufeed.com/ | jq '.version'
```

---

## Communication Plan

### Pre-Deployment

**24 hours before:**
- Email all stakeholders with deployment window
- Post in #engineering channel

**1 hour before:**
- Post in #engineering and #alerts
- Notify on-call team
- Set status page to "Maintenance Scheduled"

### During Deployment

**Start:**
- Post "Deployment in progress" in #engineering
- Update status page to "Maintenance"

**Completion:**
- Post "Deployment complete, monitoring" in #engineering
- Update status page to "All Systems Operational"

### Post-Deployment

**1 hour after:**
- Post metrics summary in #engineering
- Email stakeholders if successful

**Issues:**
- Post immediately in #incidents
- Follow incident response runbook
- Email stakeholders with status updates

---

## Appendix

### Key Contacts

- **Deployment Lead:** _______________
- **Database Admin:** _______________
- **On-Call Engineer:** _______________
- **Product Owner:** _______________

### Key URLs

- **Production API:** https://api.yufeed.com
- **Production Web:** https://app.yufeed.com
- **Prometheus:** https://prometheus.yufeed.com
- **Grafana:** https://grafana.yufeed.com
- **Status Page:** https://status.yufeed.com

### Emergency Contacts

- **PagerDuty:** +1-XXX-XXX-XXXX
- **Slack:** #incidents
- **Email:** oncall@yufeed.com

---

**Deployment Sign-Off**

- [ ] Pre-deployment checklist complete
- [ ] Staging verification successful
- [ ] Production deployment successful
- [ ] Post-deployment verification complete
- [ ] Monitoring period complete
- [ ] No rollback required

**Deployed By:** _______________ **Date:** ___________ **Time:** ___________

**Verified By:** _______________ **Date:** ___________ **Time:** ___________

---

**End of Checklist**
