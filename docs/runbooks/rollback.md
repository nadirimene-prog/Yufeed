# Rollback Procedure

**Last Updated:** 2026-02-06
**Owner:** Platform Engineering Team
**On-Call Contact:** Check PagerDuty rotation

---

## Overview

This runbook covers emergency rollback procedures for YuFeed platform. Use when a deployment causes critical issues that cannot be quickly fixed forward.

**Golden Rule:** When in doubt, rollback. Forward fixes can wait.

---

## When to Rollback

### Immediate Rollback Triggers (No Discussion Needed)

- **Error rate > 5%** for 5+ minutes
- **Latency p95 > 2s** for 10+ minutes
- **API completely down** for 2+ minutes
- **Data corruption detected**
- **Security vulnerability** introduced
- **Critical user journey broken** (login, transactions, alerts)
- **DLQ size > 200** (massive processing failures)

### Rollback After Team Discussion

- Error rate 1-5% for 15+ minutes
- Latency degraded but < 2s
- Non-critical feature broken
- Performance degraded but within SLO
- Customer complaints increasing

---

## Automated Rollback

YuFeed has automated rollback capability for certain conditions.

### Automated Triggers

```yaml
# Configured in deployment/production/rollback-policy.yml

triggers:
  - name: high_error_rate
    condition: error_rate > 0.05
    duration: 5m
    action: rollback_api

  - name: critical_latency
    condition: p95_latency > 2000ms
    duration: 5m
    action: rollback_api

  - name: api_down
    condition: health_check_failed
    duration: 2m
    action: rollback_api
```

### Check Automated Rollback Status

```bash
# Check if automated rollback in progress
kubectl get deploy/yufeed-api -o jsonpath='{.metadata.annotations.rollback-status}'

# View rollback logs
kubectl logs -l app=rollback-controller --tail=50
```

---

## Manual Rollback Steps

### Step 1: Declare Incident

```bash
# Post in Slack
#incident-response channel:

"🚨 ROLLBACK IN PROGRESS
Issue: [Brief description]
Trigger: [Error rate spike | Latency | etc]
Rollback initiated by: @engineer
Version: [current] → [previous]
ETA: 10 minutes

Status updates every 5 minutes."
```

### Step 2: Identify Last Known-Good Version

```bash
cd /Users/imenenadir/Documents/Yufeed

# List recent tags
git tag --sort=-creatordate | head -10

# Check currently deployed version
curl https://api.yufeed.com/health | jq '.version'

# Or check Kubernetes
kubectl get deployment/yufeed-api -o jsonpath='{.spec.template.spec.containers[0].image}'

# Identify last stable version (usually previous tag)
ROLLBACK_VERSION="v2026.02.05-abc123"  # Example
```

### Step 3: Rollback API

#### Option A: Kubernetes Rollback (Fastest)

```bash
# Rollback to previous revision
kubectl rollout undo deployment/yufeed-api

# Or rollback to specific revision
kubectl rollout history deployment/yufeed-api
kubectl rollout undo deployment/yufeed-api --to-revision=<revision-number>

# Monitor rollback
kubectl rollout status deployment/yufeed-api

# Verify health
for i in {1..5}; do
  curl https://api.yufeed.com/health
  sleep 2
done
```

#### Option B: Manual Image Revert

```bash
# Set image to previous version
kubectl set image deployment/yufeed-api api=yufeed-api:$ROLLBACK_VERSION

# Monitor rollout
kubectl rollout status deployment/yufeed-api --timeout=5m

# Verify all pods updated
kubectl get pods -l app=yufeed-api
```

#### Option C: Docker Compose Rollback

```bash
cd /deployment/production

# Update docker-compose.yml to previous version
sed -i.bak "s/yufeed-api:.*/yufeed-api:$ROLLBACK_VERSION/" docker-compose.yml

# Restart services
docker-compose up -d api

# Verify
docker-compose ps
docker-compose logs -f api | head -50
```

### Step 4: Rollback Database Migration (If Needed)

**⚠️ CRITICAL:** Database rollbacks are risky. Only if absolutely necessary.

```bash
# Check current migration
alembic current

# Review migration history
alembic history

# Downgrade to previous migration
alembic downgrade -1

# Verify downgrade successful
alembic current

# Check for errors
tail -100 /var/log/yufeed/alembic.log
```

**If Migration is Not Reversible:**

```bash
# Option 1: Restore from backup
pg_restore -h prod-db.yufeed.com -U user -d yufeed backup_20260206_023000.dump

# Option 2: Manual SQL fixes (document in incident report)
psql $DATABASE_URL < manual_fix.sql
```

### Step 5: Rollback Frontend (If Needed)

```bash
cd apps/web

# For Vercel deployment
vercel rollback https://yufeed.com --yes

# For S3 + CloudFront
# Restore previous S3 version
aws s3 ls s3://yufeed-web-prod-backups/ | tail -5
aws s3 sync s3://yufeed-web-prod-backups/backup-20260205/ s3://yufeed-web-prod/ --delete

# Invalidate CloudFront cache
aws cloudfront create-invalidation --distribution-id E123ABC --paths "/*"

# For Docker deployment
kubectl set image deployment/yufeed-web web=yufeed-web:$ROLLBACK_VERSION
kubectl rollout status deployment/yufeed-web
```

---

## Post-Rollback Verification

### Immediate Checks (0-5 minutes)

```bash
# 1. Verify version rolled back
curl https://api.yufeed.com/health | jq '.version'
# Expected: Previous version

# 2. Check health endpoints
curl https://api.yufeed.com/health | jq
# Expected: {"status": "healthy"}

curl https://api.yufeed.com/health/db | jq
# Expected: {"status": "connected"}

# 3. Monitor error rate
watch -n 5 'curl -s https://api.yufeed.com/metrics | grep -E "api_request.*{status=\"5"'
# Expected: Error rate dropping

# 4. Check critical endpoints
curl https://api.yufeed.com/api/transactions -H "Authorization: Bearer $TOKEN"
curl https://api.yufeed.com/api/alerts -H "Authorization: Bearer $TOKEN"
# Expected: 200 OK responses
```

### Extended Checks (5-30 minutes)

```bash
# Run smoke tests
cd apps/api
pytest tests/smoke/ --base-url=https://api.yufeed.com -v

# Monitor SLOs in Grafana
open https://grafana.yufeed.com/d/slo-overview

# Verify:
# - API Availability back to > 99.9%
# - Latency p95 back to < 500ms
# - Transaction processing success > 99%
# - DLQ size stabilized
```

### Business Impact Assessment

```bash
# Check if any transactions lost
# Query for gaps in transaction_id sequence
psql $DATABASE_URL -c "
  SELECT COUNT(*) as gap_count
  FROM (
    SELECT transaction_id,
           LEAD(transaction_id) OVER (ORDER BY created_at) as next_id
    FROM transactions
    WHERE created_at > NOW() - INTERVAL '1 hour'
  ) gaps
  WHERE next_id - transaction_id > 1;"

# Check if any alerts missed
psql $DATABASE_URL -c "
  SELECT COUNT(*) as missed_alerts
  FROM transactions t
  LEFT JOIN alerts a ON t.transaction_id = a.transaction_id
  WHERE t.created_at > NOW() - INTERVAL '1 hour'
    AND t.risk_score > 70
    AND a.id IS NULL;"

# Review DLQ for failed transactions
curl https://api.yufeed.com/admin/dlq?limit=100 | jq '.items | length'
```

---

## Troubleshooting Rollback Issues

### Rollback Fails to Deploy

```bash
# Check deployment status
kubectl describe deployment/yufeed-api

# Common issues:

# 1. Image not found
#    → Verify image exists in registry
docker pull yufeed-api:$ROLLBACK_VERSION

# 2. Resource constraints
#    → Check cluster capacity
kubectl top nodes
kubectl describe node <node-name>

# 3. Health checks failing
#    → Check logs for startup errors
kubectl logs -l app=yufeed-api --tail=100

# 4. Previous version has dependency issues
#    → May need to skip back further
#    → Or fix forward with hotfix
```

### Database Rollback Fails

```bash
# Check migration status
alembic current

# If migration stuck:
# 1. Check for locks
psql $DATABASE_URL -c "SELECT * FROM pg_locks WHERE NOT granted;"

# 2. Check for active connections
psql $DATABASE_URL -c "SELECT * FROM pg_stat_activity WHERE state = 'active';"

# 3. Force unlock (DANGEROUS - last resort)
psql $DATABASE_URL -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'active';"

# Then retry migration
alembic downgrade -1
```

### Rollback Completes But Issues Persist

This suggests the root cause was not the deployment.

```bash
# Check external dependencies
# 1. Database performance
psql $DATABASE_URL -c "SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"

# 2. Redis connectivity
redis-cli -h prod-redis.yufeed.com ping
redis-cli -h prod-redis.yufeed.com info memory

# 3. External API dependencies
curl https://external-api.example.com/health

# 4. Network issues
ping prod-db.yufeed.com
traceroute prod-db.yufeed.com

# If external issue:
# - Follow incident response runbook
# - May need infrastructure changes, not code rollback
```

---

## Rollback Decision Matrix

| Issue | Rollback? | Alternative |
|-------|-----------|-------------|
| API error rate > 5% | **YES - Immediate** | None |
| API latency > 2s p95 | **YES - Immediate** | None |
| Single endpoint broken | **Maybe** | Disable endpoint via feature flag |
| Non-critical feature broken | **No** | Fix forward or disable feature |
| Performance degraded 20% | **Maybe** | Investigate first, rollback if no quick fix |
| Data corruption | **YES + Restore DB** | None |
| Security vulnerability | **YES - Immediate** | None |
| Customer complaints increasing | **Maybe** | Investigate impact, rollback if widespread |

---

## Communication During Rollback

### Status Update Template (Every 5 minutes)

**Channel:** #incident-response

```
🔄 Rollback Status Update [HH:MM UTC]

Progress: [Step X of 5] [Step description]
Status: [In progress | Completed | Blocked]
Current metrics:
  - Error rate: [X%]
  - Latency p95: [Xms]
  - API health: [healthy | degraded]

Next: [Next step description]
ETA completion: [X minutes]

Blockers: [Any blockers or concerns]
```

### Rollback Complete Notification

**Channel:** #incident-response, #engineering

```
✅ Rollback Complete

Rolled back from: v2026.02.06-def456
Rolled back to: v2026.02.05-abc123
Duration: 12 minutes
Current status: Stable

Verification:
  ✅ API health: healthy
  ✅ Error rate: 0.05% (normal)
  ✅ Latency p95: 245ms (normal)
  ✅ Smoke tests: passing

Business impact:
  - [Describe any lost transactions, missed alerts, etc]
  - DLQ items: 12 (being replayed)

Next steps:
  1. Root cause analysis within 24h
  2. Post-mortem scheduled for [DATE]
  3. Forward fix planned for [DATE]

Incident channel: #incident-2026-02-06
```

---

## Post-Rollback Actions

### Immediate (0-1 hour)

- [ ] Confirm all systems stable
- [ ] Document rollback reason and steps taken
- [ ] Assess business impact (lost data, failed transactions)
- [ ] Create incident report ticket
- [ ] Begin root cause analysis

### Short-term (1-24 hours)

- [ ] Complete root cause analysis
- [ ] Identify specific commit/change that caused issue
- [ ] Create fix plan (with tests to prevent regression)
- [ ] Schedule post-mortem meeting
- [ ] Update relevant runbooks with learnings

### Medium-term (1-7 days)

- [ ] Conduct post-mortem (blameless)
- [ ] Document action items from post-mortem
- [ ] Implement additional monitoring/alerting if needed
- [ ] Plan and test forward fix
- [ ] Deploy fix to staging
- [ ] Deploy fix to production (with extra caution)

---

## Preventing Future Rollbacks

### Checklist to Add to Deployment Process

- [ ] **Canary Deployments**: Deploy to 10% traffic first, monitor for 30 minutes
- [ ] **Feature Flags**: New features behind flags, enable gradually
- [ ] **Automated Testing**: Comprehensive integration tests in staging
- [ ] **Performance Testing**: Load test significant changes in staging
- [ ] **Database Migration Testing**: Test migrations on production-sized dataset
- [ ] **Rollback Testing**: Test rollback procedure in staging before production
- [ ] **Monitoring Alerts**: Ensure SLO-based alerts will catch issues quickly
- [ ] **Change Review**: Peer review all production-bound changes

---

## Rollback Logs

Document each rollback for pattern analysis:

| Date | Version | Reason | Duration | Impact | Root Cause | Prevention |
|------|---------|--------|----------|--------|------------|------------|
| 2026-02-06 | v2026.02.06 | API error rate 15% | 12 min | 20 failed txns | Missing database index | Add index validation to CI |
| | | | | | | |

---

## References

- [Deployment Runbook](./deployment.md)
- [Incident Response](./incident-response.md)
- [Database Migration Guide](./database-migrations.md)
- [SLO Definitions](../../monitoring/slos.yml)
- [Post-Mortem Template](../templates/post-mortem.md)
