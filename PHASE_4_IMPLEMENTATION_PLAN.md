# Phase 4: Implementation Plan - Detailed Task Breakdown

**Project:** YuFeed Platform Enhancement
**Version:** 2.0
**Date:** January 22, 2026
**Status:** Planning Phase
**Total Duration:** 8 weeks

---

## Overview

This document provides a comprehensive, task-level implementation plan for Phase 4 enhancements. Each phase includes detailed tasks, acceptance criteria, dependencies, and estimated effort.

**Phase Structure:**
- **Phase 4A:** Foundation (Testing, Monitoring, Caching) - Weeks 1-2
- **Phase 4B:** Intelligence (ML, Triage, Real-time) - Weeks 3-4
- **Phase 4C:** Scale (Multi-tenancy, GraphQL, Graph) - Weeks 5-6
- **Phase 4D:** Crypto Native (Blockchain, Reporting, API) - Weeks 7-8

---

## Phase 4A: Foundation (Weeks 1-2)

**Goal:** Establish production-ready foundation with testing, monitoring, and performance optimization.

### 1. Comprehensive Testing Suite ✅

**Duration:** 4-5 days
**Priority:** P0 (Critical)

#### Task 1.1: Unit Test Infrastructure Setup
**Effort:** 0.5 days
**Owner:** Backend Team

**Subtasks:**
- [ ] Configure pytest with coverage reporting
- [ ] Set up pytest fixtures for database, Redis, OpenSearch
- [ ] Create mock factories for common models (Transaction, Alert, User)
- [ ] Configure pytest-asyncio for async tests
- [ ] Set up coverage thresholds (target: 80%)

**Acceptance Criteria:**
- ✅ pytest runs with `pytest tests/`
- ✅ Coverage report generated with `pytest --cov`
- ✅ Fixtures available for DB sessions, API clients
- ✅ Mock factories work for all major models

**Files to Create:**
```
apps/api/tests/
├── conftest.py                 # pytest configuration & fixtures
├── factories.py                # Model factories
└── mocks.py                    # Mock services
```

#### Task 1.2: API Endpoint Unit Tests
**Effort:** 2 days
**Owner:** Backend Team
**Dependencies:** Task 1.1

**Subtasks:**
- [ ] Test all auth endpoints (login, register, refresh, logout)
- [ ] Test transaction ingestion endpoints
- [ ] Test alert CRUD operations
- [ ] Test case management endpoints
- [ ] Test decisioning endpoints
- [ ] Test audit logging endpoints
- [ ] Test rule management endpoints
- [ ] Mock external services (Anthropic API, sanctions APIs)

**Acceptance Criteria:**
- ✅ 80%+ coverage on all API routers
- ✅ Tests for happy paths and error cases
- ✅ Authentication/authorization tested
- ✅ All tests pass in CI/CD

**Files to Create:**
```
apps/api/tests/api/
├── test_auth.py
├── test_transactions.py
├── test_alerts.py
├── test_cases.py
├── test_decisioning.py
├── test_audit.py
└── test_monitoring_rules.py
```

**Example Test:**
```python
# tests/api/test_auth.py
def test_login_success(client, db_session):
    # Create test user
    user = UserFactory.create(email="test@example.com")

    # Attempt login
    response = client.post("/api/auth/login", json={
        "email": "test@example.com",
        "password": "password123"
    })

    # Assertions
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert "refresh_token" in response.json()

def test_login_invalid_credentials(client):
    response = client.post("/api/auth/login", json={
        "email": "fake@example.com",
        "password": "wrong"
    })
    assert response.status_code == 401
```

#### Task 1.3: Service Layer Unit Tests
**Effort:** 1 day
**Owner:** Backend Team
**Dependencies:** Task 1.1

**Subtasks:**
- [ ] Test RulesEngine.evaluate_transaction()
- [ ] Test RiskScoringService.calculate_risk()
- [ ] Test FeatureStore.compute_features()
- [ ] Test event_normalizer functions
- [ ] Test EventBus pub/sub
- [ ] Test plugin registry

**Acceptance Criteria:**
- ✅ 85%+ coverage on services layer
- ✅ Edge cases tested (null values, invalid inputs)
- ✅ Performance benchmarks for critical paths

**Files to Create:**
```
apps/api/tests/services/
├── test_rules_engine.py
├── test_risk_scoring.py
├── test_feature_store.py
├── test_event_normalizer.py
└── test_event_bus.py
```

#### Task 1.4: Integration Tests
**Effort:** 1.5 days
**Owner:** Backend Team
**Dependencies:** Task 1.2, Task 1.3

**Subtasks:**
- [ ] Test end-to-end transaction ingestion flow
- [ ] Test alert creation and triage workflow
- [ ] Test case creation from alert
- [ ] Test decisioning event → decision flow
- [ ] Test audit logging capture
- [ ] Test rule evaluation with database

**Acceptance Criteria:**
- ✅ Complete user journeys tested
- ✅ Database transactions properly tested
- ✅ External service mocks validated

**Files to Create:**
```
apps/api/tests/integration/
├── test_transaction_flow.py
├── test_alert_workflow.py
├── test_case_workflow.py
└── test_decisioning_flow.py
```

#### Task 1.5: Frontend Testing Setup
**Effort:** 0.5 days
**Owner:** Frontend Team

**Subtasks:**
- [ ] Set up Vitest for component testing
- [ ] Configure React Testing Library
- [ ] Set up Playwright for E2E tests
- [ ] Create test utilities and helpers

**Acceptance Criteria:**
- ✅ `npm run test` runs unit tests
- ✅ `npm run test:e2e` runs E2E tests
- ✅ Test utilities available

**Files to Create:**
```
apps/web/tests/
├── setup.ts
├── utils.tsx
└── __mocks__/
```

---

### 2. Monitoring & Observability ✅

**Duration:** 4-5 days
**Priority:** P0 (Critical)

#### Task 2.1: Prometheus Metrics Integration
**Effort:** 1 day
**Owner:** Backend Team

**Subtasks:**
- [ ] Install prometheus_client
- [ ] Create metrics middleware
- [ ] Add counter metrics (requests, errors)
- [ ] Add histogram metrics (latency, duration)
- [ ] Add gauge metrics (connections, queue size)
- [ ] Expose /metrics endpoint

**Acceptance Criteria:**
- ✅ Metrics accessible at /metrics
- ✅ Request latency tracked (p50, p95, p99)
- ✅ Error rates tracked by endpoint
- ✅ Custom business metrics (alerts/min, decisions/min)

**Files to Create:**
```
apps/api/src/monitoring/
├── __init__.py
├── metrics.py              # Metric definitions
└── middleware.py           # Metrics middleware
```

**Implementation:**
```python
# src/monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Request metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint']
)

# Business metrics
alerts_created_total = Counter(
    'alerts_created_total',
    'Total alerts created',
    ['severity', 'alert_type']
)

decisions_made_total = Counter(
    'decisions_made_total',
    'Total decisions made',
    ['decision', 'risk_level']
)

# System metrics
active_connections = Gauge(
    'active_database_connections',
    'Active database connections'
)
```

#### Task 2.2: Structured Logging
**Effort:** 1 day
**Owner:** Backend Team

**Subtasks:**
- [ ] Configure structlog for JSON logging
- [ ] Add request ID tracking
- [ ] Add correlation ID for distributed tracing
- [ ] Log all errors with context
- [ ] Configure log levels by environment

**Acceptance Criteria:**
- ✅ All logs in JSON format
- ✅ Request ID in all logs
- ✅ Errors include stack traces
- ✅ Configurable via LOG_LEVEL env var

**Files to Modify:**
```
apps/api/src/
├── main.py                 # Configure structlog
└── logging_config.py       # NEW: Logging configuration
```

**Implementation:**
```python
# src/logging_config.py
import structlog
import logging

def configure_logging():
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer()
        ],
        logger_factory=structlog.PrintLoggerFactory(),
    )

# Usage
logger = structlog.get_logger()
logger.info("transaction_processed",
            transaction_id="txn-123",
            user_id="user-456",
            amount=50000)
```

#### Task 2.3: OpenTelemetry Tracing
**Effort:** 1.5 days
**Owner:** Backend Team
**Dependencies:** Task 2.1

**Subtasks:**
- [ ] Install opentelemetry dependencies
- [ ] Configure Jaeger exporter
- [ ] Auto-instrument FastAPI
- [ ] Auto-instrument SQLAlchemy
- [ ] Auto-instrument HTTP clients
- [ ] Add custom spans for business logic

**Acceptance Criteria:**
- ✅ Traces exported to Jaeger
- ✅ Database queries traced
- ✅ External API calls traced
- ✅ Custom spans for rule evaluation, feature extraction

**Files to Create:**
```
apps/api/src/monitoring/
└── tracing.py              # OpenTelemetry setup
```

**Implementation:**
```python
# src/monitoring/tracing.py
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

def setup_tracing(app):
    trace.set_tracer_provider(TracerProvider())

    jaeger_exporter = JaegerExporter(
        agent_host_name="localhost",
        agent_port=6831,
    )

    trace.get_tracer_provider().add_span_processor(
        BatchSpanProcessor(jaeger_exporter)
    )

    FastAPIInstrumentor.instrument_app(app)
    SQLAlchemyInstrumentor().instrument()

# Usage in code
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

def evaluate_rules(transaction):
    with tracer.start_as_current_span("evaluate_rules") as span:
        span.set_attribute("transaction_id", transaction.id)
        # ... rule evaluation logic
```

#### Task 2.4: Grafana Dashboards
**Effort:** 1 day
**Owner:** DevOps/Backend Team
**Dependencies:** Task 2.1

**Subtasks:**
- [ ] Set up Grafana in docker-compose
- [ ] Create system health dashboard
- [ ] Create API performance dashboard
- [ ] Create business metrics dashboard
- [ ] Configure alerts for critical metrics

**Acceptance Criteria:**
- ✅ Grafana accessible at localhost:3001
- ✅ Dashboards show live metrics
- ✅ Alerts configured (error rate >5%, p99 latency >500ms)

**Dashboards to Create:**
1. **System Health**
   - CPU, Memory, Disk usage
   - Database connection pool
   - Redis connection status
   - OpenSearch cluster health

2. **API Performance**
   - Request rate (req/sec)
   - Latency (p50, p95, p99)
   - Error rate by endpoint
   - Slowest endpoints

3. **Business Metrics**
   - Alerts created/hour
   - Decisions made/min
   - SAR filing rate
   - False positive rate

---

### 3. Caching Strategy ✅

**Duration:** 3 days
**Priority:** P1 (High)

#### Task 3.1: Redis Cache Infrastructure
**Effort:** 0.5 days
**Owner:** Backend Team

**Subtasks:**
- [ ] Install redis-py with async support
- [ ] Create cache utility with TTL support
- [ ] Implement cache-aside pattern
- [ ] Add cache key versioning
- [ ] Configure cache eviction policies

**Acceptance Criteria:**
- ✅ Redis client configured with connection pooling
- ✅ Cache utility supports get/set/delete/exists
- ✅ TTL properly enforced
- ✅ Cache invalidation working

**Files to Create:**
```
apps/api/src/cache/
├── __init__.py
├── redis_client.py         # Redis connection
├── cache_util.py           # Cache utilities
└── decorators.py           # @cached decorator
```

**Implementation:**
```python
# src/cache/cache_util.py
import json
from typing import Any, Optional
from redis import Redis
from functools import wraps

class CacheManager:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.version = "v1"

    def make_key(self, namespace: str, identifier: str) -> str:
        return f"{self.version}:{namespace}:{identifier}"

    def get(self, namespace: str, identifier: str) -> Optional[Any]:
        key = self.make_key(namespace, identifier)
        value = self.redis.get(key)
        return json.loads(value) if value else None

    def set(self, namespace: str, identifier: str, value: Any, ttl: int):
        key = self.make_key(namespace, identifier)
        self.redis.setex(key, ttl, json.dumps(value))

    def delete(self, namespace: str, identifier: str):
        key = self.make_key(namespace, identifier)
        self.redis.delete(key)

    def invalidate_pattern(self, pattern: str):
        keys = self.redis.keys(f"{self.version}:{pattern}:*")
        if keys:
            self.redis.delete(*keys)

# Decorator
def cached(namespace: str, ttl: int = 300):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = get_cache_manager()
            identifier = f"{func.__name__}:{hash(str(args) + str(kwargs))}"

            # Try cache
            cached_value = cache.get(namespace, identifier)
            if cached_value:
                return cached_value

            # Compute
            result = await func(*args, **kwargs)

            # Store
            cache.set(namespace, identifier, result, ttl)
            return result
        return wrapper
    return decorator
```

#### Task 3.2: Implement Caching for Hot Endpoints
**Effort:** 1.5 days
**Owner:** Backend Team
**Dependencies:** Task 3.1

**Subtasks:**
- [ ] Cache user risk profiles (5min TTL)
- [ ] Cache rule definitions (10min TTL)
- [ ] Cache feature aggregations (1min TTL)
- [ ] Cache sanctions lists (1hour TTL)
- [ ] Cache network graph data (15min TTL)
- [ ] Cache dashboard statistics (30sec TTL)

**Acceptance Criteria:**
- ✅ Cache hit rate >70% for cached endpoints
- ✅ Cache miss handled gracefully
- ✅ Cache invalidation on updates

**Files to Modify:**
```
apps/api/src/api/
├── risk_profiles.py        # Cache user risk profiles
├── monitoring_rules.py     # Cache rule definitions
└── monitoring_dashboard.py # Cache statistics
```

**Implementation:**
```python
# src/api/risk_profiles.py
from src.cache.decorators import cached

@router.get("/risk-profiles/{user_id}")
@cached(namespace="risk_profiles", ttl=300)  # 5 min
async def get_user_risk_profile(user_id: str, db: Session = Depends(get_db)):
    profile = db.query(UserRiskProfile).filter(
        UserRiskProfile.user_id == user_id
    ).first()
    return profile

@router.put("/risk-profiles/{user_id}")
async def update_user_risk_profile(
    user_id: str,
    update: RiskProfileUpdate,
    db: Session = Depends(get_db)
):
    # Update profile
    profile = db.query(UserRiskProfile).filter(...).first()
    profile.risk_score = update.risk_score
    db.commit()

    # Invalidate cache
    cache = get_cache_manager()
    cache.delete("risk_profiles", user_id)

    return profile
```

#### Task 3.3: Query Result Caching
**Effort:** 1 day
**Owner:** Backend Team
**Dependencies:** Task 3.1

**Subtasks:**
- [ ] Cache frequently accessed queries
- [ ] Cache aggregation results
- [ ] Cache search results (with pagination)
- [ ] Add cache warming on startup
- [ ] Monitor cache effectiveness

**Acceptance Criteria:**
- ✅ Complex queries cached (>100ms execution time)
- ✅ Cache warming completes on startup
- ✅ Cache metrics exposed (hit rate, miss rate)

**Implementation:**
```python
# Cache warming on startup
@app.on_event("startup")
async def warm_cache():
    cache = get_cache_manager()
    db = SessionLocal()

    # Warm active rules
    rules = db.query(MonitoringRule).filter(
        MonitoringRule.enabled == True
    ).all()
    for rule in rules:
        cache.set("rules", rule.rule_id, rule.dict(), ttl=600)

    # Warm sanctions lists
    sanctions = fetch_sanctions_lists()
    cache.set("sanctions", "all", sanctions, ttl=3600)

    db.close()
    logger.info("Cache warming complete")
```

---

## Phase 4B: Intelligence (Weeks 3-4)

**Goal:** Implement ML-powered features for intelligent alert triage and real-time notifications.

### 4. Intelligent Alert Triage ✅

**Duration:** 4-5 days
**Priority:** P1 (High)

#### Task 4.1: Historical Data Analysis
**Effort:** 1 day
**Owner:** Data Science Team

**Subtasks:**
- [ ] Export historical alert data with outcomes
- [ ] Analyze false positive patterns
- [ ] Identify predictive features
- [ ] Calculate baseline metrics (FP rate, SAR rate)
- [ ] Create labeled training dataset

**Acceptance Criteria:**
- ✅ Dataset with 10,000+ labeled alerts
- ✅ Features identified (20+ candidates)
- ✅ Baseline metrics documented

**Deliverables:**
```
apps/api/ml/
├── data/
│   └── alert_training_data.csv
├── notebooks/
│   └── 01_eda.ipynb              # Exploratory analysis
└── reports/
    └── feature_analysis.md
```

#### Task 4.2: ML Model Training
**Effort:** 2 days
**Owner:** Data Science Team
**Dependencies:** Task 4.1

**Subtasks:**
- [ ] Train binary classifier (SAR vs False Positive)
- [ ] Experiment with models (XGBoost, Random Forest, LightGBM)
- [ ] Perform hyperparameter tuning
- [ ] Evaluate on test set (AUC, precision, recall)
- [ ] Create model explainability report (SHAP)

**Acceptance Criteria:**
- ✅ AUC >0.85 on test set
- ✅ Precision >80% at 50% recall
- ✅ Model serialized and versioned

**Files to Create:**
```
apps/api/ml/
├── models/
│   └── alert_triage_v1.pkl
├── notebooks/
│   ├── 02_training.ipynb
│   └── 03_evaluation.ipynb
└── src/
    └── train.py                  # Training script
```

**Model Features:**
```python
# Feature groups
FEATURES = [
    # Alert features
    "severity", "alert_type", "risk_score",

    # User features
    "account_age_days", "kyc_status", "historical_sar_rate",
    "total_transaction_count", "avg_transaction_amount",

    # Transaction features
    "amount", "amount_zscore", "is_international",
    "time_of_day", "day_of_week",

    # Velocity features (from feature store)
    "velocity_1h_count", "velocity_24h_total",
    "velocity_7d_unique_countries",

    # Network features
    "counterparty_risk_score", "network_centrality"
]
```

#### Task 4.3: Model Serving Infrastructure
**Effort:** 1 day
**Owner:** Backend Team
**Dependencies:** Task 4.2

**Subtasks:**
- [ ] Create MLModel service class
- [ ] Load model on startup
- [ ] Create prediction endpoint
- [ ] Add model versioning support
- [ ] Implement fallback logic (if model fails, use rules)

**Acceptance Criteria:**
- ✅ Model predictions <50ms latency
- ✅ Graceful degradation if model unavailable
- ✅ Model version tracked in decisions

**Files to Create:**
```
apps/api/src/ml/
├── __init__.py
├── model_loader.py             # Load models
├── predictor.py                # Inference
└── explainer.py                # SHAP explanations
```

**Implementation:**
```python
# src/ml/predictor.py
import joblib
from typing import Dict, Any

class AlertTriagePredictor:
    def __init__(self, model_path: str):
        self.model = joblib.load(model_path)
        self.version = "v1.0"

    def predict(self, features: Dict[str, Any]) -> Dict[str, Any]:
        # Extract feature vector
        X = self._extract_features(features)

        # Predict
        proba = self.model.predict_proba([X])[0]
        prediction = "sar" if proba[1] > 0.5 else "false_positive"
        confidence = max(proba)

        return {
            "prediction": prediction,
            "confidence": confidence,
            "sar_probability": proba[1],
            "model_version": self.version
        }

    def explain(self, features: Dict[str, Any]) -> Dict[str, float]:
        # SHAP explanation
        X = self._extract_features(features)
        shap_values = self.explainer.shap_values([X])[0]

        return dict(zip(self.feature_names, shap_values))
```

#### Task 4.4: Auto-Triage Integration
**Effort:** 1 day
**Owner:** Backend Team
**Dependencies:** Task 4.3

**Subtasks:**
- [ ] Integrate predictor into alert creation flow
- [ ] Add ML prediction to alert record
- [ ] Auto-assign low-risk alerts to "auto_reviewed"
- [ ] Create triage dashboard with predictions
- [ ] Add analyst feedback mechanism

**Acceptance Criteria:**
- ✅ All new alerts get ML prediction
- ✅ Low-confidence alerts flagged for review
- ✅ High-confidence false positives auto-closed
- ✅ Analyst can override predictions

**Files to Modify:**
```
apps/api/src/api/
└── alerts.py                   # Add ML triage
apps/api/src/models/
└── transaction_models.py       # Add ml_prediction fields
```

**Implementation:**
```python
# src/api/alerts.py (modified)
from src.ml.predictor import AlertTriagePredictor

predictor = AlertTriagePredictor("ml/models/alert_triage_v1.pkl")

@router.post("/", response_model=AlertResponse)
def create_alert(alert: AlertCreate, db: Session = Depends(get_db)):
    # Create alert
    db_alert = Alert(**alert.dict())
    db.add(db_alert)
    db.flush()

    # Get ML prediction
    features = FeatureStore.compute_features(
        user_id=alert.user_id,
        event_type="alert_created",
        payload=alert.dict(),
        db=db
    )

    prediction = predictor.predict(features)

    # Store prediction
    db_alert.ml_prediction = prediction["prediction"]
    db_alert.ml_confidence = prediction["confidence"]
    db_alert.ml_model_version = prediction["model_version"]

    # Auto-triage if high confidence
    if prediction["confidence"] > 0.9:
        if prediction["prediction"] == "false_positive":
            db_alert.status = "auto_closed"
            db_alert.resolution_notes = "Auto-closed by ML (high confidence false positive)"
        elif prediction["prediction"] == "sar":
            db_alert.priority = 1  # Highest priority
            db_alert.assigned_to = "senior_analyst"

    db.commit()
    db.refresh(db_alert)
    return db_alert
```

---

### 5. Advanced Feature Engineering ✅

**Duration:** 3-4 days
**Priority:** P1 (High)

#### Task 5.1: Time-Series Features
**Effort:** 1.5 days
**Owner:** Data Science/Backend Team

**Subtasks:**
- [ ] Implement rolling window aggregations
- [ ] Calculate trend features (increasing/decreasing)
- [ ] Add seasonality features (day of week, time of day)
- [ ] Compute Z-scores for anomaly detection
- [ ] Add exponential moving averages

**Acceptance Criteria:**
- ✅ 15+ time-series features computed
- ✅ Features cached for performance
- ✅ Historical lookback configurable

**Files to Modify:**
```
apps/api/src/services/feature_store.py
```

**New Features:**
```python
# Time-series features to add
TIME_SERIES_FEATURES = {
    "velocity_trend_24h": "slope of transaction count over 24h",
    "amount_trend_7d": "trend in transaction amounts",
    "amount_zscore": "Z-score of current amount vs 30d average",
    "hourly_pattern_score": "deviation from typical hourly pattern",
    "weekly_pattern_score": "deviation from typical weekly pattern",
    "amount_ema_ratio": "current amount / EMA(30d)",
    "velocity_acceleration": "change in velocity trend",
}
```

#### Task 5.2: Graph-Based Features
**Effort:** 1.5 days
**Owner:** Backend Team
**Dependencies:** Network analysis service

**Subtasks:**
- [ ] Calculate user centrality scores (PageRank, betweenness)
- [ ] Identify user communities (Louvain algorithm)
- [ ] Measure network clustering coefficient
- [ ] Calculate shortest path to known risky entities
- [ ] Detect structural patterns (stars, chains, cycles)

**Acceptance Criteria:**
- ✅ Graph features computed in <200ms
- ✅ Graph cache updated incrementally
- ✅ 10+ graph features available

**Files to Create:**
```
apps/api/src/services/
└── graph_features.py           # Graph feature extraction
```

**Implementation:**
```python
# src/services/graph_features.py
import networkx as nx
from typing import Dict, Any

class GraphFeatureExtractor:
    def __init__(self, graph: nx.DiGraph):
        self.graph = graph
        self._centrality_cache = {}

    def extract_features(self, user_id: str) -> Dict[str, Any]:
        if user_id not in self.graph:
            return self._default_features()

        return {
            "degree_centrality": self._get_centrality(user_id),
            "betweenness_centrality": self._get_betweenness(user_id),
            "clustering_coefficient": nx.clustering(self.graph, user_id),
            "community_size": self._get_community_size(user_id),
            "min_distance_to_risky": self._min_distance_to_risky(user_id),
            "is_bridge_node": self._is_bridge(user_id),
            "neighbor_risk_score_avg": self._avg_neighbor_risk(user_id),
        }
```

#### Task 5.3: Automated Feature Store Updates
**Effort:** 1 day
**Owner:** Backend Team

**Subtasks:**
- [ ] Create background job to update features
- [ ] Implement incremental feature computation
- [ ] Add feature versioning
- [ ] Monitor feature staleness
- [ ] Create feature importance tracking

**Acceptance Criteria:**
- ✅ Features updated every 5 minutes
- ✅ Feature versions tracked
- ✅ Feature lag monitored (age of features)

**Files to Create:**
```
apps/api/src/tasks/
└── feature_refresh.py          # Celery task
```

---

### 6. Real-Time WebSocket Notifications ✅

**Duration:** 3 days
**Priority:** P1 (High)

#### Task 6.1: WebSocket Server Setup
**Effort:** 1 day
**Owner:** Backend Team

**Subtasks:**
- [ ] Install FastAPI WebSocket support
- [ ] Create WebSocket connection manager
- [ ] Implement authentication for WebSocket
- [ ] Add connection heartbeat/ping-pong
- [ ] Handle disconnections gracefully

**Acceptance Criteria:**
- ✅ WebSocket endpoint at /ws
- ✅ JWT authentication required
- ✅ Connection manager handles multiple clients
- ✅ Auto-reconnect on disconnect

**Files to Create:**
```
apps/api/src/websocket/
├── __init__.py
├── manager.py                  # Connection manager
├── auth.py                     # WS authentication
└── handlers.py                 # Message handlers
```

**Implementation:**
```python
# src/websocket/manager.py
from typing import Dict, Set
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)

    async def send_to_user(self, user_id: str, message: dict):
        if user_id in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except:
                    disconnected.add(connection)

            # Clean up disconnected
            for conn in disconnected:
                self.active_connections[user_id].discard(conn)

    async def broadcast(self, message: dict):
        for user_connections in self.active_connections.values():
            for connection in user_connections:
                try:
                    await connection.send_json(message)
                except:
                    pass

manager = ConnectionManager()
```

#### Task 6.2: Event Notification System
**Effort:** 1.5 days
**Owner:** Backend Team
**Dependencies:** Task 6.1

**Subtasks:**
- [ ] Create notification event types
- [ ] Integrate with EventBus
- [ ] Send WebSocket notifications on events
- [ ] Add notification preferences per user
- [ ] Create notification history

**Acceptance Criteria:**
- ✅ Notifications sent on: alert created, case assigned, decision made
- ✅ Users only receive relevant notifications
- ✅ Notification history stored

**Files to Modify:**
```
apps/api/src/websocket/
└── notifications.py            # NEW: Notification sender
apps/api/src/api/
├── alerts.py                   # Send notifications
└── cases.py                    # Send notifications
```

**Implementation:**
```python
# src/websocket/notifications.py
from src.websocket.manager import manager
from src.utils.event_bus import EventBus

@EventBus.subscribe("alert_created")
async def notify_alert_created(event_data: dict):
    alert = event_data["alert"]

    notification = {
        "type": "alert_created",
        "data": {
            "alert_id": alert.alert_id,
            "severity": alert.severity,
            "user_id": alert.user_id,
            "description": alert.description
        },
        "timestamp": datetime.utcnow().isoformat()
    }

    # Send to assigned analyst
    if alert.assigned_to:
        await manager.send_to_user(alert.assigned_to, notification)

    # Broadcast to admins
    await manager.broadcast_to_role("admin", notification)

@EventBus.subscribe("case_assigned")
async def notify_case_assigned(event_data: dict):
    case = event_data["case"]
    notification = {
        "type": "case_assigned",
        "data": {
            "case_id": case.case_id,
            "title": case.title
        }
    }
    await manager.send_to_user(case.assigned_to, notification)
```

#### Task 6.3: Frontend WebSocket Integration
**Effort:** 0.5 days
**Owner:** Frontend Team
**Dependencies:** Task 6.1

**Subtasks:**
- [ ] Create WebSocket hook (useWebSocket)
- [ ] Implement auto-reconnect logic
- [ ] Add notification toast component
- [ ] Update UI on real-time events
- [ ] Add notification sound (optional)

**Acceptance Criteria:**
- ✅ WebSocket auto-connects on login
- ✅ Notifications displayed as toasts
- ✅ UI updates without refresh

**Files to Create:**
```
apps/web/src/hooks/
└── useWebSocket.ts
apps/web/src/components/
└── NotificationToast.tsx
```

**Implementation:**
```typescript
// src/hooks/useWebSocket.ts
import { useEffect, useState } from 'react';
import { useAuth } from './useAuth';

export function useWebSocket() {
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [notifications, setNotifications] = useState<any[]>([]);
  const { token } = useAuth();

  useEffect(() => {
    if (!token) return;

    const websocket = new WebSocket(
      `ws://localhost:8000/ws?token=${token}`
    );

    websocket.onmessage = (event) => {
      const notification = JSON.parse(event.data);
      setNotifications((prev) => [notification, ...prev]);

      // Show toast
      toast.info(notification.data.description);
    };

    websocket.onerror = () => {
      // Auto-reconnect after 5s
      setTimeout(() => setWs(null), 5000);
    };

    setWs(websocket);

    return () => websocket.close();
  }, [token]);

  return { notifications };
}
```

---

## Phase 4C: Scale (Weeks 5-6)

**Goal:** Enable multi-tenancy, modern API layer (GraphQL), and advanced graph analytics.

### 7. Multi-Tenancy Support ✅

**Duration:** 4-5 days
**Priority:** P2 (Medium)

#### Task 7.1: Database Schema Changes
**Effort:** 1 day
**Owner:** Backend Team

**Subtasks:**
- [ ] Add tenant_id column to all tables
- [ ] Create tenants table
- [ ] Create tenant_users table (many-to-many)
- [ ] Update all foreign keys with tenant_id
- [ ] Create migration script

**Acceptance Criteria:**
- ✅ All tables have tenant_id
- ✅ Foreign keys enforce tenant isolation
- ✅ Migration runs without errors

**Files to Create:**
```
apps/api/alembic/versions/
└── xxxxx_add_multi_tenancy.py
```

**Schema Changes:**
```python
# Migration
def upgrade():
    # Add tenants table
    op.create_table(
        'tenants',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('tenant_id', sa.String(255), unique=True, nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow),
        sa.Column('is_active', sa.Boolean(), default=True)
    )

    # Add tenant_id to existing tables
    for table in ['transactions', 'alerts', 'cases', 'monitoring_rules']:
        op.add_column(table, sa.Column('tenant_id', sa.String(255)))
        op.create_index(f'ix_{table}_tenant_id', table, ['tenant_id'])
```

#### Task 7.2: Row-Level Security (RLS)
**Effort:** 1.5 days
**Owner:** Backend Team
**Dependencies:** Task 7.1

**Subtasks:**
- [ ] Implement tenant context middleware
- [ ] Add tenant filter to all queries
- [ ] Create tenant-scoped database session
- [ ] Test cross-tenant isolation
- [ ] Add tenant switching for admins

**Acceptance Criteria:**
- ✅ Users can only access own tenant data
- ✅ Queries automatically filtered by tenant_id
- ✅ Cross-tenant access blocked

**Files to Create:**
```
apps/api/src/tenancy/
├── __init__.py
├── middleware.py               # Tenant context middleware
├── context.py                  # Tenant context manager
└── queries.py                  # Tenant-aware queries
```

**Implementation:**
```python
# src/tenancy/middleware.py
from contextvars import ContextVar

tenant_context: ContextVar[Optional[str]] = ContextVar('tenant_context', default=None)

@app.middleware("http")
async def tenant_middleware(request: Request, call_next):
    # Extract tenant from JWT or header
    tenant_id = extract_tenant_from_request(request)

    token = tenant_context.set(tenant_id)
    try:
        response = await call_next(request)
        return response
    finally:
        tenant_context.reset(token)

# src/tenancy/queries.py
def get_tenant_filtered_query(model, db: Session):
    tenant_id = tenant_context.get()
    if not tenant_id:
        raise ValueError("No tenant context set")

    return db.query(model).filter(model.tenant_id == tenant_id)

# Usage
@router.get("/alerts")
def list_alerts(db: Session = Depends(get_db)):
    query = get_tenant_filtered_query(Alert, db)
    alerts = query.all()
    return alerts
```

#### Task 7.3: Tenant Configuration
**Effort:** 1 day
**Owner:** Backend Team
**Dependencies:** Task 7.2

**Subtasks:**
- [ ] Create tenant settings model
- [ ] Add per-tenant rate limits
- [ ] Add per-tenant feature flags
- [ ] Add per-tenant branding (logo, colors)
- [ ] Create tenant admin API

**Acceptance Criteria:**
- ✅ Each tenant has custom settings
- ✅ Rate limits enforced per tenant
- ✅ Feature flags work per tenant

**Files to Create:**
```
apps/api/src/api/
└── tenants.py                  # Tenant management API
apps/api/src/models/
└── tenant_models.py
```

#### Task 7.4: API Key-Based Tenant Routing
**Effort:** 1 day
**Owner:** Backend Team
**Dependencies:** Task 7.2

**Subtasks:**
- [ ] Create API keys table
- [ ] Generate API keys per tenant
- [ ] Add API key authentication
- [ ] Route requests to tenant based on API key
- [ ] Add API key rotation

**Acceptance Criteria:**
- ✅ API key identifies tenant
- ✅ Requests routed to correct tenant
- ✅ Invalid keys rejected

**Implementation:**
```python
# API Key format: yk_live_<tenant_id>_<random>
# Example: yk_live_acme_corp_a1b2c3d4e5f6

@router.middleware("http")
async def api_key_middleware(request: Request, call_next):
    api_key = request.headers.get("X-API-Key")

    if api_key and api_key.startswith("yk_"):
        # Parse tenant from API key
        parts = api_key.split("_")
        if len(parts) >= 4:
            tenant_id = parts[2]

            # Validate API key
            key_valid = validate_api_key(api_key, tenant_id)
            if key_valid:
                tenant_context.set(tenant_id)

    return await call_next(request)
```

---

### 8. GraphQL API Layer ✅

**Duration:** 4 days
**Priority:** P2 (Medium)

#### Task 8.1: Strawberry GraphQL Setup
**Effort:** 0.5 days
**Owner:** Backend Team

**Subtasks:**
- [ ] Install strawberry-graphql[fastapi]
- [ ] Create GraphQL schema structure
- [ ] Configure GraphQL endpoint (/graphql)
- [ ] Add GraphiQL playground
- [ ] Configure CORS for GraphQL

**Acceptance Criteria:**
- ✅ GraphQL endpoint accessible
- ✅ GraphiQL available at /graphql
- ✅ Schema validation working

**Files to Create:**
```
apps/api/src/graphql/
├── __init__.py
├── schema.py                   # Main schema
├── types/                      # GraphQL types
├── queries/                    # Query resolvers
└── mutations/                  # Mutation resolvers
```

**Implementation:**
```python
# src/main.py
from strawberry.fastapi import GraphQLRouter
from src.graphql.schema import schema

graphql_app = GraphQLRouter(schema)
app.include_router(graphql_app, prefix="/graphql")
```

#### Task 8.2: Define GraphQL Types
**Effort:** 1 day
**Owner:** Backend Team
**Dependencies:** Task 8.1

**Subtasks:**
- [ ] Create Alert type
- [ ] Create Transaction type
- [ ] Create Case type
- [ ] Create User type
- [ ] Create MonitoringRule type
- [ ] Add relationships between types

**Acceptance Criteria:**
- ✅ All main entities have GraphQL types
- ✅ Relationships properly defined
- ✅ Fields match database schema

**Files to Create:**
```
apps/api/src/graphql/types/
├── alert.py
├── transaction.py
├── case.py
├── user.py
└── rule.py
```

**Implementation:**
```python
# src/graphql/types/alert.py
import strawberry
from typing import Optional, List
from datetime import datetime

@strawberry.type
class Alert:
    id: int
    alert_id: str
    alert_type: str
    severity: str
    status: str
    user_id: str
    description: Optional[str]
    risk_score: Optional[float]
    created_at: datetime

    # Relationships
    @strawberry.field
    async def transaction(self, info) -> Optional["Transaction"]:
        # Resolver with DataLoader (prevents N+1)
        return await info.context["transaction_loader"].load(self.transaction_id)

    @strawberry.field
    async def case(self, info) -> Optional["Case"]:
        # Get associated case
        pass
```

#### Task 8.3: Implement Queries
**Effort:** 1.5 days
**Owner:** Backend Team
**Dependencies:** Task 8.2

**Subtasks:**
- [ ] Create alerts query with filters
- [ ] Create transactions query with filters
- [ ] Create cases query with filters
- [ ] Add pagination support
- [ ] Add sorting support
- [ ] Implement DataLoaders for N+1 prevention

**Acceptance Criteria:**
- ✅ All queries support filtering
- ✅ Pagination implemented
- ✅ No N+1 queries (use DataLoader)

**Files to Create:**
```
apps/api/src/graphql/queries/
├── alerts.py
├── transactions.py
└── cases.py
```

**Implementation:**
```python
# src/graphql/queries/alerts.py
import strawberry
from typing import List, Optional
from strawberry.types import Info

@strawberry.type
class Query:
    @strawberry.field
    async def alerts(
        self,
        info: Info,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Alert]:
        db = info.context["db"]

        query = db.query(AlertModel)
        if status:
            query = query.filter(AlertModel.status == status)
        if severity:
            query = query.filter(AlertModel.severity == severity)

        alerts = query.offset(offset).limit(limit).all()
        return alerts

    @strawberry.field
    async def alert(self, info: Info, alert_id: str) -> Optional[Alert]:
        db = info.context["db"]
        alert = db.query(AlertModel).filter(
            AlertModel.alert_id == alert_id
        ).first()
        return alert
```

#### Task 8.4: Implement Mutations
**Effort:** 1 day
**Owner:** Backend Team
**Dependencies:** Task 8.3

**Subtasks:**
- [ ] Create alert mutations (assign, escalate, resolve)
- [ ] Create case mutations (create, update, close)
- [ ] Create transaction ingestion mutation
- [ ] Add input validation
- [ ] Add authorization checks

**Acceptance Criteria:**
- ✅ All mutations properly validated
- ✅ Authorization enforced
- ✅ Optimistic updates supported

**Files to Create:**
```
apps/api/src/graphql/mutations/
├── alerts.py
├── cases.py
└── transactions.py
```

**Implementation:**
```python
# src/graphql/mutations/alerts.py
import strawberry
from strawberry.types import Info

@strawberry.type
class Mutation:
    @strawberry.mutation
    async def assign_alert(
        self,
        info: Info,
        alert_id: str,
        assigned_to: str
    ) -> Alert:
        db = info.context["db"]
        current_user = info.context["user"]

        # Authorization check
        if not current_user.has_role(["admin", "analyst"]):
            raise PermissionError("Not authorized")

        alert = db.query(AlertModel).filter(
            AlertModel.alert_id == alert_id
        ).first()

        if not alert:
            raise ValueError("Alert not found")

        alert.assigned_to = assigned_to
        alert.status = "in_review"
        db.commit()

        return alert
```

---

### 9. Advanced Graph Analytics ✅

**Duration:** 4-5 days
**Priority:** P2 (Medium)

#### Task 9.1: Neo4j Integration
**Effort:** 1 day
**Owner:** Backend Team

**Subtasks:**
- [ ] Add Neo4j to docker-compose
- [ ] Install neo4j Python driver
- [ ] Create graph sync service
- [ ] Sync transactions to Neo4j
- [ ] Create indexes on Neo4j

**Acceptance Criteria:**
- ✅ Neo4j accessible at localhost:7474
- ✅ Transaction data synced to graph
- ✅ Queries return in <1s

**Files to Create:**
```
apps/api/src/graph/
├── __init__.py
├── neo4j_client.py             # Neo4j connection
├── sync_service.py             # Sync data to Neo4j
└── queries.py                  # Cypher queries
```

**Implementation:**
```python
# src/graph/neo4j_client.py
from neo4j import GraphDatabase

class Neo4jClient:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def execute_query(self, query: str, parameters: dict = None):
        with self.driver.session() as session:
            result = session.run(query, parameters)
            return [record.data() for record in result]

# src/graph/sync_service.py
def sync_transaction_to_graph(transaction: Transaction):
    client = get_neo4j_client()

    # Create nodes
    query = """
    MERGE (u1:User {id: $user_id})
    MERGE (u2:User {id: $counterparty_id})
    CREATE (u1)-[t:TRANSACTION {
        id: $transaction_id,
        amount: $amount,
        timestamp: $timestamp,
        risk_score: $risk_score
    }]->(u2)
    """

    client.execute_query(query, {
        "user_id": transaction.user_id,
        "counterparty_id": transaction.counterparty_id,
        "transaction_id": transaction.transaction_id,
        "amount": float(transaction.amount),
        "timestamp": transaction.timestamp.isoformat(),
        "risk_score": float(transaction.risk_score or 0)
    })
```

#### Task 9.2: Community Detection
**Effort:** 1.5 days
**Owner:** Data Science/Backend Team
**Dependencies:** Task 9.1

**Subtasks:**
- [ ] Implement Louvain algorithm
- [ ] Identify transaction communities
- [ ] Calculate community risk scores
- [ ] Flag suspicious communities
- [ ] Create community visualization data

**Acceptance Criteria:**
- ✅ Communities detected in <5s
- ✅ High-risk communities flagged
- ✅ Results cached

**Files to Create:**
```
apps/api/src/graph/
└── community_detection.py
```

**Implementation:**
```python
# src/graph/community_detection.py
def detect_communities(min_size: int = 5) -> List[Dict]:
    client = get_neo4j_client()

    # Run Louvain algorithm
    query = """
    CALL gds.louvain.stream('transaction-graph')
    YIELD nodeId, communityId
    RETURN gds.util.asNode(nodeId).id as user_id, communityId
    ORDER BY communityId
    """

    results = client.execute_query(query)

    # Group by community
    communities = {}
    for row in results:
        community_id = row["communityId"]
        if community_id not in communities:
            communities[community_id] = []
        communities[community_id].append(row["user_id"])

    # Calculate risk scores
    community_list = []
    for community_id, members in communities.items():
        if len(members) >= min_size:
            risk_score = calculate_community_risk(members)
            community_list.append({
                "community_id": community_id,
                "members": members,
                "size": len(members),
                "risk_score": risk_score
            })

    return sorted(community_list, key=lambda x: x["risk_score"], reverse=True)
```

#### Task 9.3: Centrality Analysis
**Effort:** 1 day
**Owner:** Backend Team
**Dependencies:** Task 9.1

**Subtasks:**
- [ ] Calculate PageRank scores
- [ ] Calculate betweenness centrality
- [ ] Calculate closeness centrality
- [ ] Identify key nodes (hubs)
- [ ] Flag high-centrality risky users

**Acceptance Criteria:**
- ✅ Centrality scores computed
- ✅ Top 100 central nodes identified
- ✅ High-risk hubs flagged

**Implementation:**
```python
# src/graph/centrality.py
def calculate_centrality_scores() -> Dict[str, float]:
    client = get_neo4j_client()

    # PageRank
    query = """
    CALL gds.pageRank.stream('transaction-graph')
    YIELD nodeId, score
    RETURN gds.util.asNode(nodeId).id as user_id, score
    ORDER BY score DESC
    LIMIT 100
    """

    results = client.execute_query(query)
    return {row["user_id"]: row["score"] for row in results}

def identify_hubs(risk_threshold: float = 50) -> List[Dict]:
    centrality_scores = calculate_centrality_scores()

    hubs = []
    for user_id, centrality in centrality_scores.items():
        # Get user risk profile
        risk_profile = get_user_risk_profile(user_id)

        if risk_profile.risk_score > risk_threshold:
            hubs.append({
                "user_id": user_id,
                "centrality_score": centrality,
                "risk_score": risk_profile.risk_score,
                "alert_count": get_user_alert_count(user_id)
            })

    return hubs
```

#### Task 9.4: Path Analysis
**Effort:** 1 day
**Owner:** Backend Team
**Dependencies:** Task 9.1

**Subtasks:**
- [ ] Find shortest paths between users
- [ ] Trace fund flows (source to destination)
- [ ] Identify layering patterns
- [ ] Detect circular transactions
- [ ] Create path visualization data

**Acceptance Criteria:**
- ✅ Shortest path found in <1s
- ✅ Fund flows traced up to 10 hops
- ✅ Circular patterns detected

**Implementation:**
```python
# src/graph/path_analysis.py
def find_shortest_path(source_user: str, target_user: str, max_hops: int = 10):
    client = get_neo4j_client()

    query = """
    MATCH path = shortestPath(
        (source:User {id: $source})-[*..10]-(target:User {id: $target})
    )
    RETURN [node in nodes(path) | node.id] as users,
           [rel in relationships(path) | {
               amount: rel.amount,
               timestamp: rel.timestamp
           }] as transactions
    """

    result = client.execute_query(query, {
        "source": source_user,
        "target": target_user
    })

    return result[0] if result else None

def detect_circular_flows(user_id: str, min_amount: float = 1000):
    client = get_neo4j_client()

    # Find cycles starting and ending at user
    query = """
    MATCH path = (u:User {id: $user_id})-[:TRANSACTION*2..5]->(u)
    WHERE ALL(rel in relationships(path) WHERE rel.amount >= $min_amount)
    RETURN path
    LIMIT 10
    """

    results = client.execute_query(query, {
        "user_id": user_id,
        "min_amount": min_amount
    })

    return results
```

---

## Phase 4D: Crypto Native (Weeks 7-8)

**Goal:** Expand platform capabilities for crypto compliance and advanced reporting.

### 10. Blockchain Data Ingestion Pipeline ✅

**Duration:** 4 days
**Priority:** P2 (Medium)

#### Task 10.1: Blockchain Event Listener
**Effort:** 1.5 days
**Owner:** Backend Team

**Subtasks:**
- [ ] Install Web3.py / Ethers.py
- [ ] Create event listener service
- [ ] Listen to Transfer events on major chains (Ethereum, BSC, Polygon)
- [ ] Parse and normalize blockchain events
- [ ] Store events in database

**Acceptance Criteria:**
- ✅ Events captured in real-time (<5s latency)
- ✅ Multi-chain support (ETH, BSC, Polygon)
- ✅ Event normalization working

**Files to Create:**
```
apps/api/src/blockchain/
├── __init__.py
├── listener.py                 # Event listener
├── parsers.py                  # Event parsers
└── chains.py                   # Chain configurations
```

**Implementation:**
```python
# src/blockchain/listener.py
from web3 import Web3
from web3.middleware import geth_poa_middleware

class BlockchainListener:
    def __init__(self, rpc_url: str, contract_addresses: List[str]):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        self.contracts = contract_addresses

    async def listen_for_transfers(self):
        # Get latest block
        latest_block = self.w3.eth.block_number

        # Listen to Transfer events
        transfer_filter = self.w3.eth.filter({
            "fromBlock": latest_block,
            "toBlock": "latest",
            "address": self.contracts,
            "topics": [self.w3.keccak(text="Transfer(address,address,uint256)")]
        })

        while True:
            for event in transfer_filter.get_new_entries():
                await self.process_transfer_event(event)
            await asyncio.sleep(5)

    async def process_transfer_event(self, event):
        # Parse event
        from_address = "0x" + event["topics"][1].hex()[26:]
        to_address = "0x" + event["topics"][2].hex()[26:]
        amount = int(event["data"].hex(), 16)

        # Normalize to transaction format
        transaction = {
            "transaction_id": event["transactionHash"].hex(),
            "user_id": from_address,
            "counterparty_id": to_address,
            "amount": amount / 1e18,  # Convert from wei
            "currency": "ETH",
            "transaction_type": "crypto_transfer",
            "timestamp": datetime.utcnow(),
            "blockchain": "ethereum",
            "block_number": event["blockNumber"]
        }

        # Ingest to decisioning
        await ingest_blockchain_transaction(transaction)
```

#### Task 10.2: Address Risk Scoring
**Effort:** 1 day
**Owner:** Backend Team
**Dependencies:** Task 10.1

**Subtasks:**
- [ ] Create address risk model
- [ ] Integrate with TRM Labs API
- [ ] Score addresses on first seen
- [ ] Update scores periodically
- [ ] Flag high-risk addresses

**Acceptance Criteria:**
- ✅ Addresses scored on first transaction
- ✅ High-risk addresses flagged
- ✅ Risk scores cached (1 hour TTL)

**Files to Create:**
```
apps/api/src/blockchain/
└── address_scoring.py
```

#### Task 10.3: DeFi Protocol Tracking
**Effort:** 1 day
**Owner:** Backend Team
**Dependencies:** Task 10.1

**Subtasks:**
- [ ] Identify major DeFi protocols (Uniswap, Aave, Compound)
- [ ] Track interactions with DeFi
- [ ] Calculate DeFi exposure score
- [ ] Flag high-risk DeFi activity (mixers, bridges)

**Acceptance Criteria:**
- ✅ DeFi interactions tracked
- ✅ High-risk protocols flagged (Tornado Cash, etc.)
- ✅ Exposure score calculated

#### Task 10.4: Cross-Chain Transaction Linking
**Effort:** 0.5 days
**Owner:** Backend Team
**Dependencies:** Task 10.1

**Subtasks:**
- [ ] Detect cross-chain transfers (bridges)
- [ ] Link transactions across chains
- [ ] Track wallet clusters (same owner)
- [ ] Create unified transaction view

**Acceptance Criteria:**
- ✅ Bridge transactions detected
- ✅ Cross-chain flows tracked
- ✅ Wallet clustering working

---

### 11. Advanced Reporting & Analytics ✅

**Duration:** 4 days
**Priority:** P1 (High)

#### Task 11.1: Report Builder UI
**Effort:** 2 days
**Owner:** Frontend Team

**Subtasks:**
- [ ] Create drag-and-drop report builder
- [ ] Add filter controls (date range, users, alert types)
- [ ] Add chart/table components
- [ ] Add SQL query builder (optional)
- [ ] Preview report before generation

**Acceptance Criteria:**
- ✅ Drag-and-drop UI works
- ✅ Reports can be saved and reused
- ✅ Preview shows sample data

**Files to Create:**
```
apps/web/src/app/reports/
├── builder/
│   └── page.tsx                # Report builder
└── [report_id]/
    └── page.tsx                # View report
```

#### Task 11.2: Scheduled Report Generation
**Effort:** 1 day
**Owner:** Backend Team

**Subtasks:**
- [ ] Create report schedules table
- [ ] Add Celery task for report generation
- [ ] Generate PDF reports (using WeasyPrint)
- [ ] Generate Excel reports (using openpyxl)
- [ ] Email reports to recipients

**Acceptance Criteria:**
- ✅ Reports generated on schedule
- ✅ PDFs properly formatted
- ✅ Reports delivered via email

**Files to Create:**
```
apps/api/src/reporting/
├── generator.py                # Report generation
├── exporters.py                # PDF/Excel export
└── scheduler.py                # Schedule management
apps/api/src/tasks/
└── report_tasks.py             # Celery tasks
```

**Implementation:**
```python
# src/reporting/generator.py
from weasyprint import HTML
from jinja2 import Template

class ReportGenerator:
    def generate_sar_report(self, alert_ids: List[str]) -> bytes:
        # Load template
        template = Template(open("templates/sar_report.html").read())

        # Get data
        alerts = get_alerts(alert_ids)
        context = {
            "alerts": alerts,
            "generated_at": datetime.utcnow(),
            "total_alerts": len(alerts)
        }

        # Render HTML
        html = template.render(context)

        # Convert to PDF
        pdf = HTML(string=html).write_pdf()
        return pdf
```

#### Task 11.3: Regulatory Report Templates
**Effort:** 1 day
**Owner:** Compliance/Backend Team

**Subtasks:**
- [ ] Create SAR report template
- [ ] Create CTR (Currency Transaction Report) template
- [ ] Create DOEP (Director of OFAC Enforcement Program) template
- [ ] Create monthly compliance summary template
- [ ] Add regulatory citations

**Acceptance Criteria:**
- ✅ Templates match regulatory requirements
- ✅ All required fields included
- ✅ Reports exportable to PDF

**Files to Create:**
```
apps/api/templates/
├── sar_report.html
├── ctr_report.html
├── doep_report.html
└── monthly_summary.html
```

---

### 12. API Rate Limiting Enhancements ✅

**Duration:** 2-3 days
**Priority:** P2 (Medium)

#### Task 12.1: Tiered Rate Limits
**Effort:** 1 day
**Owner:** Backend Team

**Subtasks:**
- [ ] Define rate limit tiers (free, pro, enterprise)
- [ ] Store tier in user/tenant model
- [ ] Apply different limits per tier
- [ ] Create tier upgrade endpoint

**Acceptance Criteria:**
- ✅ Free: 100 req/hour
- ✅ Pro: 1,000 req/hour
- ✅ Enterprise: 10,000 req/hour

**Files to Modify:**
```
apps/api/src/middleware/rate_limiter.py
apps/api/src/models/tenant_models.py
```

**Implementation:**
```python
# Updated rate limiter
def get_rate_limit_for_user(user: CurrentUser) -> str:
    if user.tenant.tier == "free":
        return "100 per hour"
    elif user.tenant.tier == "pro":
        return "1000 per hour"
    elif user.tenant.tier == "enterprise":
        return "10000 per hour"
    return "100 per hour"  # default

@router.get("/alerts")
@limiter.limit(get_rate_limit_for_user)
def list_alerts(request: Request, ...):
    pass
```

#### Task 12.2: Dynamic Rate Limiting
**Effort:** 1 day
**Owner:** Backend Team
**Dependencies:** Task 12.1

**Subtasks:**
- [ ] Monitor system load (CPU, memory)
- [ ] Reduce limits when system under stress
- [ ] Prioritize premium tiers during congestion
- [ ] Add rate limit headers (X-RateLimit-*)

**Acceptance Criteria:**
- ✅ Limits reduced at >80% system load
- ✅ Premium users prioritized
- ✅ Rate limit headers returned

#### Task 12.3: Usage Analytics Dashboard
**Effort:** 0.5 days
**Owner:** Frontend Team
**Dependencies:** Task 12.1

**Subtasks:**
- [ ] Create usage dashboard
- [ ] Show current tier and limits
- [ ] Show usage over time (chart)
- [ ] Show rate limit violations
- [ ] Add upgrade CTA

**Acceptance Criteria:**
- ✅ Dashboard shows live usage
- ✅ Chart shows last 30 days
- ✅ Upgrade link works

---

## Testing Strategy Across All Phases

### Automated Testing Requirements

**Coverage Targets:**
- Unit Tests: 80%+
- Integration Tests: Key workflows
- E2E Tests: Critical user paths
- Load Tests: 500 req/sec sustained

**Test Types:**

1. **Unit Tests** (pytest)
```python
# Example: Feature store test
def test_compute_velocity_features(db_session):
    # Create test data
    user_id = "test-user"
    for i in range(10):
        create_transaction(user_id, amount=1000)

    # Compute features
    features = FeatureStore.compute_features(
        user_id=user_id,
        event_type="txn_fiat",
        payload={},
        db=db_session
    )

    # Assertions
    assert features["velocity_1h_count"] == 10
    assert features["velocity_1h_total"] == 10000
```

2. **Integration Tests**
```python
# Example: End-to-end transaction flow
def test_transaction_to_alert_flow(client, db_session):
    # Ingest transaction
    response = client.post("/api/transactions/ingest", json={
        "transaction_id": "txn-test",
        "user_id": "user-123",
        "amount": 50000,
        "currency": "USD"
    })
    assert response.status_code == 201

    # Check alert created
    alerts = client.get("/api/alerts?user_id=user-123").json()
    assert len(alerts) > 0
    assert alerts[0]["alert_type"] == "large_transaction"
```

3. **Load Tests** (Locust)
```python
# Example: Load test
from locust import HttpUser, task, between

class YufeedUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def get_alerts(self):
        self.client.get("/api/alerts")

    @task(1)
    def ingest_transaction(self):
        self.client.post("/api/decisioning/decide", json={
            "event_type": "txn_fiat",
            "payload": {"amount": 5000}
        })
```

4. **E2E Tests** (Playwright)
```typescript
// Example: Alert triage workflow
test('analyst can triage alerts', async ({ page }) => {
  await page.goto('/alerts');

  // Filter pending alerts
  await page.click('[data-testid="filter-pending"]');

  // Click first alert
  await page.click('[data-testid="alert-row"]:first-child');

  // Assign to self
  await page.click('[data-testid="assign-to-me"]');

  // Verify status changed
  await expect(page.locator('[data-testid="alert-status"]'))
    .toHaveText('In Review');
});
```

---

## Success Criteria

### Phase 4A (Foundation)
- ✅ Test coverage >80%
- ✅ Prometheus metrics exposed
- ✅ Grafana dashboards operational
- ✅ Cache hit rate >70%
- ✅ All tests passing in CI/CD

### Phase 4B (Intelligence)
- ✅ ML model AUC >0.85
- ✅ Auto-triage reduces analyst workload by 40%
- ✅ WebSocket latency <100ms
- ✅ 20+ features in feature store
- ✅ Feature computation <200ms

### Phase 4C (Scale)
- ✅ Multi-tenancy fully isolated
- ✅ GraphQL API operational
- ✅ Graph queries <1s
- ✅ Community detection working
- ✅ Path analysis accurate

### Phase 4D (Crypto Native)
- ✅ Blockchain events captured <5s latency
- ✅ Address risk scoring operational
- ✅ Reports generated on schedule
- ✅ Tiered rate limits enforced
- ✅ Usage dashboard live

---

## Risk Mitigation

### Technical Risks

**Risk 1: Performance Degradation**
- **Mitigation:** Load test after each phase
- **Rollback:** Feature flags for new features
- **Monitoring:** Alert on p99 latency >500ms

**Risk 2: Database Migration Failures**
- **Mitigation:** Test migrations on staging first
- **Rollback:** Alembic downgrade scripts
- **Backup:** Database backup before migration

**Risk 3: ML Model Accuracy**
- **Mitigation:** A/B test before full rollout
- **Rollback:** Fall back to rule-based system
- **Monitoring:** Track false positive rate

**Risk 4: Multi-Tenancy Leaks**
- **Mitigation:** Comprehensive isolation testing
- **Rollback:** Keep single-tenant mode available
- **Monitoring:** Audit log review for cross-tenant access

---

## Resource Requirements

### Team Composition
- **Backend Engineers:** 2-3 FTE
- **Frontend Engineers:** 1-2 FTE
- **Data Scientists:** 1 FTE
- **DevOps Engineer:** 0.5 FTE (shared)
- **QA Engineer:** 1 FTE

### Infrastructure
- **Development:**
  - Docker Compose (local)
  - GitHub Actions (CI/CD)

- **Production:**
  - 4 vCPU, 16GB RAM (API servers × 2)
  - PostgreSQL (100GB storage)
  - Redis (8GB memory)
  - Neo4j (50GB storage)
  - OpenSearch (200GB storage)

---

## Deployment Strategy

### Rollout Plan

**Week 1-2 (Phase 4A):**
- Deploy to staging
- Run load tests
- Fix performance issues
- Deploy to production (monitoring first)

**Week 3-4 (Phase 4B):**
- A/B test ML model (10% traffic)
- Monitor false positive rate
- Gradual rollout to 100%
- Enable WebSocket notifications

**Week 5-6 (Phase 4C):**
- Multi-tenancy: Create first test tenant
- GraphQL: Beta release to select users
- Graph: Enable for power users only

**Week 7-8 (Phase 4D):**
- Blockchain: Enable for crypto customers
- Reporting: Release to compliance officers
- Rate limiting: Enforce tiers

---

## Documentation Requirements

Each phase requires:
- [ ] Architecture documentation
- [ ] API documentation (OpenAPI/GraphQL schema)
- [ ] Developer guide
- [ ] Operations runbook
- [ ] User guide (for product features)

---

## Conclusion

This implementation plan provides a **detailed, task-level roadmap** for Phase 4 enhancements. Each task includes:
- Effort estimates
- Acceptance criteria
- Dependencies
- Implementation guidance
- Test requirements

**Total Duration:** 8 weeks
**Total Tasks:** 80+ tasks across 12 major features

The plan is designed to be **incremental** and **low-risk**, with each phase building on the previous one. All changes are **backwards compatible** and can be rolled back if needed.

---

**Next Steps:**
1. Review and approve this plan
2. Assign tasks to team members
3. Create JIRA/Linear tickets
4. Begin Phase 4A (Foundation)

**Questions or modifications?** Let me know which phase to start with!

---

*Last Updated: January 22, 2026*
*Version: 1.0*
*Status: Ready for Implementation*
