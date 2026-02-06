# Incident Response Runbook

**Last Updated:** 2026-02-06
**Owner:** Platform Engineering Team
**On-Call Contact:** Check PagerDuty rotation

---

## Severity Levels

| Severity | Response Time | Description | Examples |
|----------|--------------|-------------|----------|
| **P0 - Critical** | <15 minutes | Complete service outage, data loss | API down, database corruption, security breach |
| **P1 - High** | <1 hour | Partial outage, critical feature down | Transaction processing failing, authentication broken |
| **P2 - Medium** | <4 hours | Degraded performance, non-critical feature down | Slow API responses, feature extraction lag |
| **P3 - Low** | <24 hours | Minor issues, cosmetic bugs | UI glitch, logging issue |

---

## Incident Response Steps

### 1. Acknowledge & Assess (0-5 minutes)

```bash
# Acknowledge in PagerDuty
# Join #incident-response channel in Slack

# Quick health check
curl https://api.yufeed.com/health | jq
curl https://api.yufeed.com/metrics | grep -E "error_rate|latency"

# Check Grafana SLO dashboard
open https://grafana.yufeed.com/d/slo-overview

# Assess severity and impact
# - How many users affected?
# - What functionality broken?
# - Data at risk?
```

**Post Initial Assessment:**
```
🚨 INCIDENT DECLARED: [Brief Title]

Severity: P0/P1/P2/P3
Detected: [TIME] UTC
Impact: [Brief description]
Incident Commander: @engineer

Investigation channel: #incident-YYYYMMDD-N
Status updates every [15/30/60] minutes

Current status: Investigating
```

### 2. Investigate (5-30 minutes)

```bash
# Check recent deployments
git log --oneline -10
kubectl rollout history deployment/yufeed-api

# Check error logs
kubectl logs -l app=yufeed-api --tail=500 | grep ERROR

# Check database
psql $DATABASE_URL -c "
  SELECT COUNT(*) as active_connections
  FROM pg_stat_activity
  WHERE state = 'active';"

psql $DATABASE_URL -c "
  SELECT query, calls, total_time, mean_time
  FROM pg_stat_statements
  ORDER BY total_time DESC LIMIT 10;"

# Check Celery workers
celery -A src.worker inspect active
celery -A src.worker inspect stats

# Check external dependencies
curl https://external-api.example.com/health

# Check DLQ size
curl https://api.yufeed.com/admin/dlq | jq '.items | length'
```

### 3. Communicate (Every 15-60 minutes based on severity)

**Update Template:**
```
📊 Incident Update [HH:MM UTC]

Status: [Investigating | Identified | Mitigating | Resolved]

What we know:
- [Finding 1]
- [Finding 2]

Current impact:
- [Impact description]
- Affected users: [count/percentage]

Actions taken:
- [Action 1]
- [Action 2]

Next steps:
- [Next action]

ETA resolution: [estimate]
```

### 4. Mitigate (Based on root cause)

#### If Recent Deployment

```bash
# See rollback.md
kubectl rollout undo deployment/yufeed-api
kubectl rollout status deployment/yufeed-api
```

#### If Database Issue

```bash
# Check slow queries
psql $DATABASE_URL -c "
  SELECT pid, now() - query_start as duration, query, state
  FROM pg_stat_activity
  WHERE state != 'idle'
    AND now() - query_start > interval '30 seconds'
  ORDER BY duration DESC;"

# Kill long-running queries (if safe)
psql $DATABASE_URL -c "SELECT pg_terminate_backend(12345);"  # Replace with actual PID

# Scale read replicas
kubectl scale deployment/yufeed-db-replica --replicas=5

# Review and add missing indexes (see performance.md)
```

#### If External Dependency Failure

```bash
# Implement circuit breaker
curl -X POST https://api.yufeed.com/admin/circuit-breaker \
  -d '{"service": "external-api", "enabled": true}'

# Failover to backup service
kubectl set env deployment/yufeed-api EXTERNAL_API_URL=https://backup-api.example.com
```

#### If Traffic Spike

```bash
# Scale horizontally
kubectl scale deployment/yufeed-api --replicas=10

# Enable rate limiting
curl -X POST https://api.yufeed.com/admin/rate-limit \
  -d '{"enabled": true, "requests_per_minute": 1000}'

# Enable caching aggressively
curl -X POST https://api.yufeed.com/admin/cache-config \
  -d '{"ttl": 300}'  # 5 minutes
```

### 5. Resolve & Verify (30+ minutes)

```bash
# Verify metrics returned to normal
curl https://api.yufeed.com/metrics | grep -E "error_rate|latency"

# Run smoke tests
pytest tests/smoke/ --base-url=https://api.yufeed.com -v

# Check SLOs in Grafana
# - API Availability > 99.9%
# - Latency p95 < 500ms
# - Transaction success > 99%

# Monitor for 30 minutes before declaring resolved
```

**Resolution Notification:**
```
✅ INCIDENT RESOLVED

Incident: [Title]
Duration: [X] hours [Y] minutes
Resolution time: [HH:MM] UTC

Root cause: [Brief description]

Impact summary:
- [Impact 1]
- [Impact 2]

Resolution:
- [Action taken]

Follow-up:
- Post-mortem scheduled: [DATE/TIME]
- Tickets created: [TICKET-123, TICKET-456]

Monitoring for 24 hours.
```

### 6. Post-Incident (24-48 hours)

- [ ] Write incident report
- [ ] Schedule blameless post-mortem
- [ ] Create action items to prevent recurrence
- [ ] Update runbooks with learnings
- [ ] Communicate to stakeholders

---

## Common Incidents & Quick Fixes

### High API Error Rate

**Quick Investigation:**
```bash
# Which endpoints?
kubectl logs -l app=yufeed-api --tail=1000 | grep "ERROR" | cut -d' ' -f5 | sort | uniq -c | sort -rn

# Recent deployments?
kubectl rollout history deployment/yufeed-api | tail -5

# Database connectivity?
psql $DATABASE_URL -c "SELECT 1;"
```

**Quick Mitigation:**
- Recent deployment → Rollback
- Database issue → Scale replicas
- Specific endpoint → Disable via feature flag

### Slow Feature Extraction

**Quick Investigation:**
```bash
# Check p95 latency
curl 'http://prometheus.yufeed.com/api/v1/query?query=histogram_quantile(0.95,rate(feature_extraction_duration_seconds_bucket[5m]))' | jq

# Check database query performance
psql $DATABASE_URL -c "EXPLAIN ANALYZE
  SELECT COUNT(id) FROM transactions
  WHERE tenant_id = 'test' AND user_id = 'user123'
    AND timestamp >= NOW() - INTERVAL '24 hours';"
```

**Quick Mitigation:**
- Missing indexes → Add immediately
- Cold cache → Warm cache for active users
- Database overload → Scale read replicas

### DLQ Size Growing

**Quick Investigation:**
```bash
# Query DLQ items
curl https://api.yufeed.com/admin/dlq?limit=50 | jq

# Check for patterns
curl https://api.yufeed.com/admin/dlq?limit=100 | jq '.items[].error_message' | sort | uniq -c | sort -rn
```

**Quick Mitigation:**
- Recent deployment issue → Rollback
- Transient external API failure → Wait for recovery, items will retry
- Code bug → Fix and redeploy, then replay DLQ

### WebSocket Disconnections

**Quick Investigation:**
```bash
# Check connection count
curl https://api.yufeed.com/metrics | grep websocket_connections_active

# Check logs for disconnect reasons
kubectl logs -l app=yufeed-api --tail=500 | grep "websocket" | grep "disconnect"
```

**Quick Mitigation:**
- Server restart → Wait for clients to reconnect automatically
- Network issue → Check load balancer config
- Resource exhaustion → Scale horizontally

---

## Escalation Matrix

| Issue | First Responder | Escalate To | Escalate If |
|-------|----------------|-------------|-------------|
| API outage | On-call engineer | Engineering lead | >30 min unresolved |
| Database issue | On-call engineer | Database specialist | Query optimization needed |
| Security incident | On-call engineer | Security team | Immediately |
| Data corruption | On-call engineer | CTO | Data loss confirmed |
| External dependency | On-call engineer | VP Engineering | >1 hour impact |

**Contact Information:**
- On-call Engineer: PagerDuty rotation
- Engineering Lead: @lead in Slack
- Database Specialist: @db-specialist
- Security Team: security@yufeed.com
- VP Engineering: @vp-eng

---

## Tools & Dashboards

- **Grafana SLO Dashboard:** https://grafana.yufeed.com/d/slo-overview
- **Prometheus:** http://prometheus.yufeed.com
- **Logs:** `kubectl logs -l app=yufeed-api`
- **Metrics:** https://api.yufeed.com/metrics
- **DLQ Admin:** https://api.yufeed.com/admin/dlq
- **PagerDuty:** https://yufeed.pagerduty.com

---

## References

- [Deployment Runbook](./deployment.md)
- [Rollback Procedure](./rollback.md)
- [Performance Investigation](./performance.md)
- [SLO Definitions](../../monitoring/slos.yml)
