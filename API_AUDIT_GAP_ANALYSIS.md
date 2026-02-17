# 🔍 API AUDIT & GAP ANALYSIS REPORT
## YuFeed Platform - Backend vs Frontend Coverage

**Date:** 2026-02-16  
**Auditor:** Automated Analysis

---

## 📊 EXECUTIVE SUMMARY

| Metric | Count | Percentage |
|--------|-------|------------|
| **Total Backend Endpoints** | 321 | 100% |
| **Frontend-Used Endpoints** | ~96 | 30% |
| **Orphaned (Unused) Endpoints** | ~225 | 70% |
| **Deprecated Endpoints** | 3 | <1% |
| **API Categories** | 31 | - |
| **Fully Covered Categories** | 5 | 16% |
| **Partially Covered Categories** | 6 | 19% |
| **Zero Coverage Categories** | 20 | 65% |

---

## 🚦 COVERAGE MATRIX

| Category | Backend | Frontend | Coverage | Status |
|----------|---------|----------|----------|--------|
| AI AML Officer | 15 | 12 | 80% | 🟢 |
| Policies | 15 | 13 | 87% | 🟢 |
| Risk Management | 16 | 16 | 100% | 🟢 |
| Obligations | 7 | 8* | 114% | 🟡 |
| Natural Language Query | 5 | 5 | 100% | 🟢 |
| Search & Documents | 4 | 2 | 50% | 🟡 |
| Alerts | 16 | 4 | 25% | 🔴 |
| Cases | 17 | 2 | 12% | 🔴 |
| Authentication | 10 | 1 | 10% | 🔴 |
| Audit | 8 | 0 | 0% | 🔴 |
| Tenants | 15 | 0 | 0% | 🔴 |
| Transactions | 10 | 0 | 0% | 🔴 |
| Travel Rule | 4 | 0 | 0% | 🔴 |
| CELEX Search | 7 | 0 | 0% | 🔴 |
| AI-Agents | 11 | 0 | 0% | 🔴 |
| Monitoring Rules | 25 | 0 | 0% | 🔴 |
| Model Registry | 7 | 0 | 0% | 🔴 |
| Network Analysis | 3 | 0 | 0% | 🔴 |
| Onchain Risk | 2 | 0 | 0% | 🔴 |
| Decisioning | 3 | 0 | 0% | 🔴 |
| Evidence/Evidence Packs | 7 | 3 | 43% | 🟡 |
| SAR Filing | 3 | 0 | 0% | 🔴 |
| Audit Trails | 4 | 0 | 0% | 🔴 |
| Compliance Dashboard | 2 | 0 | 0% | 🔴 |
| Scope Analysis | 2 | 0 | 0% | 🔴 |
| Findings | 6 | 5 | 83% | 🟢 |
| Risk Profiles | 6 | 0 | 0% | 🔴 |
| Features | 4 | 0 | 0% | 🔴 |
| Case Decisions | 6 | 5 | 83% | 🟢 |
| Impact Assessment | 0 | 6** | N/A | ⚠️ |
| **Gap Analysis** (New) | 10 | 0 | 0% | 🔴 |
| **Policy Generator** (New) | 11 | 0 | 0% | 🔴 |
| **Reminders** (New) | 9 | 0 | 0% | 🔴 |

\* Frontend uses 8 but one endpoint might be duplicate  
\** Frontend calls these but backend may not implement

---

## 🟢 WELL-COVERED APIs (Frontend + Backend Aligned)

### 1. AI AML Officer (12/15 endpoints)
```
✅ POST /api/aml-officer/investigate
✅ POST /api/aml-officer/investigate/batch
✅ GET /api/aml-officer/briefing/daily
✅ POST /api/aml-officer/ask
✅ GET /api/aml-officer/alerts/proactive
✅ POST /api/aml-officer/sanctions/screen
✅ POST /api/aml-officer/sanctions/screen/batch
✅ GET /api/aml-officer/sanctions/statistics
✅ POST /api/aml-officer/sar/prepare
✅ GET /api/aml-officer/sar/templates
✅ GET /api/aml-officer/health
✅ GET /api/aml-officer/capabilities

❌ POST /api/aml-officer/workflow/execute
❌ GET /api/aml-officer/investigation/{id}
```

### 2. Policies (13/15 endpoints)
```
✅ GET /api/policies
✅ POST /api/policies
✅ GET /api/policies/{id}
✅ PATCH /api/policies/{id}
✅ DELETE /api/policies/{id}
✅ POST /api/policies/{id}/approve
✅ GET /api/policies/{id}/obligations
✅ GET /api/policies/templates
✅ POST /api/policies/{id}/sections
✅ PATCH /api/policies/sections/{id}
✅ DELETE /api/policies/sections/{id}
✅ POST /api/policies/from-template/{id}
✅ POST /api/policies/{id}/link-obligation/{oid}

❌ GET /api/policies/templates/{id}
❌ GET /api/policies/{id}/sections
```

### 3. Risk Management (16/16 endpoints) ✅ COMPLETE
All risk endpoints are connected.

### 4. Natural Language Query (5/5 endpoints) ✅ COMPLETE
All NL query endpoints are connected.

### 5. Findings (5/6 endpoints)
```
✅ GET /api/findings
✅ GET /api/findings/{id}
✅ POST /api/findings/{id}/close
✅ POST /api/findings/{id}/escalate
✅ PATCH /api/findings/{id}

❌ POST /api/findings
❌ DELETE /api/findings/{id}
```

### 6. Case Decisions (5/6 endpoints)
```
✅ GET /api/cases/{id}/decisions
✅ POST /api/cases/{id}/decisions
✅ POST /api/cases/{id}/decisions/{id}/submit
✅ POST /api/cases/{id}/decisions/{id}/approve
✅ POST /api/cases/{id}/decisions/{id}/reject

❌ GET /api/cases/{id}/decisions/{id}
```

---

## 🟡 PARTIALLY COVERED APIs

### 7. Obligations (8 endpoints, 100%+ coverage)
**Potential Duplicate:** Frontend uses PATCH to `/api/obligations/{id}` for updates, but backend also has `/api/obligations/{id}/approve`

```
✅ GET /api/obligations
✅ GET /api/obligations/{id}
✅ PATCH /api/obligations/{id}
✅ PATCH /api/obligations/{id}/approve
✅ GET /api/obligations/{id}/risks
✅ GET /api/obligations/{id}/internal-rules
✅ GET /api/obligations/{id}/policy-suggestions
✅ POST /api/compliance/obligations/{id}/internal-rules
```

### 8. Search & Documents (2/4 endpoints)
```
✅ GET /api/search
✅ GET /api/documents/{celex}

❌ GET /api/documents/{celex}/diff
❌ GET /api/documents/{celex}/versions
```

### 9. Alerts (4/16 endpoints)
```
✅ GET /api/alerts
✅ GET /api/alerts/{id}
✅ PATCH /api/alerts/{id}

❌ POST /api/alerts
❌ GET /api/alerts/critical
❌ GET /api/alerts/pending
❌ GET /api/alerts/sar/filed
❌ GET /api/alerts/statistics
❌ GET /api/alerts/statistics/overview
❌ POST /api/alerts/{id}/assign
❌ POST /api/alerts/{id}/escalate
❌ POST /api/alerts/{id}/false-positive
❌ POST /api/alerts/{id}/file-sar
❌ GET /api/alerts/{id}/regulatory-context
❌ POST /api/alerts/{id}/resolve
❌ GET /api/alerts/{id}/transaction
```

### 10. Cases (2/17 endpoints)
```
✅ GET /api/cases/
✅ GET /api/cases/{id}/decisions

❌ POST /api/cases/
❌ POST /api/cases/from-alert/{id}
❌ GET /api/cases/statistics/overview
❌ GET /api/cases/{id}
❌ PATCH /api/cases/{id}
❌ POST /api/cases/{id}/add-alert/{alert_id}
❌ POST /api/cases/{id}/add-evidence
❌ GET /api/cases/{id}/alerts
❌ POST /api/cases/{id}/assign
❌ POST /api/cases/{id}/close
❌ POST /api/cases/{id}/escalate
❌ POST /api/cases/{id}/findings
❌ POST /api/cases/{id}/notes
❌ GET /api/cases/{id}/notes
❌ GET /api/cases/{id}/regulations
❌ GET /api/cases/{id}/transactions
```

---

## 🔴 ORPHANED APIs (Backend Only - No Frontend Usage)

### 11. Authentication (1/10 used)
```
✅ POST /api/auth/login

❌ POST /api/auth/register
❌ POST /api/auth/refresh
❌ POST /api/auth/logout
❌ POST /api/auth/logout-all
❌ GET /api/auth/me
❌ POST /api/auth/change-password
❌ POST /api/auth/forgot-password
❌ POST /api/auth/reset-password
❌ POST /api/auth/token
```

### 12. Audit (0/8 used)
```
❌ GET /api/audit/
❌ POST /api/audit/decisions
❌ GET /api/audit/decisions
❌ GET /api/audit/decisions/{id}
❌ POST /api/audit/events
❌ GET /api/audit/events/{id}
❌ GET /api/audit/logs
❌ GET /api/audit/logs/{id}
```

### 13. Compliance Workflow (2/12 used)
```
✅ GET /api/compliance/obligations/{id}/internal-rules
✅ POST /api/compliance/obligations/{id}/internal-rules

❌ PATCH /api/compliance/internal-rules/{id}
❌ GET /api/compliance/internal-rules/{id}/mappings
❌ POST /api/compliance/internal-rules/{id}/mappings
❌ GET /api/compliance/policies
❌ POST /api/compliance/policies
❌ GET /api/compliance/policies/{id}
❌ PATCH /api/compliance/policies/{id}
❌ GET /api/compliance/policies/{id}/sections
❌ POST /api/compliance/policies/{id}/sections
❌ PATCH /api/compliance/policy-sections/{id}
```

### 14. Tenants (0/15 used)
All tenant management endpoints are orphaned.

### 15. Transactions (0/10 used)
All transaction endpoints are orphaned.

### 16. Travel Rule (0/4 used)
All travel rule endpoints are orphaned.

### 17. CELEX Search (0/7 used)
All CELEX search endpoints are orphaned.

### 18. AI-Agents (0/11 used)
All AI agent endpoints are orphaned.

### 19. Monitoring Rules (0/25 used)
All monitoring rules endpoints are orphaned.

### 20. Model Registry (0/7 used)
All model registry endpoints are orphaned.

### 21. Network Analysis (0/3 used)
All network analysis endpoints are orphaned.

### 22. Onchain Risk (0/2 used)
All onchain risk endpoints are orphaned.

### 23. Decisioning (0/3 used)
All decisioning endpoints are orphaned.

### 24. SAR Filing (0/3 used)
All SAR filing endpoints are orphaned.

### 25. Audit Trails (0/4 used)
All audit trails endpoints are orphaned.

### 26. Compliance Dashboard (0/2 used)
All compliance dashboard endpoints are orphaned.

### 27. Scope Analysis (0/2 used)
All scope analysis endpoints are orphaned.

### 28. Risk Profiles (0/6 used)
All risk profile endpoints are orphaned.

### 29. Features (0/4 used)
All features endpoints are orphaned.

---

## ⚠️ NEWLY ADDED APIS (Backend Only)

### 30. Gap Analysis (0/10 used)
Just added to backend, needs frontend integration:
```
❌ GET /api/gap-analysis/dashboard
❌ GET /api/gap-analysis/gaps
❌ POST /api/gap-analysis/map-obligation
❌ POST /api/gap-analysis/unmap-obligation/{id}
❌ GET /api/gap-analysis/obligation/{id}/coverage
❌ GET /api/gap-analysis/coverage-by-document
❌ POST /api/gap-analysis/recalculate
❌ GET /api/gap-analysis/categories
❌ GET /api/gap-analysis/trend
❌ GET /api/gap-analysis/admin/mappings
```

### 31. Policy Generator (0/11 used)
Just added to backend, needs frontend integration:
```
❌ POST /api/policy-generator/generate
❌ GET /api/policy-generator/templates
❌ GET /api/policy-generator/templates/{id}/variables
❌ POST /api/policy-generator/templates/{id}/preview
❌ POST /api/policy-generator/quick-generate
❌ GET /api/policy-generator/jobs
❌ GET /api/policy-generator/results/{job_id}
❌ GET /api/policy-generator/results/{job_id}/preview
❌ POST /api/policy-generator/results/{job_id}/approve
❌ POST /api/policy-generator/results/{job_id}/reject
❌ GET /api/policy-generator/stats
```

### 32. Reminders (0/9 used)
Just added to backend, needs frontend integration:
```
❌ GET /api/reminders/upcoming
❌ GET /api/reminders/statistics
❌ GET /api/reminders/history/{obligation_id}
❌ POST /api/reminders/send-now/{obligation_id}
❌ POST /api/reminders/snooze/{obligation_id}
❌ GET /api/reminders/subscriptions
❌ POST /api/reminders/subscriptions
❌ DELETE /api/reminders/subscriptions/{id}
❌ GET /api/reminders/admin/logs
```

---

## 🚨 CRITICAL FINDINGS

### 1. DEPRECATED ENDPOINTS (3)
```
⚠️ POST /api/rules [DEPRECATED]
⚠️ GET /api/rules [DEPRECATED]
⚠️ GET /api/rules/{rule_id} [DEPRECATED]
```
**Action:** Remove from backend or migrate to new endpoints.

### 2. ENDPOINT DUPLICATION
Backend has **TWO** policy APIs:
- `/api/policies/*` (15 endpoints) - Used by frontend ✅
- `/api/compliance/policies/*` (7 endpoints) - Not used ❌

**Action:** Consolidate or deprecate the `/api/compliance/policies` endpoints.

### 3. MISSING BACKEND IMPLEMENTATIONS
Frontend calls these but backend may not exist:
```
⚠️ POST /api/impact/documents/{celex}/analyze
⚠️ GET /api/impact/documents/{celex}/assessment
⚠️ GET /api/impact/documents/{celex}/actions
⚠️ PUT /api/impact/actions/{actionId}
⚠️ GET /api/impact/actions/all
⚠️ GET /api/impact/dashboard/stats
```

### 4. AUTH GAPS
Backend has full auth system (10 endpoints) but frontend only implements login.
Missing frontend implementation:
- User registration
- Password reset flow
- Token refresh
- Profile management
- Logout

---

## 📈 PRIORITIZED RECOMMENDATIONS

### 🔴 Priority 1 - Critical (Week 1-2)
1. **Remove Deprecated Endpoints**
   - Delete or migrate 3 `/api/rules/*` endpoints

2. **Consolidate Policy APIs**
   - Deprecate `/api/compliance/policies/*` in favor of `/api/policies/*`

3. **Implement Impact Assessment Backend**
   - Create 6 missing endpoints

4. **Connect New APIs**
   - Build frontend for Gap Analysis (10 endpoints)
   - Build frontend for Policy Generator (11 endpoints)
   - Build frontend for Reminders (9 endpoints)

### 🟠 Priority 2 - High (Week 3-4)
5. **Complete Authentication**
   - Add registration page
   - Add password reset flow
   - Add token refresh logic
   - Add profile management

6. **Connect Core Features**
   - Alerts management UI (12 unused endpoints)
   - Cases management UI (15 unused endpoints)

### 🟡 Priority 3 - Medium (Month 2)
7. **Connect Transaction System**
   - Transaction monitoring UI (10 endpoints)

8. **Connect Admin Features**
   - Tenant management UI (15 endpoints)
   - Audit trails UI (8 endpoints)

### 🟢 Priority 4 - Low (Month 3+)
9. **Connect Advanced Features**
   - AI Agents (11 endpoints)
   - CELEX Search (7 endpoints)
   - Model Registry (7 endpoints)
   - Travel Rule (4 endpoints)
   - Onchain Risk (2 endpoints)
   - Network Analysis (3 endpoints)
   - And remaining specialized APIs

---

## 📊 EFFORT ESTIMATION

| Priority | APIs | Endpoints | Est. Effort |
|----------|------|-----------|-------------|
| P1 - Critical | 4 | 49 | 2 weeks |
| P2 - High | 3 | 40 | 2 weeks |
| P3 - Medium | 3 | 33 | 2 weeks |
| P4 - Low | 15 | 103 | 6 weeks |
| **Total** | **25** | **225** | **12 weeks** |

---

## 🎯 QUICK WINS

These APIs are fully backend-ready and just need frontend pages:

1. **Gap Analysis Dashboard** (10 endpoints)
   - Ready to implement - just needs UI

2. **Policy Generator** (11 endpoints)
   - Ready to implement - just needs UI

3. **Reminders** (9 endpoints)
   - Ready to implement - just needs UI

4. **Alerts Management** (12 unused endpoints)
   - Full CRUD already available

5. **Cases Management** (15 unused endpoints)
   - Full case lifecycle available

---

*End of Report*
