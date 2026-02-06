# Deployment Runbook

**Last Updated:** 2026-02-06
**Owner:** Platform Engineering Team
**On-Call Contact:** Check PagerDuty rotation

---

## Overview

This runbook covers the standard deployment process for YuFeed platform components. Follow these steps for safe, monitored deployments with quick rollback capability.

---

## Pre-Deployment Checklist

Before initiating deployment, verify:

- [ ] All tests passing in CI/CD (GitHub Actions)
- [ ] Staging deployment successful and verified
- [ ] Database migrations reviewed and tested
- [ ] Breaking changes documented and communicated
- [ ] Feature flags configured (if applicable)
- [ ] Rollback plan documented
- [ ] On-call engineer identified and available
- [ ] Stakeholders notified (if customer-facing changes)
- [ ] Backup of current production state captured

---

## Deployment Timing

**Preferred Window:** Tuesday-Thursday, 2:00 AM - 4:00 AM UTC
**Rationale:** Low traffic period, full team available during business hours for monitoring

**Avoid:**
- Fridays (limited support weekend coverage)
- Mondays (post-weekend catchup)
- During known high-traffic events
- Holiday periods

---

## Step 1: Deploy to Staging

### 1.1 Pull Latest Code

```bash
cd /Users/imenenadir/Documents/Yufeed
git checkout main
git pull origin main

# Verify you're on the correct commit
git log -1 --oneline
```

### 1.2 Build Backend API

```bash
cd apps/api

# Build Docker image
docker build -t yufeed-api:staging-$(git rev-parse --short HEAD) .

# Tag as latest staging
docker tag yufeed-api:staging-$(git rev-parse --short HEAD) yufeed-api:staging

# Push to registry
docker push yufeed-api:staging-$(git rev-parse --short HEAD)
docker push yufeed-api:staging
```

### 1.3 Run Database Migrations (Staging)

```bash
# Connect to staging database
export DATABASE_URL="postgresql://user:pass@staging-db.yufeed.com:5432/yufeed"

# Check current migration status
alembic current

# Dry-run migration (if available)
alembic upgrade head --sql > migration_preview.sql
cat migration_preview.sql  # Review changes

# Apply migration
alembic upgrade head

# Verify migration applied
alembic current
```

### 1.4 Deploy API to Staging

```bash
# Update docker-compose or k8s deployment
cd /deployment/staging

# Rolling restart
docker-compose up -d api

# Or for Kubernetes
kubectl set image deployment/yufeed-api api=yufeed-api:staging-$(git rev-parse --short HEAD)
kubectl rollout status deployment/yufeed-api
```

### 1.5 Deploy Frontend to Staging

```bash
cd apps/web

# Build production bundle
npm run build

# Deploy to staging environment (method depends on hosting)
# Example for Vercel:
vercel --prod --env staging

# Example for Docker:
docker build -t yufeed-web:staging .
docker push yufeed-web:staging
```

---

## Step 2: Verify Staging Deployment

### 2.1 Health Checks

```bash
# API health endpoint
curl https://staging-api.yufeed.com/health
# Expected: {"status": "healthy", "version": "..."}

# Database connectivity
curl https://staging-api.yufeed.com/health/db
# Expected: {"status": "connected", "latency_ms": <50}

# Redis connectivity
curl https://staging-api.yufeed.com/health/redis
# Expected: {"status": "connected"}

# Frontend health
curl https://staging.yufeed.com
# Expected: 200 OK with HTML
```

### 2.2 Run Smoke Tests

```bash
cd apps/api

# Run critical path smoke tests
pytest tests/smoke/ --base-url=https://staging-api.yufeed.com -v

# Expected: All tests pass
```

### 2.3 Check Metrics

```bash
# Query Prometheus for error rate
curl -s 'http://prometheus.yufeed.com/api/v1/query?query=rate(api_request_duration_seconds_count{status=~"5.."}[5m])' | jq

# Check feature extraction latency
curl -s 'http://prometheus.yufeed.com/api/v1/query?query=histogram_quantile(0.95,rate(feature_extraction_duration_seconds_bucket[5m]))' | jq

# Verify cache hit rate
curl -s 'http://prometheus.yufeed.com/api/v1/query?query=sum(rate(cache_hits_total[5m]))/(sum(rate(cache_hits_total[5m]))+sum(rate(cache_misses_total[5m])))' | jq
```

### 2.4 Manual QA

- [ ] Login flow works
- [ ] Transaction ingestion works
- [ ] Alert creation triggers correctly
- [ ] Feature store returns non-stub data
- [ ] WebSocket real-time updates functional
- [ ] Critical user journeys complete successfully

---

## Step 3: Production Deployment

### 3.1 Enable Read-Only Mode (if migrations required)

```bash
# Set API to read-only to prevent writes during migration
curl -X POST https://api.yufeed.com/admin/read-only-mode \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"enabled": true, "reason": "Deployment in progress"}'

# Verify read-only mode active
curl https://api.yufeed.com/health | jq '.read_only'
# Expected: true
```

### 3.2 Run Database Migrations (Production)

```bash
# Connect to production database (use read replica for safety check)
export DATABASE_URL="postgresql://user:pass@prod-db.yufeed.com:5432/yufeed"

# CRITICAL: Backup database first
pg_dump -h prod-db.yufeed.com -U user -d yufeed -F c -b -v -f "backup_$(date +%Y%m%d_%H%M%S).dump"

# Check current migration
alembic current

# Apply migration with monitoring
alembic upgrade head 2>&1 | tee migration_prod.log

# Verify migration successful
alembic current
tail -20 migration_prod.log
```

### 3.3 Deploy API (Rolling Restart)

```bash
cd /deployment/production

# Tag production release
git tag -a v$(date +%Y.%m.%d)-$(git rev-parse --short HEAD) -m "Production deployment $(date)"
git push origin v$(date +%Y.%m.%d)-$(git rev-parse --short HEAD)

# Build production image
docker build -t yufeed-api:v$(date +%Y.%m.%d) .
docker push yufeed-api:v$(date +%Y.%m.%d)

# Rolling restart (3 replicas)
for i in {1..3}; do
  echo "Updating replica $i..."
  kubectl set image deployment/yufeed-api api=yufeed-api:v$(date +%Y.%m.%d) --record

  # Wait for rollout
  kubectl rollout status deployment/yufeed-api --timeout=5m

  # Verify health
  sleep 10
  curl https://api.yufeed.com/health

  echo "Replica $i updated successfully"
done
```

### 3.4 Disable Read-Only Mode

```bash
# Re-enable writes
curl -X POST https://api.yufeed.com/admin/read-only-mode \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'

# Verify read-only mode disabled
curl https://api.yufeed.com/health | jq '.read_only'
# Expected: false
```

### 3.5 Deploy Frontend

```bash
cd apps/web

# Build production bundle
npm run build

# Deploy (method depends on hosting)
# Example for Vercel:
vercel --prod

# Example for S3 + CloudFront:
aws s3 sync dist/ s3://yufeed-web-prod/ --delete
aws cloudfront create-invalidation --distribution-id E123ABC --paths "/*"
```

---

## Step 4: Post-Deployment Verification

### 4.1 Immediate Checks (0-15 minutes)

```bash
# Monitor error rate
watch -n 5 'curl -s https://api.yufeed.com/metrics | grep -E "api_request.*{status=\"5"'

# Check Grafana SLO dashboard
open https://grafana.yufeed.com/d/slo-overview

# Monitor logs for errors
kubectl logs -f deployment/yufeed-api --tail=100 | grep -i error

# Run production smoke tests
pytest tests/smoke/ --base-url=https://api.yufeed.com -v
```

### 4.2 SLO Monitoring (15-60 minutes)

Monitor in Grafana:
- [ ] API Availability > 99.9%
- [ ] API Latency p95 < 500ms
- [ ] Transaction Processing Success > 99%
- [ ] Feature Cache Hit Rate > 95%
- [ ] DLQ Size < 50

**If any SLO breached:** Follow [rollback procedure](./rollback.md)

### 4.3 Business Metrics Check

```bash
# Transaction ingestion rate (should be normal)
curl -s 'http://prometheus.yufeed.com/api/v1/query?query=rate(transactions_processed_total[5m])' | jq

# Alert creation rate (should be within expected range)
curl -s 'http://prometheus.yufeed.com/api/v1/query?query=rate(alerts_created_total[5m])' | jq

# Feature extraction calls (should be consistent)
curl -s 'http://prometheus.yufeed.com/api/v1/query?query=rate(feature_extraction_duration_seconds_count[5m])' | jq
```

---

## Step 5: Extended Monitoring (1-24 hours)

### First Hour

- [ ] No critical alerts fired
- [ ] Error rate < 0.1%
- [ ] Latency within SLO targets
- [ ] No increase in DLQ size
- [ ] User-facing features functional

### First 4 Hours

- [ ] SLOs maintained
- [ ] No customer complaints
- [ ] Background tasks running normally
- [ ] Cache hit rates stable

### First 24 Hours

- [ ] Daily metrics review clean
- [ ] No unexpected behavior patterns
- [ ] Feature flags can be enabled (if used)
- [ ] Document any issues encountered

---

## Rollback Decision Tree

```
Is error rate > 5% for 5+ minutes?
├─ YES → ROLLBACK IMMEDIATELY
└─ NO → Continue monitoring

Is latency p95 > 2s for 10+ minutes?
├─ YES → ROLLBACK IMMEDIATELY
└─ NO → Continue monitoring

Is DLQ size > 200?
├─ YES → ROLLBACK IMMEDIATELY
└─ NO → Continue monitoring

Are critical user journeys broken?
├─ YES → ROLLBACK IMMEDIATELY
└─ NO → Continue monitoring

Is there data corruption?
├─ YES → ROLLBACK + RESTORE DATABASE
└─ NO → Continue monitoring
```

**When in doubt, rollback.** See [rollback.md](./rollback.md) for procedure.

---

## Communication Templates

### Pre-Deployment Notification

**Channel:** #engineering, #platform-team
**Timing:** 24 hours before

```
🚀 Production Deployment Scheduled

Date: [DATE]
Time: [TIME] UTC
Duration: ~30 minutes expected
Impacted Services: API, Web Frontend
Downtime: None expected (rolling restart)

Changes:
- [Brief summary of changes]
- [Link to release notes]

On-Call: @engineer
Rollback Plan: Documented

Questions? Reply here.
```

### Deployment Complete

**Channel:** #engineering, #platform-team

```
✅ Production Deployment Complete

Version: v2026.02.06
Deployed: 03:45 UTC
Duration: 28 minutes
Issues: None

Monitoring: https://grafana.yufeed.com/d/slo-overview

Next Steps:
- Monitoring for 24 hours
- Feature flags to be enabled gradually

Questions? Reply here.
```

### Deployment Issue

**Channel:** #engineering, #incident-response

```
🚨 Production Deployment Issue Detected

Issue: [Description]
Impact: [Customer-facing? Scope?]
Action: [Investigating | Rolling back]
ETA: [Estimate]

Incident Channel: #incident-2026-02-06
On-Call: @engineer

Updates every 15 minutes.
```

---

## Troubleshooting

### API Won't Start

```bash
# Check logs
kubectl logs deployment/yufeed-api --tail=100

# Common issues:
# 1. Database connection failed
#    → Verify DATABASE_URL env var
#    → Check database connectivity: nc -zv prod-db.yufeed.com 5432

# 2. Migration mismatch
#    → Check alembic current
#    → May need to rollback migration

# 3. Environment variable missing
#    → kubectl describe deployment/yufeed-api
#    → Verify all secrets mounted
```

### High Error Rate After Deployment

```bash
# Identify failing endpoints
curl -s https://api.yufeed.com/metrics | grep -E "api_request.*{status=\"5" | head -20

# Check recent logs for stack traces
kubectl logs deployment/yufeed-api --tail=500 | grep -i error

# Query error distribution by endpoint
# (use Grafana or Prometheus query)

# If widespread: ROLLBACK
# If isolated endpoint: May be able to hotfix or disable feature
```

### Database Migration Failed

```bash
# Check migration log
cat migration_prod.log | tail -50

# Check database state
psql $DATABASE_URL -c "SELECT * FROM alembic_version;"

# Options:
# 1. If migration partially applied: May need manual SQL fixes
# 2. If migration not started: Safe to retry
# 3. If data corruption: RESTORE FROM BACKUP
```

---

## Post-Deployment

### Day 1

- [ ] Review all metrics in Grafana
- [ ] Check for any unusual patterns
- [ ] Verify background jobs running
- [ ] Document any issues in deployment log

### Week 1

- [ ] Daily metrics review
- [ ] Check for gradual degradation
- [ ] Monitor customer feedback
- [ ] Schedule retrospective if issues

### Follow-Up

- [ ] Update this runbook with learnings
- [ ] Create tickets for any tech debt identified
- [ ] Document any manual steps that should be automated

---

## References

- [Rollback Procedure](./rollback.md)
- [Incident Response](./incident-response.md)
- [SLO Definitions](../../monitoring/slos.yml)
- [Grafana Dashboards](https://grafana.yufeed.com)
- [PagerDuty Rotation](https://yufeed.pagerduty.com)
