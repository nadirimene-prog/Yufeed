# Yufeed Dashboard Implementation - Agent Assignments

## Overview

This document defines specialized AI agents that will work on different aspects of the Yufeed dashboard implementation. Each agent has a specific focus area, clear responsibilities, and defined deliverables.

---

## Agent Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        YUFEED IMPLEMENTATION AGENTS                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │ AGENT-REALTIME  │  │ AGENT-FRONTEND  │  │ AGENT-BACKEND   │             │
│  │ WebSocket &     │  │ UI Components   │  │ API & Services  │             │
│  │ Live Data       │  │ & Pages         │  │                 │             │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘             │
│           │                    │                    │                       │
│           └────────────────────┼────────────────────┘                       │
│                                │                                            │
│  ┌─────────────────┐  ┌───────┴─────────┐  ┌─────────────────┐             │
│  │ AGENT-AI        │  │ ORCHESTRATOR    │  │ AGENT-REPORTS   │             │
│  │ NLP Rules &     │  │ Coordination &  │  │ PDF/Excel &     │             │
│  │ ML Monitoring   │  │ Integration     │  │ Scheduling      │             │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘             │
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │ AGENT-COMPLIANCE│  │ AGENT-TESTING   │  │ AGENT-INFRA     │             │
│  │ SAR Lifecycle & │  │ Unit & E2E      │  │ Docker, Redis   │             │
│  │ Audit Trail     │  │ Tests           │  │ Performance     │             │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 4 Agents (Enterprise Polish)

To cover Phase 4 deliverables, two additional agents are defined:

- AGENT-ENTERPRISE-FE: Mobile UX, theming/branding, sanctions UI, currency display, frontend performance
- AGENT-ENTERPRISE-BE: Currency services, sanctions screening, performance optimization, tenant isolation, custom domains

---

## Agent 1: AGENT-REALTIME

### Mission
Build real-time infrastructure including WebSocket communication, live data updates, and the Command Center dashboard.

### Responsibilities
1. WebSocket server implementation
2. Real-time event broadcasting
3. Connection management
4. Live metrics aggregation
5. Geographic heatmap data

### Technical Skills Required
- FastAPI WebSockets
- Redis pub/sub
- React hooks for WebSocket
- Zustand state management
- Mapbox GL JS

### Assigned Tasks

#### Task 1.1: WebSocket Server Infrastructure
**Priority:** Critical | **Effort:** High

```python
# Create these files:
# apps/api/src/websocket/__init__.py
# apps/api/src/websocket/manager.py
# apps/api/src/websocket/events.py
# apps/api/src/websocket/broadcaster.py
# apps/api/src/websocket/auth.py

# manager.py - Key implementation:
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.redis = None

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        await self.subscribe_to_channels(client_id)

    async def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def broadcast(self, event_type: str, data: dict):
        # Publish to Redis for horizontal scaling
        await self.redis.publish(f"ws:{event_type}", json.dumps(data))

    async def send_personal(self, client_id: str, data: dict):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(data)
```

**Deliverables:**
- [ ] `ConnectionManager` class with connect/disconnect/broadcast
- [ ] Redis pub/sub integration for horizontal scaling
- [ ] JWT authentication for WebSocket connections
- [ ] Heartbeat mechanism (ping/pong every 30s)
- [ ] Auto-reconnection logic
- [ ] Event types: `transaction.new`, `alert.created`, `alert.updated`, `system.health`

---

#### Task 1.2: Frontend WebSocket Hook
**Priority:** Critical | **Effort:** Medium

```typescript
// Create: apps/web/src/hooks/useWebSocket.ts

interface WebSocketOptions {
  url: string;
  onMessage: (event: WebSocketEvent) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  reconnectAttempts?: number;
  reconnectInterval?: number;
}

export function useWebSocket(options: WebSocketOptions) {
  const [status, setStatus] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected');
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectCount = useRef(0);

  const connect = useCallback(() => {
    const token = getAuthToken();
    const ws = new WebSocket(`${options.url}?token=${token}`);

    ws.onopen = () => {
      setStatus('connected');
      reconnectCount.current = 0;
      options.onConnect?.();
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      options.onMessage(data);
    };

    ws.onclose = () => {
      setStatus('disconnected');
      options.onDisconnect?.();
      // Auto-reconnect with exponential backoff
      if (reconnectCount.current < (options.reconnectAttempts || 5)) {
        setTimeout(() => {
          reconnectCount.current++;
          connect();
        }, Math.min(1000 * Math.pow(2, reconnectCount.current), 30000));
      }
    };

    wsRef.current = ws;
  }, [options]);

  return { status, connect, disconnect: () => wsRef.current?.close() };
}
```

**Deliverables:**
- [ ] `useWebSocket` hook with auto-reconnection
- [ ] `useRealTimeStore` Zustand store for live data
- [ ] `ConnectionStatus` indicator component
- [ ] Event subscription/unsubscription helpers

---

#### Task 1.3: Live Metrics Aggregation API
**Priority:** Critical | **Effort:** Medium

```python
# Create: apps/api/src/api/realtime.py

@router.get("/metrics/live")
async def get_live_metrics(db: Session = Depends(get_db)):
    """
    Returns real-time metrics for Command Center
    """
    now = datetime.utcnow()
    one_minute_ago = now - timedelta(minutes=1)
    one_hour_ago = now - timedelta(hours=1)

    return {
        "transactions_per_minute": await count_transactions(db, one_minute_ago, now),
        "active_alerts": await count_alerts(db, status="pending"),
        "critical_alerts": await count_alerts(db, severity="critical", status="pending"),
        "system_health": await get_system_health(),
        "processing_latency": await get_latency_percentiles(),
        "geographic_distribution": await get_transaction_geo_distribution(db, one_hour_ago),
    }

async def get_latency_percentiles():
    """Get P50, P95, P99 latency from recent requests"""
    # Implementation using Redis sorted sets or Prometheus
    pass

async def get_transaction_geo_distribution(db: Session, since: datetime):
    """Aggregate transactions by country for heatmap"""
    result = db.query(
        Transaction.country_code,
        func.count(Transaction.id).label('count'),
        func.sum(Transaction.amount).label('total_amount')
    ).filter(
        Transaction.created_at >= since
    ).group_by(
        Transaction.country_code
    ).all()

    return [{"country": r.country_code, "count": r.count, "amount": r.total_amount} for r in result]
```

**Deliverables:**
- [ ] `/api/realtime/metrics/live` endpoint
- [ ] Transaction rate calculation (tx/min, tx/sec)
- [ ] Latency percentile tracking (P50, P95, P99)
- [ ] Geographic aggregation for heatmap
- [ ] System health check endpoint
- [ ] Caching with 5-second TTL

---

#### Task 1.4: Command Center Dashboard
**Priority:** Critical | **Effort:** High

```typescript
// Create: apps/web/src/components/command-center/index.tsx

export function CommandCenter() {
  const { metrics, status } = useRealTimeStore();

  return (
    <div className="grid grid-cols-12 gap-6">
      {/* Top Metrics Bar */}
      <div className="col-span-12">
        <LiveMetricsBar metrics={metrics} />
      </div>

      {/* Geographic Heatmap */}
      <div className="col-span-8">
        <GeographicHeatmap data={metrics.geoDistribution} />
      </div>

      {/* System Health */}
      <div className="col-span-4">
        <SystemHealthPanel health={metrics.systemHealth} />
      </div>

      {/* Real-time Alert Feed */}
      <div className="col-span-12">
        <RealTimeAlertFeed />
      </div>
    </div>
  );
}
```

**Deliverables:**
- [ ] `CommandCenter` layout component
- [ ] `LiveMetricsBar` with animated counters
- [ ] `TransactionCounter` with number animation
- [ ] `GeographicHeatmap` with Mapbox integration
- [ ] `SystemHealthPanel` with service status
- [ ] `ProcessingLatencyChart` sparkline
- [ ] `RealTimeAlertFeed` with auto-scroll

**Component Files to Create:**
```
apps/web/src/components/command-center/
├── index.tsx
├── live-metrics-bar.tsx
├── transaction-counter.tsx
├── geographic-heatmap.tsx
├── system-health-panel.tsx
├── processing-latency.tsx
└── real-time-alert-feed.tsx
```

---

#### Task 1.5: Geographic Heatmap Component
**Priority:** High | **Effort:** High

```typescript
// Create: apps/web/src/components/command-center/geographic-heatmap.tsx

import mapboxgl from 'mapbox-gl';
import { useEffect, useRef } from 'react';

interface GeoData {
  country: string;
  count: number;
  amount: number;
  riskLevel?: 'low' | 'medium' | 'high';
}

export function GeographicHeatmap({ data }: { data: GeoData[] }) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);

  useEffect(() => {
    if (!mapContainer.current) return;

    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: 'mapbox://styles/mapbox/dark-v11',
      center: [10, 50], // Europe center
      zoom: 3,
    });

    // Add choropleth layer
    map.current.on('load', () => {
      map.current?.addSource('countries', {
        type: 'vector',
        url: 'mapbox://mapbox.country-boundaries-v1',
      });

      map.current?.addLayer({
        id: 'country-fills',
        type: 'fill',
        source: 'countries',
        'source-layer': 'country_boundaries',
        paint: {
          'fill-color': [
            'interpolate',
            ['linear'],
            ['get', 'transaction_count'],
            0, '#1a1a2e',
            100, '#16213e',
            500, '#0f3460',
            1000, '#e94560',
          ],
          'fill-opacity': 0.8,
        },
      });
    });

    return () => map.current?.remove();
  }, []);

  // Update data on change
  useEffect(() => {
    if (!map.current || !data) return;
    // Update choropleth with new data
    updateChoroplethData(map.current, data);
  }, [data]);

  return (
    <div className="relative h-[400px] rounded-lg overflow-hidden">
      <div ref={mapContainer} className="absolute inset-0" />
      <div className="absolute top-4 left-4 bg-slate-900/90 p-3 rounded-lg">
        <h3 className="text-sm font-medium text-white">Transaction Origins</h3>
        <p className="text-xs text-slate-400">Last hour</p>
      </div>
      <Legend />
    </div>
  );
}
```

**Deliverables:**
- [ ] Mapbox GL JS integration
- [ ] Choropleth layer for country transaction volume
- [ ] High-risk country highlighting (red border)
- [ ] Click interaction for country details
- [ ] Real-time data updates
- [ ] Legend component
- [ ] Dark theme styling

---

### Agent 1 Acceptance Criteria

| Criteria | Metric |
|----------|--------|
| WebSocket connection time | < 500ms |
| WebSocket message latency | < 100ms |
| Reconnection success rate | > 99% |
| Live metrics refresh rate | 1 second |
| Heatmap render time | < 200ms |
| Memory usage (WebSocket) | < 50MB per 1000 connections |

---

## Agent 2: AGENT-FRONTEND

### Mission
Build UI components and pages for the unified investigation experience, including the Unified Alert Queue and Customer Investigation Console.

### Responsibilities
1. Unified Alert Queue component
2. Customer Investigation Console
3. Embedded analytics components
4. UI/UX consistency and polish
5. Responsive design

### Technical Skills Required
- React/Next.js
- TypeScript
- Tailwind CSS
- TanStack Table
- Recharts
- Framer Motion

### Assigned Tasks

#### Task 2.1: Unified Alert Queue Component
**Priority:** Critical | **Effort:** Medium

```typescript
// Create: apps/web/src/components/alerts/unified-alert-queue.tsx

interface UnifiedAlertQueueProps {
  initialView?: 'customer' | 'chronological';
  onAlertSelect?: (alert: Alert) => void;
}

export function UnifiedAlertQueue({ initialView = 'customer', onAlertSelect }: UnifiedAlertQueueProps) {
  const [view, setView] = useState(initialView);
  const [selectedTypes, setSelectedTypes] = useState<string[]>(['all']);
  const { data: alerts, isLoading } = useAlerts({ grouped: view === 'customer' });

  return (
    <div className="space-y-4">
      {/* Type Filter Tabs */}
      <AlertTypeTabs
        types={['all', 'aml', 'fraud', 'sanctions', 'kyc']}
        selected={selectedTypes}
        onChange={setSelectedTypes}
        counts={alerts?.typeCounts}
      />

      {/* View Toggle */}
      <div className="flex items-center justify-between">
        <ViewToggle value={view} onChange={setView} />
        <BulkActionToolbar selectedCount={selectedAlerts.length} />
      </div>

      {/* Alert List */}
      {view === 'customer' ? (
        <CustomerGroupedAlerts
          groups={alerts?.customerGroups}
          onAlertSelect={onAlertSelect}
        />
      ) : (
        <ChronologicalAlerts
          alerts={alerts?.items}
          onAlertSelect={onAlertSelect}
        />
      )}
    </div>
  );
}
```

**Deliverables:**
- [ ] `UnifiedAlertQueue` main component
- [ ] `AlertTypeTabs` with dynamic counts
- [ ] `CustomerGroupedAlerts` collapsible groups
- [ ] `ChronologicalAlerts` sortable table
- [ ] `AlertRow` with AI confidence badge
- [ ] `BulkActionToolbar` for multi-select actions
- [ ] `ViewToggle` (customer/chronological)
- [ ] Keyboard navigation support

**Files to Create:**
```
apps/web/src/components/alerts/
├── unified-alert-queue.tsx
├── alert-type-tabs.tsx
├── customer-grouped-alerts.tsx
├── chronological-alerts.tsx
├── alert-row.tsx
├── bulk-action-toolbar.tsx
└── view-toggle.tsx
```

---

#### Task 2.2: Customer Investigation Console
**Priority:** Critical | **Effort:** High

```typescript
// Create: apps/web/src/components/investigation/customer-console.tsx

interface CustomerConsoleProps {
  customerId: string;
}

export function CustomerConsole({ customerId }: CustomerConsoleProps) {
  const { data: customer, isLoading } = useCustomerInvestigation(customerId);
  const [activeTab, setActiveTab] = useState('overview');

  return (
    <div className="space-y-6">
      {/* Header with Risk Score */}
      <CustomerHeader customer={customer} />

      {/* Tab Navigation */}
      <TabNavigation
        tabs={['overview', 'transactions', 'alerts', 'network', 'regulatory']}
        active={activeTab}
        onChange={setActiveTab}
      />

      {/* Main Content */}
      <div className="grid grid-cols-12 gap-6">
        {/* Left Panel - 60% */}
        <div className="col-span-8 space-y-6">
          {activeTab === 'overview' && (
            <>
              <RiskTimeline events={customer?.timeline} />
              <EmbeddedAnalytics customerId={customerId} />
              <CustomerAlerts customerId={customerId} />
            </>
          )}
          {activeTab === 'transactions' && (
            <TransactionHistory customerId={customerId} />
          )}
          {activeTab === 'alerts' && (
            <UnifiedAlertQueue customerId={customerId} />
          )}
          {activeTab === 'network' && (
            <NetworkAnalysis customerId={customerId} />
          )}
          {activeTab === 'regulatory' && (
            <RegulatoryAnalysis customerId={customerId} />
          )}
        </div>

        {/* Right Panel - 40% */}
        <div className="col-span-4 space-y-6">
          <AIInsightsPanel customerId={customerId} />
          <RegulatoryContextPanel customerId={customerId} />
          <NetworkPreviewWidget customerId={customerId} />
        </div>
      </div>
    </div>
  );
}
```

**Deliverables:**
- [ ] `CustomerConsole` main layout
- [ ] `CustomerHeader` with risk badge and actions
- [ ] `TabNavigation` component
- [ ] `RiskTimeline` interactive timeline
- [ ] `EmbeddedAnalytics` contextual charts
- [ ] `AIInsightsPanel` with recommendations
- [ ] `RegulatoryContextPanel` with CELEX links
- [ ] `NetworkPreviewWidget` mini graph

**Files to Create:**
```
apps/web/src/components/investigation/
├── customer-console.tsx
├── customer-header.tsx
├── tab-navigation.tsx
├── risk-timeline.tsx
├── embedded-analytics.tsx
├── ai-insights-panel.tsx
├── regulatory-context-panel.tsx
└── network-preview-widget.tsx

apps/web/src/app/customers/[id]/
└── page.tsx
```

---

#### Task 2.3: Risk Timeline Component
**Priority:** High | **Effort:** Medium

```typescript
// Create: apps/web/src/components/investigation/risk-timeline.tsx

interface TimelineEvent {
  id: string;
  timestamp: string;
  type: 'risk_change' | 'alert' | 'case' | 'sar' | 'transaction';
  title: string;
  description: string;
  severity?: 'critical' | 'high' | 'medium' | 'low';
  metadata?: Record<string, any>;
}

export function RiskTimeline({ events }: { events: TimelineEvent[] }) {
  return (
    <div className="bg-slate-900 rounded-lg p-6">
      <h3 className="text-lg font-semibold mb-4">Risk Timeline</h3>

      <div className="relative">
        {/* Vertical line */}
        <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-slate-700" />

        {/* Events */}
        <div className="space-y-4">
          {events.map((event, index) => (
            <motion.div
              key={event.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.1 }}
              className="relative pl-10"
            >
              {/* Event dot */}
              <div className={cn(
                "absolute left-2.5 w-3 h-3 rounded-full border-2 border-slate-900",
                getEventColor(event.type, event.severity)
              )} />

              {/* Event content */}
              <div className="bg-slate-800 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-slate-400">
                    {formatDate(event.timestamp)}
                  </span>
                  <EventTypeBadge type={event.type} />
                </div>
                <h4 className="font-medium">{event.title}</h4>
                <p className="text-sm text-slate-400 mt-1">{event.description}</p>

                {/* Expandable details */}
                {event.metadata && (
                  <EventDetails metadata={event.metadata} />
                )}
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}
```

**Deliverables:**
- [ ] `RiskTimeline` component with animations
- [ ] Event type differentiation (colors, icons)
- [ ] Expandable event details
- [ ] Risk score change visualization
- [ ] Click-to-navigate to related entities
- [ ] Timeline filtering by event type

---

#### Task 2.4: Embedded Analytics Component
**Priority:** High | **Effort:** Medium

```typescript
// Create: apps/web/src/components/investigation/embedded-analytics.tsx

interface EmbeddedAnalyticsProps {
  customerId: string;
  dateRange?: { from: Date; to: Date };
}

export function EmbeddedAnalytics({ customerId, dateRange }: EmbeddedAnalyticsProps) {
  const { data: analytics } = useCustomerAnalytics(customerId, dateRange);

  return (
    <div className="bg-slate-900 rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">Transaction Analysis</h3>
        <DateRangePicker value={dateRange} onChange={setDateRange} />
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Volume Chart */}
        <div>
          <h4 className="text-sm font-medium text-slate-400 mb-2">Volume Over Time</h4>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={analytics?.volumeByDay}>
              <defs>
                <linearGradient id="volumeGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Area type="monotone" dataKey="volume" stroke="#3b82f6" fill="url(#volumeGradient)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Amount Distribution */}
        <div>
          <h4 className="text-sm font-medium text-slate-400 mb-2">Amount Distribution</h4>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={analytics?.amountBuckets}>
              <XAxis dataKey="range" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="count" fill="#8b5cf6" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Anomaly Indicators */}
      {analytics?.anomalies?.length > 0 && (
        <AnomalyIndicators anomalies={analytics.anomalies} />
      )}
    </div>
  );
}
```

**Deliverables:**
- [ ] `EmbeddedAnalytics` component
- [ ] Transaction volume chart (area)
- [ ] Amount distribution histogram
- [ ] Country breakdown pie chart
- [ ] Anomaly highlighting
- [ ] Date range filtering
- [ ] Auto-refresh on data change

---

### Agent 2 Acceptance Criteria

| Criteria | Metric |
|----------|--------|
| Component render time | < 100ms |
| Table with 1000 rows | < 500ms initial load |
| Lighthouse accessibility | > 90 |
| TypeScript coverage | 100% |
| Mobile responsiveness | All breakpoints |

---

## Agent 3: AGENT-BACKEND

### Mission
Build backend API endpoints and services for alerts, customers, and investigation features.

### Responsibilities
1. Unified alert API endpoints
2. Customer investigation endpoints
3. Data aggregation services
4. Performance optimization
5. Caching layer

### Technical Skills Required
- FastAPI
- SQLAlchemy
- PostgreSQL
- Redis
- Python async/await

### Assigned Tasks

#### Task 3.1: Unified Alert API
**Priority:** Critical | **Effort:** Medium

```python
# Modify: apps/api/src/api/alerts.py

@router.get("/unified")
async def get_unified_alerts(
    group_by: Optional[str] = Query(None, enum=["customer", "type"]),
    types: Optional[List[str]] = Query(None),
    status: Optional[str] = None,
    severity: Optional[str] = None,
    customer_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    Get alerts with optional grouping by customer or type
    """
    query = db.query(Alert)

    # Apply filters
    if types:
        query = query.filter(Alert.alert_type.in_(types))
    if status:
        query = query.filter(Alert.status == status)
    if severity:
        query = query.filter(Alert.severity == severity)
    if customer_id:
        query = query.filter(Alert.user_id == customer_id)

    # Get type counts
    type_counts = db.query(
        Alert.alert_type,
        func.count(Alert.id)
    ).filter(Alert.status == "pending").group_by(Alert.alert_type).all()

    if group_by == "customer":
        # Group by customer
        return await get_customer_grouped_alerts(query, limit, offset)
    else:
        # Chronological list
        alerts = query.order_by(Alert.created_at.desc()).offset(offset).limit(limit).all()
        return {
            "items": alerts,
            "type_counts": dict(type_counts),
            "total": query.count()
        }

async def get_customer_grouped_alerts(query, limit: int, offset: int):
    """Group alerts by customer with risk context"""
    # Get distinct customers with pending alerts
    customer_ids = query.with_entities(Alert.user_id).distinct().offset(offset).limit(limit).all()

    groups = []
    for (customer_id,) in customer_ids:
        customer_alerts = query.filter(Alert.user_id == customer_id).all()
        risk_profile = await get_user_risk_profile(customer_id)

        groups.append({
            "customer_id": customer_id,
            "customer_name": risk_profile.get("name"),
            "risk_level": risk_profile.get("risk_level"),
            "risk_score": risk_profile.get("overall_risk_score"),
            "alerts": customer_alerts,
            "alert_count": len(customer_alerts)
        })

    return {"customer_groups": groups}
```

**Deliverables:**
- [ ] `/api/alerts/unified` endpoint with grouping
- [ ] Customer-grouped alert aggregation
- [ ] Type count statistics
- [ ] Efficient pagination
- [ ] Response caching (5s TTL)

---

#### Task 3.2: Customer Investigation API
**Priority:** Critical | **Effort:** High

```python
# Create: apps/api/src/api/customers.py

@router.get("/{customer_id}/investigation")
async def get_customer_investigation(
    customer_id: str,
    db: Session = Depends(get_db)
):
    """
    Comprehensive customer investigation data
    """
    # Parallel data fetching
    async with asyncio.TaskGroup() as tg:
        profile_task = tg.create_task(get_customer_profile(db, customer_id))
        timeline_task = tg.create_task(get_customer_timeline(db, customer_id))
        alerts_task = tg.create_task(get_customer_alerts(db, customer_id))
        transactions_task = tg.create_task(get_customer_transactions(db, customer_id))
        network_task = tg.create_task(get_customer_network_preview(db, customer_id))
        regulatory_task = tg.create_task(get_customer_regulatory_context(db, customer_id))

    return {
        "profile": profile_task.result(),
        "timeline": timeline_task.result(),
        "alerts": alerts_task.result(),
        "transactions": transactions_task.result(),
        "network_preview": network_task.result(),
        "regulatory_context": regulatory_task.result()
    }

async def get_customer_timeline(db: Session, customer_id: str) -> List[TimelineEvent]:
    """Build chronological timeline of customer events"""
    events = []

    # Risk score changes
    risk_changes = db.query(RiskScoreHistory).filter(
        RiskScoreHistory.user_id == customer_id
    ).order_by(RiskScoreHistory.created_at.desc()).limit(10).all()

    for change in risk_changes:
        events.append({
            "id": f"risk_{change.id}",
            "timestamp": change.created_at.isoformat(),
            "type": "risk_change",
            "title": f"Risk Score: {change.old_score} → {change.new_score}",
            "description": change.reason,
            "severity": get_risk_severity(change.new_score)
        })

    # Alerts
    alerts = db.query(Alert).filter(Alert.user_id == customer_id).all()
    for alert in alerts:
        events.append({
            "id": f"alert_{alert.id}",
            "timestamp": alert.created_at.isoformat(),
            "type": "alert",
            "title": f"Alert: {alert.alert_type}",
            "description": alert.description,
            "severity": alert.severity
        })

    # Cases
    cases = db.query(Case).filter(Case.related_users.contains([customer_id])).all()
    for case in cases:
        events.append({
            "id": f"case_{case.id}",
            "timestamp": case.created_at.isoformat(),
            "type": "case",
            "title": f"Case Opened: {case.title}",
            "description": case.description
        })

    # Sort by timestamp
    events.sort(key=lambda x: x["timestamp"], reverse=True)
    return events
```

**Deliverables:**
- [ ] `/api/customers/{id}/investigation` comprehensive endpoint
- [ ] Customer timeline aggregation
- [ ] Parallel data fetching with asyncio
- [ ] `/api/customers/{id}/analytics` for charts
- [ ] `/api/customers/{id}/ai-insights` for recommendations
- [ ] Response caching (30s TTL)

---

#### Task 3.3: Analytics Aggregation Service
**Priority:** High | **Effort:** Medium

```python
# Create: apps/api/src/services/analytics.py

class CustomerAnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    async def get_transaction_analytics(
        self,
        customer_id: str,
        date_from: datetime,
        date_to: datetime
    ) -> dict:
        """Aggregate transaction analytics for a customer"""

        # Volume by day
        volume_by_day = self.db.query(
            func.date_trunc('day', Transaction.created_at).label('date'),
            func.count(Transaction.id).label('count'),
            func.sum(Transaction.amount).label('total')
        ).filter(
            Transaction.user_id == customer_id,
            Transaction.created_at >= date_from,
            Transaction.created_at <= date_to
        ).group_by('date').order_by('date').all()

        # Amount distribution (buckets)
        amount_buckets = self._calculate_amount_buckets(customer_id, date_from, date_to)

        # Country breakdown
        country_breakdown = self.db.query(
            Transaction.country_code,
            func.count(Transaction.id).label('count'),
            func.sum(Transaction.amount).label('total')
        ).filter(
            Transaction.user_id == customer_id,
            Transaction.created_at >= date_from,
            Transaction.created_at <= date_to
        ).group_by(Transaction.country_code).all()

        # Detect anomalies
        anomalies = await self._detect_anomalies(customer_id, date_from, date_to)

        return {
            "volume_by_day": [{"date": r.date, "count": r.count, "total": float(r.total)} for r in volume_by_day],
            "amount_buckets": amount_buckets,
            "country_breakdown": [{"country": r.country_code, "count": r.count, "total": float(r.total)} for r in country_breakdown],
            "anomalies": anomalies
        }

    def _calculate_amount_buckets(self, customer_id: str, date_from: datetime, date_to: datetime) -> list:
        """Calculate amount distribution in buckets"""
        buckets = [
            (0, 100, "€0-100"),
            (100, 1000, "€100-1k"),
            (1000, 5000, "€1k-5k"),
            (5000, 10000, "€5k-10k"),
            (10000, float('inf'), "€10k+")
        ]

        result = []
        for min_amt, max_amt, label in buckets:
            count = self.db.query(func.count(Transaction.id)).filter(
                Transaction.user_id == customer_id,
                Transaction.created_at >= date_from,
                Transaction.created_at <= date_to,
                Transaction.amount >= min_amt,
                Transaction.amount < max_amt if max_amt != float('inf') else True
            ).scalar()
            result.append({"range": label, "count": count})

        return result
```

**Deliverables:**
- [ ] `CustomerAnalyticsService` class
- [ ] Transaction volume aggregation
- [ ] Amount bucket distribution
- [ ] Country breakdown
- [ ] Anomaly detection
- [ ] Caching layer with Redis

---

### Agent 3 Acceptance Criteria

| Criteria | Metric |
|----------|--------|
| API response time | < 200ms (P95) |
| Database query time | < 50ms (P95) |
| Cache hit rate | > 80% |
| Concurrent requests | 1000 req/s |
| Error rate | < 0.1% |

---

## Agent 4: AGENT-AI

### Mission
Build the Natural Language Rule Builder, rule backtesting engine, and ML model monitoring.

### Responsibilities
1. NLP to rule DSL conversion
2. Rule validation and conflict detection
3. Backtesting engine
4. Shadow mode infrastructure
5. ML model observatory

### Technical Skills Required
- Anthropic Claude API
- Python NLP
- Statistical analysis
- ML monitoring concepts

### Assigned Tasks

#### Task 4.1: NLP Rule Parser
**Priority:** Critical | **Effort:** High

```python
# Create: apps/api/src/ai/rule_parser.py

from anthropic import Anthropic

class NLPRuleParser:
    def __init__(self):
        self.client = Anthropic()
        self.system_prompt = """You are an expert AML rule builder. Convert natural language descriptions into structured rule DSL.

Output format (JSON):
{
  "name": "Rule name",
  "category": "structuring|velocity|unusual_behavior|sanctions|geographic",
  "severity": "critical|high|medium|low",
  "conditions": [
    {
      "field": "amount|user_id|country_code|transaction_type|...",
      "operator": "equals|not_equals|greater_than|less_than|in|not_in|contains",
      "value": "..."
    }
  ],
  "logic": "AND|OR",
  "aggregation": {
    "window": "1h|24h|7d|30d",
    "group_by": "user_id|account_id|...",
    "having": {
      "count": {"operator": "greater_than", "value": 5}
    }
  },
  "alert_config": {
    "severity": "high",
    "type": "STRUCTURING"
  }
}

Rules must be:
1. Specific and actionable
2. Based on AML best practices
3. Compliant with EU regulations (AMLD6)
"""

    async def parse_natural_language(self, description: str, language: str = "en") -> dict:
        """Convert natural language to rule DSL"""

        response = await self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=self.system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": f"Convert this rule description to DSL:\n\n{description}"
                }
            ]
        )

        # Extract JSON from response
        rule_json = self._extract_json(response.content[0].text)

        # Validate the rule
        validated_rule = await self._validate_rule(rule_json)

        return {
            "rule": validated_rule,
            "natural_language": description,
            "confidence": self._calculate_confidence(response),
            "suggestions": self._extract_suggestions(response)
        }

    async def _validate_rule(self, rule: dict) -> dict:
        """Validate rule structure and values"""
        errors = []

        # Check required fields
        required = ["name", "category", "severity", "conditions"]
        for field in required:
            if field not in rule:
                errors.append(f"Missing required field: {field}")

        # Validate conditions
        for i, condition in enumerate(rule.get("conditions", [])):
            if "field" not in condition:
                errors.append(f"Condition {i}: missing field")
            if "operator" not in condition:
                errors.append(f"Condition {i}: missing operator")
            if "value" not in condition:
                errors.append(f"Condition {i}: missing value")

        if errors:
            raise ValueError(f"Rule validation failed: {errors}")

        return rule
```

**Deliverables:**
- [ ] `NLPRuleParser` class with Claude integration
- [ ] Rule DSL validation
- [ ] Multi-language support (EN, FR, DE, ES)
- [ ] Confidence scoring
- [ ] Suggestion generation
- [ ] Error handling and fallback

---

#### Task 4.2: Rule Conflict Detection
**Priority:** High | **Effort:** Medium

```python
# Create: apps/api/src/ai/rule_validator.py

class RuleValidator:
    def __init__(self, db: Session):
        self.db = db

    async def detect_conflicts(self, new_rule: dict) -> dict:
        """Detect conflicts with existing rules"""
        existing_rules = self.db.query(MonitoringRule).filter(
            MonitoringRule.enabled == True
        ).all()

        conflicts = []
        overlaps = []

        for existing in existing_rules:
            # Check for exact duplicates
            if self._is_duplicate(new_rule, existing):
                conflicts.append({
                    "rule_id": existing.id,
                    "rule_name": existing.name,
                    "type": "duplicate",
                    "description": "This rule is identical to an existing rule"
                })
                continue

            # Check for subsumption (new rule catches subset of existing)
            if self._is_subsumed(new_rule, existing):
                overlaps.append({
                    "rule_id": existing.id,
                    "rule_name": existing.name,
                    "type": "subsumed",
                    "description": "New rule catches a subset of what existing rule catches"
                })

            # Check for overlap
            overlap_pct = self._calculate_overlap(new_rule, existing)
            if overlap_pct > 0.5:
                overlaps.append({
                    "rule_id": existing.id,
                    "rule_name": existing.name,
                    "type": "overlap",
                    "overlap_percentage": overlap_pct,
                    "description": f"{overlap_pct*100:.0f}% overlap with existing rule"
                })

        return {
            "conflicts": conflicts,
            "overlaps": overlaps,
            "is_valid": len(conflicts) == 0,
            "recommendations": self._generate_recommendations(conflicts, overlaps)
        }

    def _calculate_overlap(self, rule1: dict, rule2: MonitoringRule) -> float:
        """Calculate overlap percentage between two rules"""
        # Compare conditions
        conditions1 = set(self._normalize_conditions(rule1.get("conditions", [])))
        conditions2 = set(self._normalize_conditions(json.loads(rule2.conditions_json)))

        if not conditions1 or not conditions2:
            return 0.0

        intersection = conditions1 & conditions2
        union = conditions1 | conditions2

        return len(intersection) / len(union) if union else 0.0
```

**Deliverables:**
- [ ] `RuleValidator` class
- [ ] Duplicate detection
- [ ] Subsumption analysis
- [ ] Overlap percentage calculation
- [ ] Recommendation generation
- [ ] Integration with rule creation flow

---

#### Task 4.3: Backtesting Engine
**Priority:** High | **Effort:** High

```python
# Create: apps/api/src/services/backtest_engine.py

class BacktestEngine:
    def __init__(self, db: Session, rules_engine: RulesEngine):
        self.db = db
        self.rules_engine = rules_engine

    async def backtest_rule(
        self,
        rule: dict,
        days: int = 90,
        sample_size: int = 10000
    ) -> dict:
        """Run rule against historical transactions"""

        # Get historical transactions
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        transactions = self.db.query(Transaction).filter(
            Transaction.created_at >= start_date,
            Transaction.created_at <= end_date
        ).order_by(func.random()).limit(sample_size).all()

        # Evaluate rule against each transaction
        matches = []
        for tx in transactions:
            if self.rules_engine.evaluate_rule(rule, tx):
                matches.append({
                    "transaction_id": tx.transaction_id,
                    "amount": float(tx.amount),
                    "user_id": tx.user_id,
                    "timestamp": tx.created_at.isoformat(),
                    "country": tx.country_code
                })

        # Calculate statistics
        trigger_count = len(matches)
        trigger_rate = trigger_count / len(transactions) if transactions else 0

        # Estimate TP rate from similar rules
        estimated_tp_rate = await self._estimate_tp_rate(rule)

        # Calculate overlap with existing rules
        overlap_analysis = await self._analyze_overlap(rule, matches)

        return {
            "trigger_count": trigger_count,
            "trigger_rate": trigger_rate,
            "sample_size": len(transactions),
            "time_period_days": days,
            "estimated_tp_rate": estimated_tp_rate,
            "estimated_alerts_per_month": trigger_count * (30 / days),
            "sample_matches": matches[:10],  # First 10 matches
            "overlap_analysis": overlap_analysis,
            "by_day": self._group_by_day(matches),
            "by_severity": self._group_by_severity(matches)
        }

    async def _estimate_tp_rate(self, rule: dict) -> float:
        """Estimate TP rate based on similar rules' performance"""
        similar_rules = self.db.query(MonitoringRule).filter(
            MonitoringRule.category == rule.get("category"),
            MonitoringRule.true_positive_rate.isnot(None)
        ).all()

        if not similar_rules:
            return 0.7  # Default estimate

        # Weight by similarity
        weights = []
        rates = []
        for r in similar_rules:
            similarity = self._calculate_rule_similarity(rule, r)
            weights.append(similarity)
            rates.append(r.true_positive_rate)

        if sum(weights) == 0:
            return 0.7

        return sum(w * r for w, r in zip(weights, rates)) / sum(weights)
```

**Deliverables:**
- [ ] `BacktestEngine` class
- [ ] Historical transaction sampling
- [ ] Rule evaluation against samples
- [ ] TP rate estimation
- [ ] Overlap analysis
- [ ] Results grouping (by day, severity)
- [ ] Sample match extraction

---

#### Task 4.4: Shadow Mode Service
**Priority:** High | **Effort:** Medium

```python
# Create: apps/api/src/services/shadow_mode.py

class ShadowModeService:
    def __init__(self, db: Session):
        self.db = db

    async def evaluate_shadow_rules(self, transaction: Transaction):
        """Evaluate transaction against shadow rules (no alerts created)"""
        shadow_rules = self.db.query(MonitoringRule).filter(
            MonitoringRule.mode == "shadow",
            MonitoringRule.enabled == True
        ).all()

        for rule in shadow_rules:
            if self._evaluate_rule(rule, transaction):
                # Log shadow hit (don't create real alert)
                await self._log_shadow_hit(rule, transaction)

    async def _log_shadow_hit(self, rule: MonitoringRule, transaction: Transaction):
        """Log a shadow mode rule hit for analysis"""
        shadow_hit = ShadowAlert(
            rule_id=rule.id,
            transaction_id=transaction.id,
            user_id=transaction.user_id,
            would_trigger=True,
            trigger_data={
                "amount": float(transaction.amount),
                "country": transaction.country_code,
                "type": transaction.transaction_type
            }
        )
        self.db.add(shadow_hit)
        await self.db.commit()

    async def get_shadow_performance(self, rule_id: str, days: int = 30) -> dict:
        """Get shadow rule performance statistics"""
        since = datetime.utcnow() - timedelta(days=days)

        hits = self.db.query(ShadowAlert).filter(
            ShadowAlert.rule_id == rule_id,
            ShadowAlert.created_at >= since
        ).all()

        # Group by day
        by_day = {}
        for hit in hits:
            day = hit.created_at.date().isoformat()
            by_day[day] = by_day.get(day, 0) + 1

        return {
            "total_hits": len(hits),
            "hits_per_day": len(hits) / days,
            "by_day": by_day,
            "unique_users": len(set(h.user_id for h in hits)),
            "sample_hits": [h.to_dict() for h in hits[:10]]
        }

    async def promote_to_production(self, rule_id: str) -> MonitoringRule:
        """Promote a shadow rule to production"""
        rule = self.db.query(MonitoringRule).filter(
            MonitoringRule.id == rule_id
        ).first()

        if rule.mode != "shadow":
            raise ValueError("Rule is not in shadow mode")

        rule.mode = "production"
        rule.promoted_at = datetime.utcnow()
        await self.db.commit()

        return rule
```

**Deliverables:**
- [ ] `ShadowModeService` class
- [ ] `ShadowAlert` model
- [ ] Shadow rule evaluation
- [ ] Shadow hit logging
- [ ] Performance statistics
- [ ] Promotion workflow
- [ ] API endpoints for shadow mode

---

#### Task 4.5: ML Model Observatory
**Priority:** Medium-High | **Effort:** High

```python
# Create: apps/api/src/ml/model_registry.py

class ModelRegistry:
    def __init__(self, db: Session):
        self.db = db

    async def register_model(
        self,
        name: str,
        version: str,
        model_type: str,
        metadata: dict
    ) -> MLModel:
        """Register a new model version"""
        model = MLModel(
            name=name,
            version=version,
            model_type=model_type,
            metadata=metadata,
            status="active"
        )
        self.db.add(model)
        await self.db.commit()
        return model

    async def log_prediction(
        self,
        model_id: str,
        input_data: dict,
        prediction: float,
        actual: Optional[float] = None
    ):
        """Log a model prediction for monitoring"""
        prediction_log = ModelPrediction(
            model_id=model_id,
            input_features=input_data,
            predicted_value=prediction,
            actual_value=actual
        )
        self.db.add(prediction_log)
        await self.db.commit()

    async def get_model_performance(
        self,
        model_id: str,
        days: int = 7
    ) -> dict:
        """Calculate model performance metrics"""
        since = datetime.utcnow() - timedelta(days=days)

        predictions = self.db.query(ModelPrediction).filter(
            ModelPrediction.model_id == model_id,
            ModelPrediction.created_at >= since,
            ModelPrediction.actual_value.isnot(None)
        ).all()

        if not predictions:
            return {"status": "insufficient_data"}

        # Calculate metrics
        y_true = [p.actual_value for p in predictions]
        y_pred = [p.predicted_value for p in predictions]

        return {
            "auc_roc": self._calculate_auc(y_true, y_pred),
            "precision": self._calculate_precision(y_true, y_pred),
            "recall": self._calculate_recall(y_true, y_pred),
            "f1": self._calculate_f1(y_true, y_pred),
            "false_positive_rate": self._calculate_fpr(y_true, y_pred),
            "sample_size": len(predictions),
            "time_period_days": days
        }


# Create: apps/api/src/ml/drift_detection.py

class DriftDetector:
    def __init__(self, db: Session):
        self.db = db

    async def detect_drift(
        self,
        model_id: str,
        reference_days: int = 30,
        comparison_days: int = 7
    ) -> dict:
        """Detect feature and prediction drift"""
        now = datetime.utcnow()
        reference_start = now - timedelta(days=reference_days + comparison_days)
        reference_end = now - timedelta(days=comparison_days)
        comparison_start = reference_end
        comparison_end = now

        # Get predictions for both periods
        reference_preds = await self._get_predictions(model_id, reference_start, reference_end)
        comparison_preds = await self._get_predictions(model_id, comparison_start, comparison_end)

        # Calculate PSI for prediction distribution
        prediction_drift = self._calculate_psi(
            [p.predicted_value for p in reference_preds],
            [p.predicted_value for p in comparison_preds]
        )

        # Calculate feature drift
        feature_drift = {}
        features = self._extract_feature_names(reference_preds[0].input_features if reference_preds else {})

        for feature in features:
            ref_values = [p.input_features.get(feature) for p in reference_preds if p.input_features.get(feature) is not None]
            comp_values = [p.input_features.get(feature) for p in comparison_preds if p.input_features.get(feature) is not None]

            if ref_values and comp_values:
                drift = self._calculate_psi(ref_values, comp_values)
                if drift > 0.1:  # Significant drift threshold
                    feature_drift[feature] = {
                        "psi": drift,
                        "status": "drift_detected" if drift > 0.2 else "warning"
                    }

        # Overall status
        status = "healthy"
        if prediction_drift > 0.2 or any(f["psi"] > 0.2 for f in feature_drift.values()):
            status = "drift_detected"
        elif prediction_drift > 0.1 or any(f["psi"] > 0.1 for f in feature_drift.values()):
            status = "warning"

        return {
            "status": status,
            "prediction_drift": {
                "psi": prediction_drift,
                "threshold": 0.2
            },
            "feature_drift": feature_drift,
            "reference_period": f"{reference_start.date()} to {reference_end.date()}",
            "comparison_period": f"{comparison_start.date()} to {comparison_end.date()}",
            "recommendations": self._generate_recommendations(status, prediction_drift, feature_drift)
        }

    def _calculate_psi(self, expected: list, actual: list, bins: int = 10) -> float:
        """Calculate Population Stability Index"""
        # Bin the distributions
        min_val = min(min(expected), min(actual))
        max_val = max(max(expected), max(actual))
        bin_edges = np.linspace(min_val, max_val, bins + 1)

        expected_counts, _ = np.histogram(expected, bins=bin_edges)
        actual_counts, _ = np.histogram(actual, bins=bin_edges)

        # Normalize
        expected_pct = expected_counts / len(expected)
        actual_pct = actual_counts / len(actual)

        # Replace zeros
        expected_pct = np.where(expected_pct == 0, 0.0001, expected_pct)
        actual_pct = np.where(actual_pct == 0, 0.0001, actual_pct)

        # Calculate PSI
        psi = np.sum((actual_pct - expected_pct) * np.log(actual_pct / expected_pct))
        return float(psi)
```

**Deliverables:**
- [ ] `ModelRegistry` for model versioning
- [ ] `ModelPrediction` logging
- [ ] Performance metric calculation (AUC, precision, recall, F1)
- [ ] `DriftDetector` with PSI calculation
- [ ] Feature drift analysis
- [ ] Automated drift alerting
- [ ] API endpoints for model observatory

---

### Agent 4 Acceptance Criteria

| Criteria | Metric |
|----------|--------|
| NLP rule accuracy | > 85% |
| Rule parsing time | < 3 seconds |
| Backtest execution (90d) | < 30 seconds |
| Drift detection accuracy | > 90% |
| Shadow mode overhead | < 5% latency increase |

---

## Agent 5: AGENT-REPORTS

### Mission
Build comprehensive reporting suite including PDF generation, Excel exports, and scheduled reports.

### Responsibilities
1. PDF report generation
2. Excel/CSV exports
3. Report templates
4. Scheduled report execution
5. Report delivery (email, S3)

### Technical Skills Required
- WeasyPrint/ReportLab
- openpyxl
- Jinja2 templates
- Celery
- AWS SES/S3

### Assigned Tasks

#### Task 5.1: PDF Report Generator
**Priority:** High | **Effort:** High

```python
# Create: apps/api/src/reporting/pdf_generator.py

from weasyprint import HTML, CSS
from jinja2 import Environment, FileSystemLoader

class PDFReportGenerator:
    def __init__(self):
        self.template_env = Environment(
            loader=FileSystemLoader('apps/api/src/reporting/templates')
        )
        self.base_css = CSS(filename='apps/api/src/reporting/templates/base.css')

    async def generate_sar_summary(
        self,
        date_from: datetime,
        date_to: datetime,
        data: dict
    ) -> bytes:
        """Generate SAR Summary PDF report"""
        template = self.template_env.get_template('sar_summary.html')

        html_content = template.render(
            report_title="SAR Summary Report",
            date_from=date_from.strftime("%B %d, %Y"),
            date_to=date_to.strftime("%B %d, %Y"),
            generated_at=datetime.utcnow().strftime("%B %d, %Y %H:%M UTC"),
            **data
        )

        pdf = HTML(string=html_content).write_pdf(stylesheets=[self.base_css])
        return pdf

    async def generate_executive_summary(
        self,
        date_from: datetime,
        date_to: datetime,
        data: dict
    ) -> bytes:
        """Generate Executive Summary PDF"""
        template = self.template_env.get_template('executive_summary.html')

        # Generate charts as base64 images
        charts = {
            "alert_trend": await self._generate_chart_image(data["alert_trend"]),
            "risk_distribution": await self._generate_chart_image(data["risk_distribution"]),
            "case_status": await self._generate_chart_image(data["case_status"])
        }

        html_content = template.render(
            report_title="Executive Summary",
            date_from=date_from.strftime("%B %d, %Y"),
            date_to=date_to.strftime("%B %d, %Y"),
            charts=charts,
            **data
        )

        pdf = HTML(string=html_content).write_pdf(stylesheets=[self.base_css])
        return pdf

    async def _generate_chart_image(self, chart_data: dict) -> str:
        """Generate chart as base64 image using matplotlib"""
        import matplotlib.pyplot as plt
        import io
        import base64

        fig, ax = plt.subplots(figsize=(8, 4))
        # ... chart generation based on chart_data type

        buffer = io.BytesIO()
        fig.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        plt.close(fig)

        return base64.b64encode(buffer.getvalue()).decode()
```

**Deliverables:**
- [ ] `PDFReportGenerator` class
- [ ] SAR Summary template
- [ ] Executive Summary template
- [ ] Audit Trail template
- [ ] Risk Assessment template
- [ ] Chart embedding (matplotlib)
- [ ] CSS styling for reports

**Template Files to Create:**
```
apps/api/src/reporting/templates/
├── base.css
├── sar_summary.html
├── executive_summary.html
├── audit_trail.html
├── risk_assessment.html
└── components/
    ├── header.html
    ├── footer.html
    └── table.html
```

---

#### Task 5.2: Excel Report Generator
**Priority:** High | **Effort:** Medium

```python
# Create: apps/api/src/reporting/excel_generator.py

from openpyxl import Workbook
from openpyxl.styles import Font, Fill, Border, Alignment
from openpyxl.chart import BarChart, PieChart, LineChart

class ExcelReportGenerator:
    def __init__(self):
        self.header_style = {
            "font": Font(bold=True, color="FFFFFF"),
            "fill": PatternFill(start_color="1F4E79", fill_type="solid"),
            "alignment": Alignment(horizontal="center")
        }

    async def generate_alert_report(
        self,
        alerts: List[Alert],
        include_charts: bool = True
    ) -> bytes:
        """Generate Alert Report Excel"""
        wb = Workbook()

        # Summary sheet
        summary_ws = wb.active
        summary_ws.title = "Summary"
        await self._add_summary_sheet(summary_ws, alerts)

        # Detail sheet
        detail_ws = wb.create_sheet("Alert Details")
        await self._add_alert_details(detail_ws, alerts)

        # Charts sheet
        if include_charts:
            charts_ws = wb.create_sheet("Charts")
            await self._add_charts(charts_ws, alerts)

        # Save to bytes
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return buffer.getvalue()

    async def _add_summary_sheet(self, ws, alerts: List[Alert]):
        """Add summary statistics"""
        ws["A1"] = "Alert Summary Report"
        ws["A1"].font = Font(size=16, bold=True)

        # Statistics
        stats = [
            ("Total Alerts", len(alerts)),
            ("Critical", sum(1 for a in alerts if a.severity == "critical")),
            ("High", sum(1 for a in alerts if a.severity == "high")),
            ("Medium", sum(1 for a in alerts if a.severity == "medium")),
            ("Low", sum(1 for a in alerts if a.severity == "low")),
            ("Resolved", sum(1 for a in alerts if a.status == "resolved")),
            ("Pending", sum(1 for a in alerts if a.status == "pending")),
        ]

        for i, (label, value) in enumerate(stats, start=3):
            ws[f"A{i}"] = label
            ws[f"B{i}"] = value

    async def _add_alert_details(self, ws, alerts: List[Alert]):
        """Add detailed alert list"""
        headers = ["Alert ID", "Type", "Severity", "Status", "User ID", "Created", "Amount"]

        for col, header in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = self.header_style["font"]
            cell.fill = self.header_style["fill"]

        for row, alert in enumerate(alerts, start=2):
            ws.cell(row=row, column=1, value=alert.alert_id)
            ws.cell(row=row, column=2, value=alert.alert_type)
            ws.cell(row=row, column=3, value=alert.severity)
            ws.cell(row=row, column=4, value=alert.status)
            ws.cell(row=row, column=5, value=alert.user_id)
            ws.cell(row=row, column=6, value=alert.created_at.isoformat())
            ws.cell(row=row, column=7, value=float(alert.amount) if alert.amount else None)
```

**Deliverables:**
- [ ] `ExcelReportGenerator` class
- [ ] Alert report with multiple sheets
- [ ] Transaction report
- [ ] Case report
- [ ] Chart embedding (openpyxl charts)
- [ ] Styling and formatting
- [ ] CSV export option

---

#### Task 5.3: Report Scheduler
**Priority:** Medium | **Effort:** Medium

```python
# Create: apps/api/src/reporting/scheduler.py

from celery import Celery
from celery.schedules import crontab

class ReportScheduler:
    def __init__(self, db: Session, celery: Celery):
        self.db = db
        self.celery = celery

    async def create_schedule(
        self,
        report_type: str,
        frequency: str,
        recipients: List[str],
        parameters: dict
    ) -> ScheduledReport:
        """Create a new scheduled report"""
        schedule = ScheduledReport(
            report_type=report_type,
            frequency=frequency,  # daily, weekly, monthly
            recipients=recipients,
            parameters=parameters,
            next_run=self._calculate_next_run(frequency),
            enabled=True
        )
        self.db.add(schedule)
        await self.db.commit()

        # Register with Celery beat
        await self._register_celery_task(schedule)

        return schedule

    def _calculate_next_run(self, frequency: str) -> datetime:
        """Calculate next run time based on frequency"""
        now = datetime.utcnow()

        if frequency == "daily":
            # Next day at 6:00 AM
            next_run = now.replace(hour=6, minute=0, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)
        elif frequency == "weekly":
            # Next Monday at 6:00 AM
            days_until_monday = (7 - now.weekday()) % 7 or 7
            next_run = now + timedelta(days=days_until_monday)
            next_run = next_run.replace(hour=6, minute=0, second=0, microsecond=0)
        elif frequency == "monthly":
            # First of next month at 6:00 AM
            if now.month == 12:
                next_run = now.replace(year=now.year + 1, month=1, day=1, hour=6, minute=0, second=0, microsecond=0)
            else:
                next_run = now.replace(month=now.month + 1, day=1, hour=6, minute=0, second=0, microsecond=0)

        return next_run


# Celery task
@celery.task
async def execute_scheduled_report(schedule_id: str):
    """Execute a scheduled report"""
    db = get_db()
    schedule = db.query(ScheduledReport).filter(ScheduledReport.id == schedule_id).first()

    if not schedule or not schedule.enabled:
        return

    # Generate report
    generator = get_report_generator(schedule.report_type)
    report_bytes = await generator.generate(**schedule.parameters)

    # Deliver report
    delivery = ReportDelivery(db)
    await delivery.send_email(
        recipients=schedule.recipients,
        subject=f"{schedule.report_type} Report - {datetime.utcnow().strftime('%Y-%m-%d')}",
        attachment=report_bytes,
        filename=f"{schedule.report_type}_{datetime.utcnow().strftime('%Y%m%d')}.pdf"
    )

    # Update schedule
    schedule.last_run = datetime.utcnow()
    schedule.next_run = scheduler._calculate_next_run(schedule.frequency)
    schedule.run_count += 1
    await db.commit()
```

**Deliverables:**
- [ ] `ReportScheduler` class
- [ ] `ScheduledReport` model
- [ ] Celery beat integration
- [ ] Frequency options (daily, weekly, monthly, custom cron)
- [ ] Email delivery
- [ ] S3 storage option
- [ ] Run history tracking
- [ ] API endpoints for schedule CRUD

---

### Agent 5 Acceptance Criteria

| Criteria | Metric |
|----------|--------|
| PDF generation time | < 5 seconds |
| Excel generation time | < 3 seconds |
| Report size limit | 10MB |
| Schedule reliability | 99.9% |
| Email delivery rate | > 99% |

---

## Agent 6: AGENT-COMPLIANCE

### Mission
Build SAR lifecycle management and comprehensive audit trail system.

### Responsibilities
1. SAR workflow state machine
2. Filing acknowledgment tracking
3. SAR lifecycle visualization
4. Audit trail infrastructure
5. Compliance calendar

### Technical Skills Required
- State machine design
- Workflow automation
- Database design
- FastAPI
- React visualization

### Assigned Tasks

#### Task 6.1: SAR Workflow State Machine
**Priority:** Critical | **Effort:** Medium

```python
# Create: apps/api/src/compliance/sar_workflow.py

from enum import Enum
from transitions import Machine

class SARStatus(str, Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    FILED = "filed"
    ACKNOWLEDGED = "acknowledged"
    REJECTED = "rejected"
    AMENDED = "amended"
    CLOSED = "closed"

class SARWorkflow:
    states = [s.value for s in SARStatus]

    transitions = [
        # Draft → Review
        {"trigger": "submit_for_review", "source": "draft", "dest": "pending_review"},

        # Review → Approved/Draft
        {"trigger": "approve", "source": "pending_review", "dest": "approved"},
        {"trigger": "request_changes", "source": "pending_review", "dest": "draft"},

        # Approved → Filed
        {"trigger": "file", "source": "approved", "dest": "filed"},

        # Filed → Acknowledged/Rejected
        {"trigger": "acknowledge", "source": "filed", "dest": "acknowledged"},
        {"trigger": "reject", "source": "filed", "dest": "rejected"},

        # Rejected → Amended
        {"trigger": "amend", "source": "rejected", "dest": "amended"},
        {"trigger": "refile", "source": "amended", "dest": "filed"},

        # Acknowledged → Closed
        {"trigger": "close", "source": "acknowledged", "dest": "closed"},
    ]

    def __init__(self, sar: SAR):
        self.sar = sar
        self.machine = Machine(
            model=self,
            states=self.states,
            transitions=self.transitions,
            initial=sar.status,
            after_state_change=self._on_state_change
        )

    async def _on_state_change(self):
        """Called after any state transition"""
        self.sar.status = self.state
        self.sar.status_history.append({
            "status": self.state,
            "timestamp": datetime.utcnow().isoformat(),
            "user": get_current_user()
        })
        await self._notify_stakeholders()

    async def _notify_stakeholders(self):
        """Send notifications on state change"""
        # Implement notification logic
        pass
```

**Deliverables:**
- [ ] `SARWorkflow` state machine
- [ ] State transition validation
- [ ] Status history tracking
- [ ] Notification triggers
- [ ] API endpoints for transitions
- [ ] Permission checks per transition

---

#### Task 6.2: Filing Acknowledgment Tracker
**Priority:** High | **Effort:** Medium

```python
# Create: apps/api/src/compliance/filing_tracker.py

class FilingTracker:
    def __init__(self, db: Session):
        self.db = db

    async def track_filing(
        self,
        sar_id: str,
        filing_response: dict
    ) -> FilingRecord:
        """Track a SAR filing response"""
        record = FilingRecord(
            sar_id=sar_id,
            filing_reference=filing_response.get("reference"),
            filing_status=filing_response.get("status"),  # accepted, warning, rejected
            filed_at=datetime.utcnow(),
            response_data=filing_response,
            warnings=filing_response.get("warnings", []),
            errors=filing_response.get("errors", [])
        )
        self.db.add(record)
        await self.db.commit()

        # Update SAR status
        sar = self.db.query(SAR).filter(SAR.id == sar_id).first()
        workflow = SARWorkflow(sar)

        if filing_response.get("status") == "accepted":
            await workflow.acknowledge()
        elif filing_response.get("status") == "rejected":
            await workflow.reject()

        return record

    async def get_filing_timeline(self, sar_id: str) -> List[dict]:
        """Get complete filing timeline for a SAR"""
        records = self.db.query(FilingRecord).filter(
            FilingRecord.sar_id == sar_id
        ).order_by(FilingRecord.created_at).all()

        timeline = []
        for record in records:
            timeline.append({
                "timestamp": record.created_at.isoformat(),
                "event": "filing_submitted" if not record.response_received_at else "response_received",
                "status": record.filing_status,
                "reference": record.filing_reference,
                "details": record.response_data
            })

        return timeline
```

**Deliverables:**
- [ ] `FilingTracker` class
- [ ] `FilingRecord` model
- [ ] FinCEN response parsing
- [ ] goAML response parsing
- [ ] Filing timeline aggregation
- [ ] Resubmission workflow
- [ ] Filing statistics

---

#### Task 6.3: Audit Trail Infrastructure
**Priority:** High | **Effort:** High

```python
# Create: apps/api/src/audit/models.py

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID, primary_key=True, default=uuid4)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    user_id = Column(String, index=True)
    user_email = Column(String)
    ip_address = Column(String)
    action = Column(String, index=True)  # create, update, delete, view, export
    entity_type = Column(String, index=True)  # alert, case, sar, rule, customer
    entity_id = Column(String, index=True)
    changes = Column(JSON)  # {field: {old: x, new: y}}
    metadata = Column(JSON)


# Create: apps/api/src/audit/middleware.py

class AuditMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Extract request info
            request = Request(scope, receive)
            user = await get_current_user(request)

            # Capture response
            response = await self.app(scope, receive, send)

            # Log auditable actions
            if self._is_auditable(request.method, request.url.path):
                await self._log_audit(request, user, response)
        else:
            await self.app(scope, receive, send)

    def _is_auditable(self, method: str, path: str) -> bool:
        """Determine if request should be audited"""
        # Audit all mutations
        if method in ["POST", "PUT", "PATCH", "DELETE"]:
            return True
        # Audit sensitive views
        if method == "GET" and any(p in path for p in ["/customers/", "/sar/", "/export"]):
            return True
        return False

    async def _log_audit(self, request: Request, user: User, response):
        """Create audit log entry"""
        # Extract changes from request body
        body = await request.json() if request.method != "GET" else None

        log = AuditLog(
            user_id=user.id if user else None,
            user_email=user.email if user else None,
            ip_address=request.client.host,
            action=self._get_action(request.method),
            entity_type=self._extract_entity_type(request.url.path),
            entity_id=self._extract_entity_id(request.url.path),
            changes=body,
            metadata={
                "path": request.url.path,
                "method": request.method,
                "status_code": response.status_code
            }
        )

        db = get_db()
        db.add(log)
        await db.commit()
```

**Deliverables:**
- [ ] `AuditLog` model with indexes
- [ ] `AuditMiddleware` for automatic logging
- [ ] Change diff detection
- [ ] Search/filter API
- [ ] Export functionality
- [ ] Retention policy
- [ ] API endpoints

---

### Agent 6 Acceptance Criteria

| Criteria | Metric |
|----------|--------|
| SAR workflow transitions | 100% valid |
| Audit log completeness | 100% mutations logged |
| Audit query performance | < 500ms |
| Filing tracking accuracy | 100% |
| State machine coverage | All paths tested |

---

## Agent 7: AGENT-TESTING

### Mission
Ensure code quality through comprehensive testing.

### Responsibilities
1. Unit tests for all services
2. Integration tests for APIs
3. E2E tests for critical flows
4. Performance testing
5. Security testing

### Assigned Tasks

- [ ] Unit tests for WebSocket manager
- [ ] Unit tests for rule parser
- [ ] Unit tests for backtest engine
- [ ] Integration tests for unified alerts API
- [ ] Integration tests for customer investigation API
- [ ] E2E tests for SAR workflow
- [ ] Performance tests for real-time metrics
- [ ] Security tests for authentication

---

## Agent 8: AGENT-INFRA

### Mission
Infrastructure setup and optimization.

### Responsibilities
1. Docker configuration
2. Redis setup
3. Celery configuration
4. Performance optimization
5. Monitoring setup

### Assigned Tasks

- [ ] Docker Compose for development
- [ ] Redis cluster configuration
- [ ] Celery worker setup
- [ ] Database indexing optimization
- [ ] CDN configuration
- [ ] Monitoring dashboards (Datadog/Prometheus)

---

## Agent 9: AGENT-ENTERPRISE-FE

### Mission
Deliver Phase 4 enterprise polish on the frontend: mobile responsiveness, white-label theming, currency normalization UI, sanctions match explanations, and large-list performance.

### Responsibilities
1. Mobile navigation and touch interactions
2. Responsive charts and layouts
3. Theming/branding system (CSS variables)
4. Currency normalization display + tooltips
5. Sanctions match explanation UI
6. Frontend performance (lazy loading, virtualization)

### Assigned Tasks

- [ ] Implement mobile navigation (hamburger + quick actions)
- [ ] Optimize charts and tables for small screens
- [ ] Add mobile-specific alert actions and touch gestures
- [ ] Build CSS-variable theming with org-level overrides
- [ ] Create branding settings UI (logo/colors) + preview
- [ ] Normalize currency display across alerts/transactions
- [ ] Add currency comparison tooltips (base vs original)
- [ ] Build sanctions match explanation UI
- [ ] Add virtual scrolling + lazy loading for large lists

---

## Agent 10: AGENT-ENTERPRISE-BE

### Mission
Deliver Phase 4 enterprise backend capabilities: currency normalization, enhanced sanctions screening, performance optimization, and white-label/multi-tenant support.

### Responsibilities
1. Currency conversion service (ECB rates) + base currency settings
2. Sanctions screening enhancements (SWIFT/BIC, watchlists, updates)
3. Performance optimization (query tuning, caching, WebSocket batching)
4. White-label backend (branding config API, custom domains, tenant isolation)

### Assigned Tasks

- [ ] Create currency conversion service + scheduled ECB rate sync
- [ ] Add organization base currency settings + API
- [ ] Normalize amounts in API responses
- [ ] Implement SWIFT/BIC screening + watchlist expansion
- [ ] Build watchlist update pipeline + real-time notifications
- [ ] Add match explanation data to sanctions endpoints
- [ ] Optimize high-traffic queries and add indexes as needed
- [ ] Implement Redis caching for heavy endpoints
- [ ] Batch WebSocket events with backpressure controls
- [ ] Enforce tenant isolation on all queries
- [ ] Implement custom domain support + branding config API

---

## Coordination Protocol

### Daily Standups
Each agent reports:
1. Tasks completed yesterday
2. Tasks planned for today
3. Blockers

### Integration Points

| Integration | Agents Involved | Coordination Needed |
|-------------|-----------------|---------------------|
| WebSocket → Frontend | AGENT-REALTIME, AGENT-FRONTEND | Event schema agreement |
| API → Frontend | AGENT-BACKEND, AGENT-FRONTEND | API contract definition |
| AI → Backend | AGENT-AI, AGENT-BACKEND | Service interfaces |
| Reports → Backend | AGENT-REPORTS, AGENT-BACKEND | Data access patterns |
| Compliance → Backend | AGENT-COMPLIANCE, AGENT-BACKEND | Model changes |
| Enterprise UI → Backend | AGENT-ENTERPRISE-FE, AGENT-ENTERPRISE-BE | Currency, branding, sanctions API contracts |
| White-label → Infra | AGENT-ENTERPRISE-BE, AGENT-INFRA | Custom domains + tenant isolation |
| Performance → Realtime | AGENT-ENTERPRISE-BE, AGENT-REALTIME | WebSocket batching + latency budgets |


### Code Review Process
1. Agent completes task
2. Creates PR with task reference
3. Another agent reviews
4. Merge after approval

### Communication Channels
- **#yufeed-dev** - General development discussion
- **#yufeed-blockers** - Immediate blockers
- **#yufeed-integration** - Cross-agent coordination

---

## Getting Started

### For Each Agent

1. **Read this document thoroughly**
2. **Understand your assigned tasks**
3. **Check dependencies on other agents**
4. **Start with highest priority tasks**
5. **Report progress daily**

### Task Execution Order

```
Week 1-4: AGENT-REALTIME + AGENT-BACKEND + AGENT-FRONTEND (Phase 1)
Week 5-8: AGENT-AI (Phase 2) + ongoing integration
Week 9-12: AGENT-REPORTS + AGENT-COMPLIANCE (Phase 3)
Week 13-16: AGENT-ENTERPRISE-BE + AGENT-ENTERPRISE-FE (Phase 4)
Ongoing: AGENT-TESTING + AGENT-INFRA (all phases)
```


---

*Document Version: 1.1*
*Last Updated: January 22, 2026*
