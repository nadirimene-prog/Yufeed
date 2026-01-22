# Yufeed Architecture Documentation

> **Version:** 1.0.0
> **Last Updated:** 2026-01-19
> **Status:** Production-Ready MVP

---

## Table of Contents

1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Technology Stack](#technology-stack)
4. [Project Structure](#project-structure)
5. [Backend Architecture](#backend-architecture)
6. [Frontend Architecture](#frontend-architecture)
7. [Data Flow](#data-flow)
8. [API Contracts](#api-contracts)
9. [Security](#security)
10. [Development Workflow](#development-workflow)
11. [Deployment](#deployment)
12. [Known Issues & Technical Debt](#known-issues--technical-debt)

---

## Overview

Yufeed is an EU Legal Monitoring and AML (Anti-Money Laundering) compliance platform that combines:
- **Regulatory Intelligence**: Monitor EU regulations, directives, and decisions
- **Transaction Monitoring**: Real-time fraud detection and AML compliance
- **AI-Powered Analysis**: Multi-agent AI system for document analysis, risk scoring, and SAR filing
- **Network Analysis**: Visualize transaction networks and identify suspicious patterns

### Key Features
- Full-text search across EU legal documents
- AI-powered compliance impact assessment
- Transaction monitoring with configurable rules
- Alert triage and case management
- Sanctions screening (EU, OFAC, UN)
- Network graph analysis
- SAR (Suspicious Activity Report) filing automation
- Compliance reporting and dashboard

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         FRONTEND                            │
│  Next.js 14+ App Router │ React 18+ │ TypeScript │ Tailwind│
│                    (Port 3000)                              │
└───────────────────────┬─────────────────────────────────────┘
                        │ REST API (HTTP/JSON)
                        │
┌───────────────────────▼─────────────────────────────────────┐
│                        BACKEND                              │
│              FastAPI │ Python 3.12 │ Pydantic               │
│                     (Port 8000)                             │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  API Layer   │  │  AI Agents   │  │  Integrations│    │
│  │   (Routers)  │  │ (Anthropic)  │  │  (CELEX/SOAP)│    │
│  └───────┬──────┘  └───────┬──────┘  └───────┬──────┘    │
│          │                 │                  │            │
│  ┌───────▼─────────────────▼──────────────────▼──────┐    │
│  │             Services Layer                         │    │
│  │  (Business Logic, Rule Engine, Risk Scoring)      │    │
│  └───────┬────────────────────────────────────────────┘    │
│          │                                                  │
│  ┌───────▼────────────┐        ┌──────────────────┐       │
│  │   Models Layer     │        │  Schemas Layer   │       │
│  │  (SQLAlchemy ORM)  │        │   (Pydantic)     │       │
│  └───────┬────────────┘        └──────────────────┘       │
└──────────┼──────────────────────────────────────────────────┘
           │
┌──────────▼───────────────────────────────────────────────┐
│                   INFRASTRUCTURE                         │
│                                                          │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐       │
│  │ PostgreSQL │  │   Redis    │  │ OpenSearch │       │
│  │   (5432)   │  │   (6379)   │  │   (9200)   │       │
│  └────────────┘  └────────────┘  └────────────┘       │
│                                                          │
│  ┌────────────────────────────────────────────┐        │
│  │        Celery Worker                        │        │
│  │  (Background Tasks, Daily Ingestion)       │        │
│  └────────────────────────────────────────────┘        │
└──────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Purpose | Technology |
|-----------|---------|------------|
| **Frontend** | User interface, data visualization | Next.js, React, TypeScript, Tailwind, shadcn/ui |
| **Backend API** | RESTful endpoints, request validation | FastAPI, Pydantic |
| **Services** | Business logic, rule engine, risk scoring | Python, custom engines |
| **AI Agents** | Document analysis, impact assessment, SAR generation | Anthropic Claude API |
| **Worker** | Async tasks, scheduled ingestion | Celery, Redis |
| **PostgreSQL** | Primary data store (documents, transactions, cases) | PostgreSQL 15+ |
| **OpenSearch** | Full-text search, document indexing | OpenSearch 2.x |
| **Redis** | Caching, message broker, rate limiting | Redis 7.x |

---

## Technology Stack

### Backend
```yaml
Runtime: Python 3.12+
Framework: FastAPI 0.115+
ORM: SQLAlchemy 2.0+
Validation: Pydantic 2.0+
Database: PostgreSQL 15+
Search: OpenSearch 2.x
Cache: Redis 7.x
Task Queue: Celery 5.x
AI: Anthropic Claude API (Sonnet 4.5)
SOAP Client: Zeep
HTTP Client: httpx
```

### Frontend
```yaml
Framework: Next.js 14+ (App Router)
Language: TypeScript 5+
UI Library: React 18+
Styling: Tailwind CSS 3.4+
Component Library: shadcn/ui
Charts: Recharts, D3.js
Graph Visualization: react-force-graph
Icons: lucide-react
HTTP Client: axios
```

### Infrastructure
```yaml
Containerization: Docker, Docker Compose
Database: PostgreSQL 15
Search Engine: OpenSearch 2.x
Cache/Broker: Redis 7.x
Email Testing: Mailhog
```

---

## Project Structure

```
yufeed/
├── backend/                  # Python/FastAPI backend
│   ├── src/
│   │   ├── ai/              # AI agents and orchestration
│   │   │   ├── agents/      # Specific agent implementations
│   │   │   │   ├── base.py          # Abstract base agent
│   │   │   │   ├── compliance_officer.py
│   │   │   │   ├── investigation.py
│   │   │   │   └── sar.py
│   │   │   ├── prompts/     # AI prompt templates
│   │   │   ├── analyzer.py  # Document analysis
│   │   │   ├── impact_analyzer.py
│   │   │   ├── orchestrator.py
│   │   │   ├── rag_service.py
│   │   │   └── alert_triage.py
│   │   │
│   │   ├── api/             # FastAPI routers (controllers)
│   │   │   ├── endpoints.py         # Core search & doc endpoints
│   │   │   ├── compliance.py        # Compliance dashboard
│   │   │   ├── impact.py            # Impact assessment
│   │   │   ├── query.py             # AI query interface
│   │   │   ├── transactions.py      # Transaction ingestion
│   │   │   ├── alerts.py            # Alert management
│   │   │   ├── cases.py             # Case management
│   │   │   ├── monitoring_dashboard.py
│   │   │   ├── monitoring_rules.py
│   │   │   ├── network_analysis.py
│   │   │   ├── reporting.py
│   │   │   ├── celex.py             # CELEX document retrieval
│   │   │   └── aml_officer.py       # AML Officer dashboard
│   │   │
│   │   ├── models/          # SQLAlchemy ORM models
│   │   │   ├── models.py            # LegalDocument, ImpactAssessment, etc.
│   │   │   ├── transaction_models.py # Transaction, Alert, MonitoringRule
│   │   │   ├── compliance.py        # ComplianceCase, ComplianceProfile
│   │   │   ├── annotation.py        # User annotations
│   │   │   └── impact_assessment.py
│   │   │
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   │   ├── schemas.py
│   │   │   ├── transaction_schemas.py
│   │   │   └── compliance.py
│   │   │
│   │   ├── services/        # Business logic layer
│   │   │   ├── rule_engine.py       # Low-level condition evaluator
│   │   │   ├── rules_engine.py      # High-level rule service
│   │   │   ├── risk_scoring.py      # Risk calculation
│   │   │   └── network_analysis.py  # Graph analysis
│   │   │
│   │   ├── ingestion/       # Data ingestion pipeline
│   │   │   ├── rss.py              # RSS feed ingestion
│   │   │   ├── soap.py             # SOAP API client
│   │   │   ├── cellar.py           # CELEX/CELLAR integration
│   │   │   ├── content_extractor.py
│   │   │   ├── diff_analyzer.py
│   │   │   ├── processor.py
│   │   │   └── manager.py
│   │   │
│   │   ├── integrations/    # External API integrations
│   │   │   ├── base.py
│   │   │   └── sanctions/
│   │   │       ├── service.py      # Sanctions screening orchestrator
│   │   │       ├── eu_list.py      # EU sanctions
│   │   │       └── ofac_list.py    # OFAC sanctions
│   │   │
│   │   ├── compliance/      # Compliance-specific logic
│   │   │   └── sar_filing.py       # SAR generation and filing
│   │   │
│   │   ├── cache/           # Caching layer
│   │   │   └── celex_cache.py
│   │   │
│   │   ├── utils/           # Utility functions
│   │   │   └── celex_utils.py
│   │   │
│   │   ├── config.py        # Configuration management
│   │   ├── database.py      # DB connection & session management
│   │   ├── search.py        # OpenSearch client
│   │   ├── email_service.py # Email notifications
│   │   ├── email_templates.py
│   │   ├── main.py          # FastAPI app entrypoint
│   │   └── worker.py        # Celery worker entrypoint
│   │
│   ├── alembic/             # Database migrations
│   ├── tests/               # Backend tests
│   └── scripts/             # Utility scripts
│
├── frontend/                # Next.js frontend
│   ├── src/
│   │   ├── app/             # Next.js App Router pages
│   │   │   ├── layout.tsx          # Root layout
│   │   │   ├── page.tsx            # Dashboard home
│   │   │   ├── dashboard/          # Main compliance dashboard
│   │   │   ├── search/             # Legal document search
│   │   │   ├── doc/[celex]/        # Document detail view
│   │   │   ├── query/              # AI query interface
│   │   │   ├── alerts/             # Alert list
│   │   │   ├── cases/              # Case management
│   │   │   ├── compliance/         # KYC/KYB compliance
│   │   │   ├── compliance-report/  # Compliance reporting
│   │   │   ├── watchlists/         # Monitoring feeds
│   │   │   ├── aml-officer/        # AML Officer dashboard
│   │   │   │   ├── ask/            # Ask AML Officer
│   │   │   │   ├── sanctions/      # Sanctions screening
│   │   │   │   ├── investigations/ # Investigation tool
│   │   │   │   └── sar/            # SAR filing
│   │   │   ├── transaction-alerts/ # Transaction alerts
│   │   │   ├── transaction-monitoring/
│   │   │   │   ├── dashboard/
│   │   │   │   ├── rules/
│   │   │   │   └── alerts/[id]/
│   │   │   ├── network-analysis/   # Network graph
│   │   │   ├── monitoring/         # System monitoring
│   │   │   └── sar/prepare/        # SAR preparation
│   │   │
│   │   ├── components/      # React components
│   │   │   ├── ui/          # Reusable UI primitives (shadcn/ui)
│   │   │   │   ├── button.tsx
│   │   │   │   ├── dialog.tsx
│   │   │   │   ├── table.tsx
│   │   │   │   ├── data-table.tsx
│   │   │   │   ├── command.tsx
│   │   │   │   ├── skeleton.tsx
│   │   │   │   ├── metric-card.tsx
│   │   │   │   ├── timeline.tsx
│   │   │   │   ├── sparkline.tsx
│   │   │   │   ├── risk-badge.tsx
│   │   │   │   ├── status-indicator.tsx
│   │   │   │   ├── notification-badge.tsx
│   │   │   │   ├── loading-state.tsx
│   │   │   │   └── empty-state.tsx
│   │   │   │
│   │   │   ├── compliance/  # Domain-specific components
│   │   │   │   ├── RiskBadge.tsx (⚠️ DUPLICATE)
│   │   │   │   └── StatusChip.tsx
│   │   │   │
│   │   │   ├── dashboard/   # Dashboard widgets
│   │   │   │   └── risk-trend-chart.tsx
│   │   │   │
│   │   │   ├── network/     # Network visualization
│   │   │   │   └── graph-controls.tsx
│   │   │   │
│   │   │   ├── doc/         # Document components
│   │   │   │   └── timeline-view.tsx
│   │   │   │
│   │   │   ├── sidebar.tsx          # Main navigation
│   │   │   ├── header.tsx           # Top header with breadcrumbs
│   │   │   ├── command-menu.tsx     # Cmd+K global search
│   │   │   ├── search-bar.tsx
│   │   │   ├── filters.tsx
│   │   │   ├── results-table.tsx
│   │   │   ├── query-chat.tsx       # AI chat interface
│   │   │   ├── impact-assessment.tsx
│   │   │   ├── doc-tabs.tsx
│   │   │   ├── compliance-badges.tsx (⚠️ DUPLICATE)
│   │   │   ├── NetworkGraph.tsx
│   │   │   ├── page-transition.tsx
│   │   │   ├── error-boundary.tsx
│   │   │   ├── keyboard-shortcuts-help.tsx
│   │   │   └── ToastProvider.tsx
│   │   │
│   │   ├── lib/             # Utilities and API clients
│   │   │   ├── api.ts              # Core API client
│   │   │   ├── compliance-api.ts   # Compliance endpoints
│   │   │   ├── aml-officer-api.ts  # AML Officer endpoints
│   │   │   ├── query-api.ts        # AI query endpoints
│   │   │   ├── impact-api.ts       # Impact assessment
│   │   │   ├── types.ts            # Type definitions
│   │   │   ├── watchlist-types.ts
│   │   │   └── utils.ts            # Helper functions
│   │   │
│   │   └── types/           # Shared TypeScript types
│   │       └── compliance.ts
│   │
│   └── public/              # Static assets
│
├── docker-compose.yml       # Docker orchestration
├── .env.example            # Environment variable template
└── README.md               # Project README
```

---

## Backend Architecture

### Layered Architecture Pattern

The backend follows a **strict layered architecture** to maintain separation of concerns:

```
┌────────────────────────────────────────┐
│          API Layer (Routers)           │  ← HTTP endpoints, request validation
├────────────────────────────────────────┤
│         Services Layer                 │  ← Business logic, rule engine
├────────────────────────────────────────┤
│    Models (ORM) + Schemas (Pydantic)  │  ← Data models & validation
├────────────────────────────────────────┤
│      Database / Search / Cache         │  ← Data persistence
└────────────────────────────────────────┘
```

### API Layer (`/api/`)

**Purpose**: Handle HTTP requests, validate input, return responses

**Pattern**:
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.database import get_db
from src import models, schemas

router = APIRouter(prefix="/api/v1", tags=["resource"])

@router.get("/resource/{id}", response_model=schemas.ResourceRead)
def get_resource(id: str, db: Session = Depends(get_db)):
    """Docstring explaining endpoint."""
    resource = db.query(models.Resource).filter(models.Resource.id == id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    return resource
```

**Key Routers**:
- `endpoints.py` - Core search & document retrieval
- `compliance.py` - Compliance dashboard, high-risk docs, domain stats
- `impact.py` - Impact assessment creation & retrieval
- `query.py` - AI-powered query interface
- `transactions.py` - Transaction ingestion
- `alerts.py` - Alert CRUD, status updates, workflow
- `cases.py` - Case management
- `monitoring_dashboard.py` - Transaction monitoring metrics
- `monitoring_rules.py` - Rule CRUD
- `network_analysis.py` - Graph analysis endpoints
- `reporting.py` - Compliance reporting
- `celex.py` - CELEX document metadata
- `aml_officer.py` - AML Officer AI dashboard

### Services Layer (`/services/`)

**Purpose**: Encapsulate business logic, keep it separate from HTTP concerns

**Key Services**:
- `rule_engine.py` - Low-level condition evaluator (operators, nested logic)
- `rules_engine.py` - High-level rule service (evaluation, alert creation, context generation)
- `risk_scoring.py` - Risk calculation algorithms
- `network_analysis.py` - Graph algorithms for transaction networks

**⚠️ Known Issue**: `rule_engine.py` and `rules_engine.py` have overlapping functionality. See [Technical Debt](#known-issues--technical-debt).

### Models Layer (`/models/`)

**Purpose**: Define database schema using SQLAlchemy ORM

**Key Models**:
- `LegalDocument` - EU legal documents
- `ImpactAssessment` - Business impact analysis
- `Transaction` - Financial transactions
- `Alert` - Transaction monitoring alerts
- `MonitoringRule` - Configurable rules
- `ComplianceCase` - KYC/KYB cases
- `ComplianceProfile` - Entity profiles
- `RiskProfile` - Risk scoring data

**Naming Convention**:
- File: `snake_case.py`
- Class: `PascalCase`
- Table: `snake_case` (auto-generated)

### Schemas Layer (`/schemas/`)

**Purpose**: Pydantic models for request/response validation

**Pattern**:
```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ResourceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None

class ResourceRead(BaseModel):
    id: str
    name: str
    created_at: datetime

    class Config:
        from_attributes = True  # Pydantic v2 (was orm_mode in v1)
```

**⚠️ Migration Note**: Code uses mixed Pydantic v1 (`from_orm()`) and v2 (`from_attributes = True`) patterns. Standardization needed.

### AI Agents (`/ai/`)

**Multi-Agent Architecture**:

```
Orchestrator (orchestrator.py)
    ├── Base Agent (agents/base.py) - Abstract class
    ├── Compliance Officer (agents/compliance_officer.py)
    ├── Investigation Agent (agents/investigation.py)
    └── SAR Agent (agents/sar.py)
```

**Pattern**:
```python
from src.ai.agents.base import BaseAgent

class ComplianceOfficerAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="Compliance Officer", role="compliance_analysis")

    async def process(self, task: dict) -> dict:
        """Process compliance task."""
        # Agent-specific logic
        return result
```

### Ingestion Pipeline (`/ingestion/`)

**Daily ingestion workflow** (orchestrated by Celery):

```
1. RSS Feed (rss.py) → Fetch latest EU documents
2. SOAP API (soap.py) → Retrieve full document metadata
3. CELLAR (cellar.py) → Get CELEX-specific data
4. Content Extractor (content_extractor.py) → Parse document body
5. Processor (processor.py) → Normalize & store
6. OpenSearch Indexing (search.py) → Index for search
```

**Caching**:
- CELEX metadata cached in Redis (`cache/celex_cache.py`)
- TTL: 24 hours

### Database Schema

**Key Relationships**:
```
LegalDocument (1) ─┬─< (N) ImpactAssessment
                    └─< (N) Annotation

Transaction (1) ─< (N) Alert
Alert (N) ─> (1) MonitoringRule

ComplianceCase (1) ─< (N) CaseActivity
ComplianceProfile (1) ─< (N) ComplianceCase
```

**Indexes** (⚠️ **Needs Improvement**):
- `LegalDocument.celex` (primary key)
- `LegalDocument.compliance_domain`
- Missing: `Alert.user_id`, `Alert.status`, `Transaction.user_id`

---

## Frontend Architecture

### Next.js App Router Pattern

Yufeed uses Next.js 14+ **App Router** (not Pages Router):

```
app/
├── layout.tsx              # Root layout (sidebar, header)
├── page.tsx                # Home page (/)
├── dashboard/
│   └── page.tsx            # /dashboard
├── search/
│   └── page.tsx            # /search
└── doc/[celex]/
    └── page.tsx            # /doc/:celex (dynamic route)
```

**Server vs Client Components**:
- **Server Components** (default): Fetch data on server, no hydration
- **Client Components** (`"use client"`): Interactive, stateful components

### Component Organization

```
components/
├── ui/                     # Reusable primitives (shadcn/ui)
│   ├── button.tsx
│   ├── dialog.tsx
│   └── ...
├── compliance/             # Domain-specific components
├── dashboard/              # Dashboard widgets
├── network/                # Graph visualization
└── [feature-components]    # Top-level feature components
```

**Pattern**:
```typescript
// ui/button.tsx - Primitive component
import { forwardRef } from "react"
import { cn } from "@/lib/utils"

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "outline" | "ghost"
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(buttonVariants({ variant }), className)}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button }
```

### API Client Pattern

**Centralized client** (`lib/api.ts`):
```typescript
import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Feature-specific endpoint
export const searchDocuments = async (params: SearchParams): Promise<SearchResponse> => {
  const response = await apiClient.get<SearchResponse>('/search', { params });
  return response.data;
};
```

**⚠️ Inconsistency**: Some components bypass `apiClient` and use inline `fetch()` or create separate axios instances.

### State Management

**No global state library** (Redux, Zustand, etc.). State managed via:
- React `useState` for local state
- Props for component communication
- Server Components for server-side data fetching

**Recommendation**: Consider Zustand or Context API for shared state (e.g., current user, notifications).

### Type Safety

**TypeScript configuration** (`tsconfig.json`):
```json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true
  }
}
```

**⚠️ Type Issues**:
- 13+ instances of `any` types
- Missing generic type parameters
- Type definitions duplicated across files

---

## Data Flow

### Document Search Flow

```
User enters search query
    │
    ▼
Frontend: /search/page.tsx
    │ calls searchDocuments(params)
    ▼
API Client: lib/api.ts
    │ GET /api/v1/search?q=...
    ▼
Backend: api/endpoints.py → search_api()
    │ validates params (schemas.SearchParams)
    ▼
OpenSearch: search.py → search_documents()
    │ executes query with filters
    ▼
PostgreSQL: enriches results with metadata
    │ joins with LegalDocument table
    ▼
Response: schemas.SearchResponse
    │ returns paginated results
    ▼
Frontend: displays ResultsTable
```

### Transaction Alert Flow

```
Transaction ingested
    │ POST /api/v1/transactions
    ▼
Backend: api/transactions.py → ingest_transaction()
    │ stores in PostgreSQL
    ▼
Services: rules_engine.py → evaluate_transaction()
    │ checks all active MonitoringRules
    ▼
If rule matches:
    │ create Alert in database
    │ calculate risk_score
    │ generate context (AI optional)
    ▼
Worker: Celery task sends email notification
    │ uses email_service.py
    ▼
Frontend: /alerts/page.tsx polls for new alerts
    │ displays in AlertsTable
```

### Impact Assessment Flow

```
User requests impact assessment for document
    │ POST /api/v1/impact/assess
    ▼
Backend: api/impact.py → create_impact_assessment()
    │ validates CELEX
    ▼
AI: ai/impact_analyzer.py → analyze_impact()
    │ calls Claude API with document context
    │ generates impact_level, obligations, deadlines
    ▼
PostgreSQL: stores ImpactAssessment record
    │ linked to LegalDocument
    ▼
Frontend: components/impact-assessment.tsx
    │ displays structured assessment
```

---

## API Contracts

### REST API Conventions

**Base URL**: `http://localhost:8000/api/v1` (dev) | `https://api.yufeed.eu/api/v1` (prod)

**Authentication**: None (MVP - to be added)

**Request Format**:
- Content-Type: `application/json`
- Query params: URL-encoded
- Body: JSON

**Response Format**:
```json
{
  "data": [...],       // or single object
  "count": 100,        // optional, for paginated responses
  "next": "...",       // optional, pagination cursor
  "prev": "..."        // optional, pagination cursor
}
```

**Error Format**:
```json
{
  "detail": "Error message",
  "status_code": 400
}
```

### Key Endpoints

#### Search
```
GET /api/v1/search
Query Params:
  - q: string (search query)
  - filters: JSON (compliance_domain, date_range)
  - page: int (default 1)
  - page_size: int (default 20)

Response: {
  results: LegalDocument[],
  total: int,
  page: int,
  page_size: int
}
```

#### Transactions
```
POST /api/v1/transactions
Body: {
  transaction_id: string,
  user_id: string,
  amount: float,
  currency: string,
  timestamp: datetime,
  ...
}

Response: { id: string, status: string }
```

#### Alerts
```
GET /api/v1/alerts
Response: Alert[]

PATCH /api/v1/alerts/{id}/status
Body: { status: "open" | "investigating" | "resolved" | "false_positive" }
Response: Alert
```

#### Impact Assessment
```
POST /api/v1/impact/assess
Body: { celex: string, business_context?: string }
Response: ImpactAssessment

GET /api/v1/impact/{celex}
Response: ImpactAssessment | null
```

#### AML Officer
```
POST /api/v1/aml-officer/ask
Body: { question: string, context?: object }
Response: { answer: string, confidence: float, sources: string[] }

POST /api/v1/aml-officer/sanctions/screen
Body: { entity_name: string, entity_type: "individual" | "organization" }
Response: { matches: SanctionMatch[], risk_level: string }
```

**Full API Documentation**: [http://localhost:8000/api/docs](http://localhost:8000/api/docs) (Swagger UI)

---

## Security

### Current Implementation

#### Backend Security Headers (`main.py:30-66`)
```python
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block
Content-Security-Policy: default-src 'self'; ...
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), microphone=(), camera=()
```

#### CORS Configuration
```python
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")

# ⚠️ No validation - arbitrary origins can be injected via env var
```

#### Input Validation
- Pydantic schemas validate all incoming requests
- SQL injection prevented by SQLAlchemy ORM (no raw SQL)
- CELEX format validated with regex

#### Secrets Management
- API keys stored in environment variables
- No hardcoded secrets in code
- `.env.example` provided for developers

### Security Gaps (⚠️ **Needs Attention**)

1. **No Authentication/Authorization** - All endpoints are public
2. **No Rate Limiting** - Vulnerable to DoS
3. **No CSRF Protection** - Vulnerable to CSRF attacks
4. **API Keys Not Rotated** - Anthropic API key shared across all requests
5. **No Request Size Limits** - Can be exploited for DoS
6. **CORS Validation Missing** - See [Backend Analysis](#backend-architecture)
7. **No Audit Logging** - No record of who accessed what

### Recommended Additions

```python
# backend/src/main.py

from fastapi_limiter import FastAPILimiter
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Authentication
from fastapi.security import OAuth2PasswordBearer
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Request size limit
app.add_middleware(
    RequestSizeLimitMiddleware,
    max_body_size=10 * 1024 * 1024  # 10MB
)
```

---

## Development Workflow

### Local Development Setup

1. **Clone repository**
   ```bash
   git clone https://github.com/yourorg/yufeed.git
   cd yufeed
   ```

2. **Environment setup**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Start services**
   ```bash
   docker-compose up --build
   ```

4. **Access services**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000/api/docs
   - OpenSearch: http://localhost:9200
   - Mailhog: http://localhost:8025

### Development Commands

**Backend**:
```bash
# Run backend locally (without Docker)
cd backend
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000

# Database migrations
alembic revision --autogenerate -m "description"
alembic upgrade head

# Run tests
pytest

# Type checking
mypy src/

# Linting
flake8 src/
black src/
```

**Frontend**:
```bash
cd frontend
npm install
npm run dev          # Dev server
npm run build        # Production build
npm run lint         # ESLint
npm run type-check   # TypeScript checking
```

**Worker**:
```bash
cd backend
celery -A src.worker worker --loglevel=info
```

### Git Workflow

**Branching Strategy**:
- `main` - Production-ready code
- `develop` - Integration branch
- `feature/*` - New features
- `bugfix/*` - Bug fixes
- `hotfix/*` - Urgent production fixes

**Commit Convention**:
```
<type>(<scope>): <subject>

<body>

<footer>
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Example:
```
feat(api): Add sanctions screening endpoint

- Integrate OFAC and EU sanctions lists
- Add caching for sanctions data
- Implement fuzzy name matching

Closes #123
```

---

## Deployment

### Docker Deployment

**Production Docker Compose** (not included in repo):
```yaml
version: '3.8'
services:
  backend:
    build: ./backend
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/yufeed
      - REDIS_URL=redis://redis:6379/0
      - OPENSEARCH_URL=https://opensearch:9200
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    depends_on:
      - postgres
      - redis
      - opensearch

  frontend:
    build: ./frontend
    environment:
      - NEXT_PUBLIC_API_URL=https://api.yufeed.eu

  worker:
    build: ./backend
    command: celery -A src.worker worker --loglevel=info
    depends_on:
      - redis
      - postgres
```

### Environment Variables

**Backend** (`.env`):
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/yufeed
REDIS_URL=redis://localhost:6379/0
OPENSEARCH_URL=http://localhost:9200
OPENSEARCH_USER=admin
OPENSEARCH_PASSWORD=admin

ANTHROPIC_API_KEY=sk-ant-...

ALLOWED_ORIGINS=http://localhost:3000,https://yufeed.eu
ENABLE_HSTS=true  # Production only

CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

SMTP_HOST=localhost
SMTP_PORT=1025
SMTP_FROM=noreply@yufeed.eu
```

**Frontend** (`.env.local`):
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Health Checks

```bash
# Backend health
curl http://localhost:8000/health
# Response: {"status": "ok"}

# OpenSearch health
curl http://localhost:9200/_cluster/health

# Redis health
redis-cli ping
# Response: PONG
```

---

## Known Issues & Technical Debt

### Critical (P0)

1. **Missing `re` import** ✅ **FIXED** - `services/rule_engine.py:21` used `re.match()` without import
2. **No database connection error handling** - `database.py:12-17` doesn't handle connection failures
3. **CORS validation missing** - `main.py:13-16` allows arbitrary origins via env var

### High Priority (P1)

4. **Duplicate rule engines** - `rule_engine.py` and `rules_engine.py` overlap
5. **Duplicate RiskBadge components** - 3 separate implementations in frontend
6. **Mixed Pydantic v1/v2 patterns** - `.from_orm()` vs `from_attributes = True`
7. **Print statements instead of logging** - Multiple files use `print()` in production code
8. **Missing database indexes** - `Alert.user_id`, `Alert.status`, `Transaction.user_id`
9. **No authentication/authorization** - All endpoints are public

### Medium Priority (P2)

10. **Type safety issues** - 13+ instances of `any` types in frontend
11. **Missing error boundaries** - Frontend has no global error fallback
12. **Mock data in production code** - `compliance-api.ts:88-147`
13. **API pattern inconsistencies** - Different error handling across clients
14. **Missing accessibility labels** - Buttons, inputs lack `aria-label`
15. **Incomplete SAR filing** - TODOs for FinCEN, FIU, goAML integrations
16. **No input sanitization** - Search queries not validated for length/ReDoS
17. **Missing loading states** - Several pages lack skeleton loaders

### Low Priority (P3)

18. **Dead code** - Unused components: `keyboard-shortcuts-help.tsx`, `graph-controls.tsx`
19. **Enum duplication** - `RiskLevel` defined in both `models.py` and `compliance.py`
20. **Inline component definitions** - Causes unnecessary re-renders
21. **Missing JSDoc comments** - Complex components lack documentation
22. **Bundle size** - No code splitting between pages

### Future Enhancements

23. **Add rate limiting** - Protect against DoS
24. **Implement CSRF protection** - Add token validation
25. **Add audit logging** - Track all API access
26. **Optimize database queries** - Add pagination, LIMIT clauses
27. **Add caching layer** - Redis caching for frequent queries
28. **Implement WebSocket support** - Real-time alert notifications
29. **Add monitoring/observability** - Prometheus, Grafana, Sentry
30. **Implement feature flags** - LaunchDarkly or similar

---

## Appendix

### Glossary

- **CELEX**: EU document identifier system (e.g., `32015L0849`)
- **CELLAR**: EU's database of legal documents
- **SAR**: Suspicious Activity Report (AML compliance)
- **KYC**: Know Your Customer (identity verification)
- **KYB**: Know Your Business (entity verification)
- **AML**: Anti-Money Laundering
- **OFAC**: Office of Foreign Assets Control (US sanctions)

### References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Next.js Documentation](https://nextjs.org/docs)
- [shadcn/ui](https://ui.shadcn.com/)
- [EUR-Lex API](https://eur-lex.europa.eu/content/tools/webservices.html)
- [Anthropic Claude API](https://docs.anthropic.com/)

---

**Document Version**: 1.0.0
**Last Updated**: 2026-01-19
**Maintainer**: Yufeed Development Team

