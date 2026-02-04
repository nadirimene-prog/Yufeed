# Yufeed Dashboard Implementation Plan

## Project Overview

**Objective:** Transform Yufeed into a best-in-class AML/Compliance platform competitive with Sardine.ai while leveraging our unique regulatory intelligence advantage.

**Current State:** 70-75% feature parity with industry leaders
**Target State:** 95%+ feature parity + unique regulatory differentiation

---

## Phase Structure

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        IMPLEMENTATION TIMELINE                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Phase 1          Phase 2          Phase 3          Phase 4                 │
│  Real-Time        AI Intelligence  Compliance       Enterprise              │
│  Foundation       Engine           Suite            Polish                  │
│                                                                             │
│  ████████████     ████████████     ████████████     ████████████           │
│  Weeks 1-4        Weeks 5-8        Weeks 9-12       Weeks 13-16            │
│                                                                             │
│  • WebSocket      • NLP Rules      • SAR Lifecycle  • Mobile               │
│  • Live Dashboard • Backtesting    • PDF Reports    • Performance          │
│  • Unified Alerts • ML Monitoring  • Scheduling     • Integrations         │
│  • Geo Heatmap    • Shadow Mode    • Audit Trail    • White-label          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Real-Time Foundation (Weeks 1-4)

### Objective
Build real-time infrastructure and unified investigation experience

### Deliverables

#### 1.1 WebSocket Infrastructure
**Priority:** 🔴 Critical
**Effort:** High

**Backend Tasks:**
- [ ] Set up WebSocket server with FastAPI WebSockets
- [ ] Create event broadcasting system for transactions, alerts, system status
- [ ] Implement connection management (auth, heartbeat, reconnection)
- [ ] Build Redis pub/sub for horizontal scaling
- [ ] Create event types: `transaction.new`, `alert.created`, `alert.updated`, `system.health`

**Frontend Tasks:**
- [ ] Create WebSocket hook (`useWebSocket`) with auto-reconnection
- [ ] Build real-time state management (Zustand store for live data)
- [ ] Implement connection status indicator
- [ ] Create notification system for real-time events

**Files to Create/Modify:**
```
apps/api/src/websocket/
├── __init__.py
├── manager.py          # Connection manager
├── events.py           # Event types and handlers
├── broadcaster.py      # Redis pub/sub broadcaster
└── auth.py             # WebSocket authentication

apps/web/src/
├── hooks/useWebSocket.ts
├── stores/realTimeStore.ts
└── components/ui/connection-status.tsx
```

---

#### 1.2 Command Center Dashboard
**Priority:** 🔴 Critical
**Effort:** High

**Components to Build:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ COMMAND CENTER                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ LIVE METRICS BAR                                                    │   │
│  │ 🔴 1,247 tx/min │ ⚠️ 42 alerts │ 🟢 99.9% uptime │ ⚡ 45ms latency │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌────────────────────────────────┐  ┌─────────────────────────────────┐   │
│  │ GEOGRAPHIC HEATMAP             │  │ SYSTEM HEALTH                   │   │
│  │ [Mapbox GL / Leaflet]          │  │ API: ✅  DB: ✅  AI: ✅  Queue: ✅│   │
│  │ • Live transaction origins     │  │ P50: 23ms P95: 67ms P99: 142ms  │   │
│  │ • High-risk country highlight  │  │ Queue depth: 127 alerts         │   │
│  └────────────────────────────────┘  └─────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ REAL-TIME ALERT FEED                                                │   │
│  │ [Auto-scrolling list with severity indicators]                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Frontend Tasks:**
- [ ] Create `LiveMetricsBar` component with WebSocket updates
- [ ] Build `TransactionCounter` with animated number transitions
- [ ] Implement `GeographicHeatmap` with Mapbox GL JS
- [ ] Create `SystemHealthPanel` with service status indicators
- [ ] Build `RealTimeAlertFeed` with auto-scroll and grouping
- [ ] Add `ProcessingLatencyChart` (sparkline)

**Backend Tasks:**
- [ ] Create `/api/monitoring/realtime/metrics` endpoint
- [ ] Implement metrics aggregation (tx/min, latency percentiles)
- [ ] Build geographic transaction aggregation
- [ ] Create system health check endpoint with service status

**Files to Create:**
```
apps/web/src/components/command-center/
├── index.tsx                    # Main command center layout
├── live-metrics-bar.tsx         # Top metrics strip
├── transaction-counter.tsx      # Animated live counter
├── geographic-heatmap.tsx       # Mapbox integration
├── system-health-panel.tsx      # Service status grid
├── real-time-alert-feed.tsx     # Auto-updating alert list
└── processing-latency.tsx       # Latency sparkline

apps/web/src/app/command-center/
└── page.tsx                     # Command center page

apps/api/src/api/
└── realtime.py                  # Real-time metrics endpoints
```

---

#### 1.3 Unified Alert Queue
**Priority:** 🔴 Critical
**Effort:** Medium

**Design:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ UNIFIED ALERT QUEUE                                            [Filters ▼] │
├─────────────────────────────────────────────────────────────────────────────┤
│ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐               │
│ │ All     │ │ AML     │ │ Fraud   │ │ Sanction│ │ KYC     │               │
│ │  (127)  │ │  (45)   │ │  (32)   │ │  (18)   │ │  (32)   │               │
│ └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ CUSTOMER VIEW (Toggle)                                                      │
│ ┌─────────────────────────────────────────────────────────────────────────┐│
│ │ John Doe (USR-847291)                                    Risk: HIGH     ││
│ │ ├─ 🔴 Structuring Alert (2h ago) - AI: 92% TP                          ││
│ │ ├─ 🟠 Velocity Alert (1d ago) - AI: 67% TP                             ││
│ │ └─ 🔴 Sanctions Match (3d ago) - AI: 95% TP                            ││
│ │                                                    [Investigate All]    ││
│ ├─────────────────────────────────────────────────────────────────────────┤│
│ │ ACME Corp (BIZ-123456)                                   Risk: MEDIUM  ││
│ │ └─ 🟡 Unusual Pattern (5h ago) - AI: 54% TP                            ││
│ │                                                    [Review]             ││
│ └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│ CHRONOLOGICAL VIEW (Toggle)                                                 │
│ ┌─────────────────────────────────────────────────────────────────────────┐│
│ │ Time    │ Customer     │ Type        │ Severity │ AI Score │ Actions   ││
│ │ 2h ago  │ John Doe     │ Structuring │ Critical │ 92%      │ [Review]  ││
│ │ 5h ago  │ ACME Corp    │ Pattern     │ Medium   │ 54%      │ [Review]  ││
│ │ 1d ago  │ John Doe     │ Velocity    │ High     │ 67%      │ [Review]  ││
│ └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

**Frontend Tasks:**
- [ ] Create `UnifiedAlertQueue` component
- [ ] Build customer-grouped view with collapsible sections
- [ ] Implement chronological view with sorting
- [ ] Add type filter tabs with counts
- [ ] Create bulk action toolbar
- [ ] Build alert row component with AI confidence badge

**Backend Tasks:**
- [ ] Create `/api/alerts/unified` endpoint with grouping options
- [ ] Implement customer-centric alert aggregation
- [ ] Add alert type statistics endpoint

**Files to Create:**
```
apps/web/src/components/alerts/
├── unified-alert-queue.tsx      # Main unified queue
├── customer-alert-group.tsx     # Grouped by customer
├── alert-type-tabs.tsx          # Filter tabs
├── alert-row.tsx                # Individual alert row
└── bulk-action-toolbar.tsx      # Bulk operations

apps/api/src/api/
└── alerts.py                    # Add unified endpoint
```

---

#### 1.4 Customer Investigation Console
**Priority:** 🟠 High
**Effort:** High

**Design:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ CUSTOMER: John Doe (USR-847291)                    Risk Score: 78 [HIGH]   │
├─────────────────────────────────────────────────────────────────────────────┤
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│ │ Overview │ │ Transact │ │ Alerts   │ │ Network  │ │ Regulat. │          │
│ └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ LEFT PANEL (60%)                      │ RIGHT PANEL (40%)                   │
│ ┌────────────────────────────────────┐│┌───────────────────────────────────┐│
│ │ RISK TIMELINE                      │││ AI INSIGHTS                       ││
│ │ ┌────────────────────────────────┐ │││ ┌─────────────────────────────────┐││
│ │ │ [Interactive timeline visual]  │ │││ │ "This customer shows patterns  │││
│ │ │ Jan 5: First transaction       │ │││ │  consistent with structuring.  │││
│ │ │ Jan 10: Risk score 45→78       │ │││ │  12 deposits near €10k limit   │││
│ │ │ Jan 12: Alert generated        │ │││ │  over 8 days. Recommend SAR."  │││
│ │ │ Jan 14: Case opened            │ │││ │              [File SAR] [Dismiss]│││
│ │ └────────────────────────────────┘ │││ └─────────────────────────────────┘││
│ │                                    │││                                    ││
│ │ EMBEDDED ANALYTICS                 │││ REGULATORY CONTEXT                 ││
│ │ ┌────────────────────────────────┐ │││ ┌─────────────────────────────────┐││
│ │ │ Transaction Volume (30d)       │ │││ │ 📜 AMLD6 Art. 18: EDD required │││
│ │ │ [Contextual chart - filtered]  │ │││ │ 📜 EU Reg 2015/847: Reporting  │││
│ │ │                                │ │││ │ [View Full Analysis]           │││
│ │ └────────────────────────────────┘ │││ └─────────────────────────────────┘││
│ │                                    │││                                    ││
│ │ UNIFIED ALERTS (This Customer)     │││ NETWORK PREVIEW                    ││
│ │ ┌────────────────────────────────┐ │││ ┌─────────────────────────────────┐││
│ │ │ [Embedded alert table]         │ │││ │ [Mini network graph]           │││
│ │ │                                │ │││ │ Connected: 24 users            │││
│ │ └────────────────────────────────┘ │││ │ [Expand Full Analysis]         │││
│ └────────────────────────────────────┘│└───────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

**Frontend Tasks:**
- [ ] Create `CustomerInvestigationConsole` layout
- [ ] Build `RiskTimeline` interactive component
- [ ] Create `EmbeddedAnalyticsPanel` with contextual filtering
- [ ] Build `AIInsightsPanel` with recommendations
- [ ] Create `RegulatoryContextPanel` with CELEX links
- [ ] Build `NetworkPreviewWidget` with expand capability
- [ ] Implement tab navigation (Overview, Transactions, Alerts, Network, Regulatory)

**Backend Tasks:**
- [ ] Create `/api/customers/{id}/investigation` comprehensive endpoint
- [ ] Build customer timeline aggregation
- [ ] Implement contextual analytics data endpoint

**Files to Create:**
```
apps/web/src/components/investigation/
├── customer-console.tsx         # Main investigation console
├── risk-timeline.tsx            # Interactive timeline
├── embedded-analytics.tsx       # Contextual charts
├── ai-insights-panel.tsx        # AI recommendations
├── regulatory-context.tsx       # CELEX integration
└── network-preview.tsx          # Mini network graph

apps/web/src/app/customers/[id]/
└── page.tsx                     # Customer detail page

apps/api/src/api/
└── customers.py                 # Customer investigation endpoint
```

---

## Phase 2: AI Intelligence Engine (Weeks 5-8)

### Objective
Build natural language rule creation and ML model monitoring

### Deliverables

#### 2.1 Natural Language Rule Builder
**Priority:** 🔴 Critical
**Effort:** High

**Design:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ AI RULE STUDIO                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ STEP 1: Describe Your Rule                                                  │
│ ┌─────────────────────────────────────────────────────────────────────────┐│
│ │ 💬 "Flag transactions over €9,500 that occur within 24 hours of        ││
│ │     another transaction from the same user to a different account"      ││
│ │                                                                         ││
│ │ Language: [English ▼]                           [Generate Rule] [Clear] ││
│ └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│ STEP 2: Review Generated Rule                                               │
│ ┌─────────────────────────────────────────────────────────────────────────┐│
│ │ Rule Name: Structuring Detection - Near-Threshold Split                 ││
│ │ Category: Structuring                                                    ││
│ │ Severity: High                                                           ││
│ │                                                                          ││
│ │ Conditions (Visual):                                                     ││
│ │ ┌─────────────────────────────────────────────────────────────────────┐ ││
│ │ │  IF  [amount] [>=] [9500]                                    [AND]  │ ││
│ │ │  AND [amount] [<]  [10000]                                   [AND]  │ ││
│ │ │  AND [user_has_transaction_in_last] [24h]                    [AND]  │ ││
│ │ │  AND [recipient_account] [!=] [previous_recipient]                  │ ││
│ │ │  THEN alert(severity: HIGH, type: STRUCTURING)                      │ ││
│ │ └─────────────────────────────────────────────────────────────────────┘ ││
│ │                                                                          ││
│ │ JSON Preview:                                                            ││
│ │ ┌─────────────────────────────────────────────────────────────────────┐ ││
│ │ │ {                                                                   │ ││
│ │ │   "name": "Structuring Detection - Near-Threshold Split",          │ ││
│ │ │   "conditions": [...],                                              │ ││
│ │ │   "aggregation": { "window": "24h", "group_by": "user_id" }        │ ││
│ │ │ }                                                                   │ ││
│ │ └─────────────────────────────────────────────────────────────────────┘ ││
│ └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│ STEP 3: Backtest & Deploy                                                   │
│ ┌─────────────────────────────────────────────────────────────────────────┐│
│ │ Backtest Results (90 days):                                             ││
│ │ • Would have triggered: 342 times                                       ││
│ │ • Estimated TP rate: 78% (based on similar rules)                       ││
│ │ • Overlaps with existing rules: 28%                                     ││
│ │ • Unique catches: 246                                                   ││
│ │                                                                          ││
│ │ [View Sample Matches]                                                    ││
│ │                                                                          ││
│ │ Deploy Options:                                                          ││
│ │ ○ Production (immediately active)                                        ││
│ │ ● Shadow Mode (log only, no alerts)                                      ││
│ │ ○ Scheduled (set activation date)                                        ││
│ │                                                                          ││
│ │                              [Save Draft] [Deploy to Shadow] [Deploy]   ││
│ └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

**Backend Tasks:**
- [ ] Create NLP rule parser using Claude API
- [ ] Build rule validation and conflict detection
- [ ] Implement backtest engine against historical data
- [ ] Create shadow mode infrastructure (log but don't alert)
- [ ] Build rule performance prediction model

**Frontend Tasks:**
- [ ] Create `NLPRuleBuilder` component
- [ ] Build `VisualRuleEditor` for manual adjustments
- [ ] Create `BacktestResultsPanel` with sample matches
- [ ] Build `DeploymentOptions` component
- [ ] Implement multi-language support (i18n)

**API Endpoints:**
```
POST /api/monitoring-rules/parse-nlp          # NLP → Rule DSL
POST /api/monitoring-rules/validate           # Conflict detection
POST /api/monitoring-rules/backtest           # Historical testing
POST /api/monitoring-rules/deploy             # Deploy with mode
GET  /api/monitoring-rules/{id}/shadow-stats  # Shadow mode results
```
Note: Legacy `/api/rules/*` is deprecated; prefer `/api/monitoring-rules/*`.

**Files to Create:**
```
apps/api/src/ai/
├── rule_parser.py               # NLP to rule conversion
└── rule_validator.py            # Conflict detection

apps/api/src/services/
├── backtest_engine.py           # Historical rule testing
└── shadow_mode.py               # Shadow mode tracking

apps/web/src/components/rules/
├── nlp-rule-builder.tsx         # Main NLP interface
├── visual-rule-editor.tsx       # Drag-drop rule builder
├── backtest-results.tsx         # Test results display
└── deployment-options.tsx       # Deploy mode selection

apps/web/src/app/rules/
├── page.tsx                     # Rules list
├── new/page.tsx                 # New rule (NLP)
└── [id]/page.tsx                # Rule detail/edit
```

---

#### 2.2 Rule Backtesting Engine
**Priority:** 🟠 High
**Effort:** High

**Backend Implementation:**

```python
# apps/api/src/services/backtest_engine.py

class BacktestEngine:
    """
    Evaluates rules against historical transaction data
    """

    async def backtest_rule(
        self,
        rule: MonitoringRule,
        days: int = 90,
        sample_size: int = 10000
    ) -> BacktestResult:
        """
        Run rule against historical data

        Returns:
        - trigger_count: How many times rule would have fired
        - sample_matches: Example transactions that matched
        - overlap_analysis: Rules that catch same transactions
        - estimated_tp_rate: Based on similar rule performance
        """
        pass

    async def compare_rules(
        self,
        rule_a: MonitoringRule,
        rule_b: MonitoringRule
    ) -> RuleComparison:
        """Compare two rules for overlap and performance"""
        pass
```

**Tasks:**
- [ ] Build historical transaction sampling
- [ ] Implement rule evaluation against samples
- [ ] Create overlap detection algorithm
- [ ] Build TP rate estimation from similar rules
- [ ] Implement comparison visualization

---

#### 2.3 Shadow Mode Infrastructure
**Priority:** 🟠 High
**Effort:** Medium

**Design:**
```
Shadow Mode Flow:

Transaction → Rules Engine → [Production Rules] → Alerts
                          ↘
                           [Shadow Rules] → Shadow Log (no alerts)
                                              ↓
                                         Performance Tracking
                                              ↓
                                         Promotion Decision
```

**Backend Tasks:**
- [ ] Create `ShadowAlert` model (separate from real alerts)
- [ ] Modify rules engine to evaluate shadow rules
- [ ] Build shadow performance tracking
- [ ] Create promotion workflow (shadow → production)

**Files to Create:**
```
apps/api/src/models/
└── shadow_alerts.py             # Shadow alert model

apps/api/src/services/
└── shadow_mode.py               # Shadow evaluation

apps/api/src/api/
└── shadow.py                    # Shadow mode endpoints
```

---

#### 2.4 ML Model Observatory
**Priority:** 🟡 Medium-High
**Effort:** High

**Design:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ML MODEL OBSERVATORY                                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ ACTIVE MODELS                                                               │
│ ┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐          │
│ │ Transaction Risk  │ │ Alert Triage      │ │ Fraud Ring        │          │
│ │ v2.3.1           │ │ v1.8.0            │ │ v1.2.0            │          │
│ │ ✅ Healthy        │ │ ⚠️ Drift Detected  │ │ ✅ Healthy         │          │
│ │ AUC: 0.94        │ │ AUC: 0.87 (↓0.03) │ │ AUC: 0.91        │          │
│ └───────────────────┘ └───────────────────┘ └───────────────────┘          │
│                                                                             │
│ MODEL DETAIL: Alert Triage v1.8.0                                           │
│ ┌─────────────────────────────────────────────────────────────────────────┐│
│ │                                                                          ││
│ │ SCORE DISTRIBUTION                    │ PERFORMANCE METRICS              ││
│ │ ┌───────────────────────────────┐    │ ┌─────────────────────────────┐  ││
│ │ │ [Histogram]                   │    │ │ AUC-ROC: 0.87 (▼0.03)       │  ││
│ │ │                               │    │ │ Precision: 0.82 (▼0.02)     │  ││
│ │ │ [Toggle: Raw / Percentile]    │    │ │ Recall: 0.79 (▼0.04)        │  ││
│ │ └───────────────────────────────┘    │ │ F1: 0.80 (▼0.03)            │  ││
│ │                                       │ │ FP Rate: 15.2% (▲2.1%)      │  ││
│ │ DRIFT ANALYSIS                        │ └─────────────────────────────┘  ││
│ │ ┌───────────────────────────────┐    │                                   ││
│ │ │ ⚠️ Feature drift detected:    │    │ RECOMMENDATIONS                   ││
│ │ │ • amount: +12% shift          │    │ ┌─────────────────────────────┐  ││
│ │ │ • country_code: new values    │    │ │ • Retrain with last 30d data│  ││
│ │ │                               │    │ │ • Review amount thresholds  │  ││
│ │ │ [View Feature Importance]     │    │ │ • Add new country codes     │  ││
│ │ └───────────────────────────────┘    │ └─────────────────────────────┘  ││
│ │                                                                          ││
│ └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

**Backend Tasks:**
- [ ] Create model registry with versioning
- [ ] Implement score distribution tracking
- [ ] Build drift detection algorithm (PSI, KS test)
- [ ] Create performance metric tracking over time
- [ ] Build automated alerting for drift

**Frontend Tasks:**
- [ ] Create `ModelObservatory` dashboard
- [ ] Build `ScoreDistributionChart` with toggle
- [ ] Create `DriftAnalysisPanel`
- [ ] Build `PerformanceMetricsCard`
- [ ] Implement model comparison view

**Files to Create:**
```
apps/api/src/ml/
├── __init__.py
├── model_registry.py            # Model versioning
├── drift_detection.py           # Statistical drift tests
├── performance_tracker.py       # Metric tracking
└── alerts.py                    # Drift alerting

apps/web/src/components/ml/
├── model-observatory.tsx        # Main dashboard
├── score-distribution.tsx       # Histogram with toggle
├── drift-analysis.tsx           # Drift visualization
├── performance-metrics.tsx      # Metrics cards
└── model-comparison.tsx         # A/B comparison

apps/web/src/app/models/
├── page.tsx                     # Model list
└── [id]/page.tsx                # Model detail
```

---

## Phase 3: Compliance Suite (Weeks 9-12)

### Objective
Build SAR lifecycle management and comprehensive reporting

### Deliverables

#### 3.1 SAR Lifecycle Manager
**Priority:** 🔴 Critical
**Effort:** Medium

**Design:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ SAR LIFECYCLE MANAGER                                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ PIPELINE OVERVIEW                                                           │
│ ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐           │
│ │ Draft   │→→│ Review  │→→│ Approved│→→│ Filed   │→→│ Acked   │           │
│ │   12    │  │    5    │  │    3    │  │    8    │  │   127   │           │
│ └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘           │
│                                                                             │
│ SAR DETAIL: SAR-2024-089                                                    │
│ ┌─────────────────────────────────────────────────────────────────────────┐│
│ │                                                                          ││
│ │ VISUAL LIFECYCLE                                                         ││
│ │ ○─────●─────●─────●─────●─────○                                          ││
│ │ Draft  Review  Approved  Filed  Acked  Closed                            ││
│ │ Jan 8  Jan 10  Jan 12    Jan 15 Jan 17                                   ││
│ │                                                                          ││
│ │ FILING STATUS                                                            ││
│ │ ┌─────────────────────────────────────────────────────────────────────┐ ││
│ │ │ ✅ Accepted by FinCEN                                               │ ││
│ │ │ Reference: BSA-2024-00847291                                        │ ││
│ │ │ Acknowledged: January 17, 2024 14:32 UTC                            │ ││
│ │ │                                                                      │ ││
│ │ │ Timeline:                                                            │ ││
│ │ │ • Jan 15 14:00 - Filed via FinCEN BSA E-Filing                      │ ││
│ │ │ • Jan 15 14:01 - Submission received                                │ ││
│ │ │ • Jan 17 14:32 - Accepted (no errors)                               │ ││
│ │ └─────────────────────────────────────────────────────────────────────┘ ││
│ │                                                                          ││
│ │ AI NARRATIVE                                                             ││
│ │ ┌─────────────────────────────────────────────────────────────────────┐ ││
│ │ │ "Between January 5-14, 2024, subject conducted 12 cash deposits     │ ││
│ │ │  totaling €98,500 structured to avoid reporting thresholds..."      │ ││
│ │ │                                              [Edit] [Regenerate]    │ ││
│ │ └─────────────────────────────────────────────────────────────────────┘ ││
│ │                                                                          ││
│ │ REGULATORY BASIS                                                         ││
│ │ • AMLD6 Art. 33: Suspicious transaction reporting                       ││
│ │ • EU Reg 2015/847: Funds transfer information requirements              ││
│ │                                                                          ││
│ └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

**Backend Tasks:**
- [ ] Create SAR status workflow state machine
- [ ] Implement filing acknowledgment tracking
- [ ] Build FinCEN/goAML response parsing
- [ ] Create SAR amendment workflow
- [ ] Build SAR statistics aggregation

**Frontend Tasks:**
- [ ] Create `SARLifecycleTracker` visual component
- [ ] Build `SARPipeline` overview with counts
- [ ] Create `FilingStatusPanel` with timeline
- [ ] Build `SARNarrativeEditor` with AI regeneration
- [ ] Implement `RegulatoryBasisPanel`

**Files to Create:**
```
apps/api/src/compliance/
├── sar_workflow.py              # State machine
├── filing_tracker.py            # Acknowledgment tracking
└── sar_statistics.py            # Aggregations

apps/web/src/components/sar/
├── lifecycle-tracker.tsx        # Visual lifecycle
├── pipeline-overview.tsx        # Pipeline counts
├── filing-status.tsx            # Filing details
├── narrative-editor.tsx         # AI narrative
└── regulatory-basis.tsx         # CELEX links

apps/web/src/app/sar/
├── page.tsx                     # SAR list
└── [id]/page.tsx                # SAR detail
```

---

#### 3.2 Report Generation Engine
**Priority:** 🟠 High
**Effort:** High

**Supported Formats:**
- PDF (regulatory reports, executive summaries)
- Excel (detailed data exports)
- CSV (raw data)
- JSON (API consumption)

**Report Types:**
1. **Regulatory Reports**
   - SAR Summary (monthly/quarterly)
   - CTR Summary (daily)
   - AMLD6 Compliance Report
   - Risk Assessment Report

2. **Executive Reports**
   - KPI Dashboard Export
   - Alert Volume Analysis
   - Case Resolution Summary
   - AI Performance Report

3. **Audit Reports**
   - Complete Audit Trail
   - Rule Change History
   - User Activity Log
   - Data Access Log

**Backend Tasks:**
- [ ] Integrate PDF generation (WeasyPrint or ReportLab)
- [ ] Create Excel generation (openpyxl)
- [ ] Build report template system
- [ ] Implement scheduled report execution
- [ ] Create report delivery (email, S3)

**Frontend Tasks:**
- [ ] Create `ReportCenter` dashboard
- [ ] Build `ReportTemplateSelector`
- [ ] Create `ScheduleReportModal`
- [ ] Build `ReportHistory` with downloads

**Files to Create:**
```
apps/api/src/reporting/
├── __init__.py
├── pdf_generator.py             # PDF creation
├── excel_generator.py           # Excel creation
├── templates/                   # Report templates
│   ├── sar_summary.html
│   ├── executive_summary.html
│   └── audit_trail.html
├── scheduler.py                 # Scheduled execution
└── delivery.py                  # Email/S3 delivery

apps/web/src/components/reports/
├── report-center.tsx            # Main dashboard
├── template-selector.tsx        # Report type picker
├── schedule-modal.tsx           # Scheduling UI
└── report-history.tsx           # Download history

apps/web/src/app/reports/
├── page.tsx                     # Report center
└── [id]/page.tsx                # Report detail
```

---

#### 3.3 Audit Trail System
**Priority:** 🟠 High
**Effort:** Medium

**Events to Track:**
- Alert actions (create, update, resolve, escalate)
- Case actions (create, assign, close, SAR filed)
- Rule changes (create, edit, enable/disable, delete)
- User actions (login, logout, permission changes)
- Data access (customer views, exports)
- System events (API calls, errors)

**Design:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ AUDIT TRAIL                                                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ FILTERS                                                                     │
│ ┌─────────────────────────────────────────────────────────────────────────┐│
│ │ Date: [Jan 1] to [Jan 31]  User: [All ▼]  Action: [All ▼]  Entity: [All]││
│ │                                                         [Apply] [Clear] ││
│ └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│ AUDIT LOG                                                                   │
│ ┌─────────────────────────────────────────────────────────────────────────┐│
│ │ Timestamp           │ User        │ Action      │ Entity    │ Details   ││
│ ├─────────────────────────────────────────────────────────────────────────┤│
│ │ Jan 15 14:32:01    │ john@co.com │ SAR Filed   │ SAR-089   │ [View]    ││
│ │ Jan 15 14:30:45    │ john@co.com │ Approved    │ SAR-089   │ [View]    ││
│ │ Jan 15 14:28:12    │ jane@co.com │ Escalated   │ ALT-2847  │ [View]    ││
│ │ Jan 15 14:25:00    │ system      │ AI Triage   │ ALT-2847  │ [View]    ││
│ │ Jan 15 14:20:33    │ john@co.com │ Rule Edit   │ RULE-15   │ [View]    ││
│ └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│ DETAIL VIEW: SAR Filed                                                      │
│ ┌─────────────────────────────────────────────────────────────────────────┐│
│ │ Timestamp: January 15, 2024 14:32:01 UTC                                ││
│ │ User: john@company.com (Compliance Officer)                              ││
│ │ IP Address: 192.168.1.100                                                ││
│ │ Action: SAR_FILED                                                        ││
│ │ Entity: SAR-089                                                          ││
│ │ Changes:                                                                  ││
│ │   status: "approved" → "filed"                                           ││
│ │   filed_at: null → "2024-01-15T14:32:01Z"                                ││
│ │   fincen_reference: null → "BSA-2024-00847291"                           ││
│ └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

**Backend Tasks:**
- [ ] Create `AuditLog` model with indexes
- [ ] Build audit middleware for automatic logging
- [ ] Implement change diff tracking
- [ ] Create audit search/filter API
- [ ] Build audit export functionality

**Frontend Tasks:**
- [ ] Create `AuditTrail` dashboard
- [ ] Build `AuditFilters` component
- [ ] Create `AuditLogTable` with pagination
- [ ] Build `AuditDetailModal`
- [ ] Implement audit export UI

**Files to Create:**
```
apps/api/src/audit/
├── __init__.py
├── models.py                    # AuditLog model
├── middleware.py                # Auto-logging middleware
├── diff_tracker.py              # Change detection
└── api.py                       # Audit endpoints

apps/web/src/components/audit/
├── audit-trail.tsx              # Main dashboard
├── audit-filters.tsx            # Filter panel
├── audit-table.tsx              # Log table
└── audit-detail.tsx             # Detail modal

apps/web/src/app/audit/
└── page.tsx                     # Audit trail page
```

---

## Phase 4: Enterprise Polish (Weeks 13-16)

### Objective
Production hardening, performance optimization, and enterprise features

### Deliverables

#### 4.1 Currency Normalization
**Priority:** 🟡 Medium
**Effort:** Low

**Tasks:**
- [ ] Create currency conversion service with ECB rates
- [ ] Add base currency setting (per organization)
- [ ] Implement normalized amount display throughout UI
- [ ] Build currency comparison tooltips

#### 4.2 Enhanced Sanctions Screening
**Priority:** 🟡 Medium
**Effort:** Medium

**Tasks:**
- [ ] Add SWIFT/BIC code screening
- [ ] Implement additional watchlists (10+)
- [ ] Build real-time list update notifications
- [ ] Create match explanation UI

#### 4.3 Performance Optimization
**Priority:** 🟠 High
**Effort:** High

**Tasks:**
- [ ] Implement database query optimization
- [ ] Add Redis caching layer
- [ ] Build lazy loading for large lists
- [ ] Optimize WebSocket message batching
- [ ] Implement virtual scrolling for tables

#### 4.4 Mobile Responsiveness
**Priority:** 🟡 Medium
**Effort:** Medium

**Tasks:**
- [ ] Create mobile navigation (hamburger menu)
- [ ] Optimize charts for mobile
- [ ] Build mobile-specific alert actions
- [ ] Implement touch gestures

#### 4.5 White-Label Support
**Priority:** 🟢 Low
**Effort:** Medium

**Tasks:**
- [ ] Create theming system (CSS variables)
- [ ] Build logo/branding configuration
- [ ] Implement custom domain support
- [ ] Create tenant isolation

---

## Technical Architecture

### Backend Stack
```
FastAPI (async Python web framework)
├── SQLAlchemy (ORM)
├── PostgreSQL (primary database)
├── Redis (caching, pub/sub, sessions)
├── Celery (background tasks)
├── WebSockets (real-time communication)
└── Anthropic Claude API (AI/ML)
```

### Frontend Stack
```
Next.js 14+ (React framework)
├── TypeScript (type safety)
├── Tailwind CSS (styling)
├── Zustand (state management)
├── TanStack Query (data fetching)
├── Recharts (charts)
├── Mapbox GL JS (maps)
├── Framer Motion (animations)
└── WebSocket (real-time)
```

### Infrastructure
```
Docker (containerization)
├── Kubernetes (orchestration) [production]
├── AWS/GCP (cloud provider)
├── CloudFlare (CDN, DDoS)
├── Datadog (monitoring)
└── Sentry (error tracking)
```

---

## Quality Standards

### Code Quality
- [ ] 80%+ test coverage for critical paths
- [ ] TypeScript strict mode enabled
- [ ] ESLint + Prettier configured
- [ ] Pre-commit hooks (Husky)
- [ ] Automated code review (SonarQube)

### Security
- [ ] OWASP Top 10 compliance
- [ ] Penetration testing before launch
- [ ] SOC 2 Type II preparation
- [ ] Data encryption at rest and in transit
- [ ] Role-based access control (RBAC)

### Performance
- [ ] API response time < 200ms (P95)
- [ ] Dashboard load time < 3s
- [ ] WebSocket latency < 100ms
- [ ] Database query time < 50ms (P95)

### Accessibility
- [ ] WCAG 2.1 AA compliance
- [ ] Keyboard navigation
- [ ] Screen reader support
- [ ] Color contrast compliance

---

## Risk Register

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Claude API rate limits | High | Medium | Implement caching, fallback models |
| WebSocket scalability | High | Medium | Redis pub/sub, horizontal scaling |
| PDF generation performance | Medium | High | Async generation, queue system |
| Data migration complexity | High | Low | Incremental migration, rollback plan |
| Regulatory requirement changes | Medium | Medium | Modular compliance architecture |

---

## Success Metrics

### Phase 1 Success Criteria
- [ ] WebSocket latency < 100ms
- [ ] Live dashboard updates within 1 second
- [ ] Unified alert queue loads < 2 seconds
- [ ] Zero production WebSocket disconnections

### Phase 2 Success Criteria
- [ ] NLP rule accuracy > 85%
- [ ] Backtest execution < 30 seconds for 90 days
- [ ] Shadow mode zero impact on production
- [ ] Drift detection accuracy > 90%

### Phase 3 Success Criteria
- [ ] SAR filing success rate > 99%
- [ ] PDF generation < 5 seconds
- [ ] Report scheduling 100% reliability
- [ ] Audit trail query < 500ms

### Phase 4 Success Criteria
- [ ] Page load time < 3 seconds
- [ ] Mobile usability score > 90
- [ ] Zero security vulnerabilities (critical/high)
- [ ] 99.9% uptime

---

## Next Steps

1. **Immediate:** Review and approve this implementation plan
2. **Week 1:** Begin Phase 1 with WebSocket infrastructure
3. **Ongoing:** Weekly progress reviews and adjustments

---

*Document Version: 1.0*
*Last Updated: January 2025*
*Author: Claude AI Assistant*
