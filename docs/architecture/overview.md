# YuFeed Architecture Overview

## System Context

YuFeed is a compliance platform designed for financial institutions operating in the EU. It provides AI-powered monitoring of regulatory changes, AML detection, and compliance workflow automation.

```
┌─────────────────────────────────────────────────────────────────────┐
│                         EXTERNAL SYSTEMS                             │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐    │
│  │ EUR-Lex  │  │Legifrance│  │  OFAC    │  │   EU Sanctions   │    │
│  │   API    │  │   RSS    │  │  Lists   │  │      Lists       │    │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────────┬─────────┘    │
│       │             │             │                │                │
│       └─────────────┴─────────────┴────────────────┘                │
│                          │                                          │
│                    ┌─────┴─────┐                                    │
│                    │  YuFeed   │                                    │
│                    │  Platform │                                    │
│                    └─────┬─────┘                                    │
│                          │                                          │
│       ┌──────────────────┼──────────────────┐                      │
│       │                  │                  │                      │
│  ┌────┴─────┐      ┌────┴─────┐      ┌────┴─────┐                 │
│  │   Web    │      │  Mobile  │      │   API    │                 │
│  │   App    │      │   App    │      │ Clients  │                 │
│  └──────────┘      └──────────┘      └──────────┘                 │
└─────────────────────────────────────────────────────────────────────┘
```

## Architecture Principles

1. **Security First**: Multi-tenant isolation, encryption, audit logging
2. **Scalability**: Horizontal scaling, stateless services
3. **Reliability**: Circuit breakers, retries, graceful degradation
4. **Observability**: Distributed tracing, metrics, structured logging
5. **Modularity**: Microservices-ready, clear boundaries

## Component Architecture

### API Layer (FastAPI)

```
┌─────────────────────────────────────────────────────────────┐
│                         API LAYER                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │   Routers   │ │ Middleware  │ │  Dependencies│           │
│  │             │ │             │ │              │            │
│  │ • /alerts   │ │ • Auth      │ │ • get_db     │            │
│  │ • /cases    │ │ • Tenant    │ │ • CurrentUser│            │
│  │ • /policies │ │ • Rate Limit│ │ • RequireRole│            │
│  │ • /gap-...  │ │ • Audit Log │ │              │            │
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘            │
│         │               │               │                    │
│         └───────────────┴───────────────┘                    │
│                         │                                    │
│                  ┌──────┴──────┐                            │
│                  │  Services   │                            │
│                  │   Layer     │                            │
│                  └─────────────┘                            │
└─────────────────────────────────────────────────────────────┘
```

### Service Layer

| Service | Responsibility | Key Features |
|---------|---------------|--------------|
| **AlertEngine** | AML alert management | Detection, triage, investigation |
| **CaseService** | Case lifecycle | Creation, assignment, resolution |
| **PolicyEngine** | Policy management | CRUD, versioning, approval |
| **GapAnalyzer** | Compliance gaps | Analysis, mapping, reporting |
| **ReminderService** | Deadline tracking | Notifications, subscriptions |
| **PolicyGenerator** | AI policy creation | Template-based generation |
| **ImpactAnalyzer** | Regulatory impact | AI-powered change assessment |
| **SanctionsService** | Sanctions screening | Real-time screening, batch |
| **TenantService** | Multi-tenancy | Isolation, billing, quotas |

### Data Layer

```
┌─────────────────────────────────────────────────────────────┐
│                        DATA LAYER                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                 PostgreSQL                          │    │
│  │  ┌──────────┬──────────┬──────────┬──────────┐     │    │
│  │  │ Tenants  │  Users   │  Alerts  │  Cases   │     │    │
│  │  ├──────────┼──────────┼──────────┼──────────┤     │    │
│  │  │ Policies │Obligations│AuditLogs │Evidence  │     │    │
│  │  └──────────┴──────────┴──────────┴──────────┘     │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐     │
│  │    Redis    │  │ OpenSearch  │  │   Vector DB     │     │
│  │   (Cache)   │  │   (Search)  │  │  (Embeddings)   │     │
│  └─────────────┘  └─────────────┘  └─────────────────┘     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Multi-Tenancy Architecture

YuFeed implements **row-level security** for complete tenant isolation:

```
┌─────────────────────────────────────────────────────────────┐
│                      TENANT ISOLATION                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   Request                    Middleware                     │
│      │                           │                          │
│      │  1. Extract tenant        │                          │
│      │     from API key          │                          │
│      │──────────────────────────>│                          │
│      │                           │                          │
│      │  2. Set tenant context    │                          │
│      │                           │                          │
│      │  3. Query with RLS        │                          │
│      │<──────────────────────────│                          │
│      │                           │                          │
│      │  SELECT * FROM alerts     │                          │
│      │  WHERE tenant_id = 't1'   │                          │
│      │       (automatic)         │                          │
│      │                           │                          │
└─────────────────────────────────────────────────────────────┘
```

### Tenant Data Model

```
Tenant
├── api_keys[]
├── users[]
├── settings{}
├── rate_limits{}
└── feature_flags{}
```

## AI/ML Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      AI/ML PIPELINE                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Input Sources                                               │
│  ├── EUR-Lex Documents                                       │
│  ├── User Queries                                            │
│  ├── Transaction Data                                        │
│  └── Alert Context                                           │
│         │                                                    │
│         ▼                                                    │
│  ┌─────────────────────────────────────────┐                 │
│  │         Preprocessing                   │                 │
│  │  • Text extraction                      │                 │
│  │  • Chunking                             │                 │
│  │  • Embedding generation                 │                 │
│  └─────────────────┬───────────────────────┘                 │
│                    │                                         │
│         ┌─────────┴──────────┐                              │
│         ▼                    ▼                              │
│  ┌──────────────┐    ┌──────────────┐                      │
│  │ Vector Store │    │ LLM Service  │                      │
│  │  (Chroma)    │    │ (Anthropic)  │                      │
│  └──────────────┘    └──────────────┘                      │
│         │                    │                              │
│         └─────────┬──────────┘                              │
│                   ▼                                         │
│  ┌─────────────────────────────────────────┐                 │
│  │          AI Applications                │                 │
│  │  • Impact Assessment                    │                 │
│  │  • Policy Generation                    │                 │
│  │  • Alert Triage                         │                 │
│  │  • Natural Language Queries             │                 │
│  └─────────────────────────────────────────┘                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Security Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SECURITY LAYERS                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Layer 1: Transport                                          │
│  ├── TLS 1.3 for all connections                            │
│  └── Certificate pinning                                    │
│                                                              │
│  Layer 2: Authentication                                     │
│  ├── JWT with refresh tokens                                │
│  ├── API key authentication                                 │
│  └── MFA support                                            │
│                                                              │
│  Layer 3: Authorization                                      │
│  ├── RBAC (Role-Based Access Control)                       │
│  ├── ABAC (Attribute-Based) for fine-grained                │
│  └── Tenant isolation (RLS)                                 │
│                                                              │
│  Layer 4: Application Security                               │
│  ├── Input validation                                       │
│  ├── Rate limiting                                          │
│  ├── CSRF protection                                        │
│  └── SQL injection prevention                               │
│                                                              │
│  Layer 5: Data Protection                                    │
│  ├── Encryption at rest (AES-256)                           │
│  ├── Field-level encryption for PII                         │
│  └── Secure key management                                  │
│                                                              │
│  Layer 6: Audit & Monitoring                                 │
│  ├── Comprehensive audit logging                            │
│  ├── Real-time alerting                                     │
│  └── Anomaly detection                                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    KUBERNETES DEPLOYMENT                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                   Ingress Controller                 │    │
│  │              (SSL termination, routing)              │    │
│  └──────────────────────────┬──────────────────────────┘    │
│                             │                                │
│  ┌──────────────────────────┴──────────────────────────┐    │
│  │                  API Pods (3 replicas)               │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │    │
│  │  │   API Pod    │  │   API Pod    │  │  API Pod   │ │    │
│  │  │  (FastAPI)   │  │  (FastAPI)   │  │ (FastAPI)  │ │    │
│  │  └──────────────┘  └──────────────┘  └────────────┘ │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                 Worker Pods (2 replicas)             │    │
│  │  ┌──────────────┐  ┌──────────────┐                 │    │
│  │  │ Celery Worker│  │ Celery Worker│                 │    │
│  │  └──────────────┘  └──────────────┘                 │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │               Stateful Services                      │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────────┐    │    │
│  │  │PostgreSQL│ │  Redis   │ │  OpenSearch      │    │    │
│  │  │(Primary) │ │ (Cache)  │ │  (Search)        │    │    │
│  │  │(Replica) │ │(Sentinel)│ │                  │    │    │
│  │  └──────────┘ └──────────┘ └──────────────────┘    │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Next.js 14, React, TypeScript | Web application |
| **Backend** | FastAPI, Python 3.12 | API services |
| **Database** | PostgreSQL 15 | Primary data store |
| **Cache** | Redis 7 | Caching, sessions, queues |
| **Search** | OpenSearch 2.x | Full-text search |
| **Queue** | Celery + Redis | Background jobs |
| **AI/ML** | Anthropic Claude, Chroma | LLM, vector store |
| **Monitoring** | Prometheus, Grafana | Metrics, dashboards |
| **Tracing** | Jaeger | Distributed tracing |
| **Logs** | Loki | Log aggregation |
| **Infra** | Docker, Kubernetes | Container orchestration |

## Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| API p95 latency | < 200ms | 150ms |
| Database query p99 | < 50ms | 30ms |
| AI inference p95 | < 5s | 3s |
| Availability | 99.9% | 99.95% |
| Test coverage | > 80% | 75% |

## Scalability

- **Horizontal**: API pods scale based on CPU/memory
- **Database**: Read replicas for query scaling
- **Cache**: Redis Cluster for high availability
- **Queue**: Celery workers scale with queue depth

## Related Documentation

- [API Design Guidelines](api-design.md)
- [Data Model](data-model.md)
- [Security Architecture](security.md)
- [Deployment Guide](../operations/deployment.md)
- [ADR-001: Multi-tenancy](../adr/001-multi-tenancy.md)
- [ADR-002: AI Architecture](../adr/002-ai-architecture.md)
