# Contributing to Yufeed

Thank you for your interest in contributing to Yufeed! This guide will help you understand our development workflow, coding standards, and best practices.

By participating, you agree to follow our `CODE_OF_CONDUCT.md`. For security issues, please follow `SECURITY.md` instead of opening a public issue.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Development Environment](#development-environment)
3. [Coding Standards](#coding-standards)
4. [Architecture Guidelines](#architecture-guidelines)
5. [Git Workflow](#git-workflow)
6. [Testing](#testing)
7. [Documentation](#documentation)
8. [Pull Request Process](#pull-request-process)
9. [Code Review Guidelines](#code-review-guidelines)
10. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Prerequisites

- **Docker** 20.10+ and **Docker Compose** 2.0+
- **Git** 2.30+
- **Node.js** 18+ and **npm** 9+ (for local frontend development)
- **Python** 3.12+ (for local backend development)
- **IDE**: VS Code (recommended) or any editor with TypeScript/Python support

### First-Time Setup

1. **Fork the repository** on GitHub

2. **Clone your fork**
   ```bash
   git clone https://github.com/YOUR_USERNAME/yufeed.git
   cd yufeed
   ```

3. **Add upstream remote**
   ```bash
   git remote add upstream https://github.com/ORIGINAL_ORG/yufeed.git
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys (see Environment Variables section)
   ```

5. **Start services**
   ```bash
   docker-compose up --build
   ```

6. **Verify setup**
   - Frontend: http://localhost:3000
   - Backend API Docs: http://localhost:8000/api/docs
   - Test search: Try searching for "AMLD5" in the UI

---

## Development Environment

### Docker Development (Recommended)

All services run in Docker containers with hot-reload enabled:

```bash
# Start all services
docker-compose up

# Start in background
docker-compose up -d

# View logs
docker compose logs -f api
docker compose logs -f web

# Rebuild after dependency changes
docker-compose up --build

# Stop all services
docker-compose down

# Clean volumes (⚠️ deletes database data)
docker-compose down -v
```

### Local Development (Without Docker)

#### Backend

```bash
cd apps/api

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start FastAPI server
uvicorn src.main:app --reload --port 8000

# Start Celery worker (separate terminal)
celery -A src.worker worker --loglevel=info
```

**Prerequisites for local backend**:
- PostgreSQL 15+ running on localhost:5432
- Redis 7+ running on localhost:6379
- OpenSearch 2.x running on localhost:9200

#### Frontend

```bash
cd apps/web

# Install dependencies
npm install

# Start Next.js dev server
npm run dev

# Runs on http://localhost:3000
```

### Environment Variables

Create `.env` in the project root:

```bash
# Database
DATABASE_URL=postgresql://yufeed:yufeed123@localhost:5432/yufeed

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# OpenSearch
OPENSEARCH_URL=http://localhost:9200
OPENSEARCH_USER=admin
OPENSEARCH_PASSWORD=admin

# AI (Required for AI features)
ANTHROPIC_API_KEY=sk-ant-your-key-here

# CORS (comma-separated origins)
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Email (Mailhog for dev)
SMTP_HOST=localhost
SMTP_PORT=1025
SMTP_FROM=noreply@yufeed.eu

# Feature Flags
ENABLE_HSTS=false  # Set to true in production
```

Frontend `.env.local`:
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Coding Standards

### Backend (Python)

#### Style Guide

Follow **PEP 8** with these additions:
- Line length: 100 characters (not 79)
- Use **type hints** on all function signatures
- Use **docstrings** (Google style) for all public functions/classes

**Example**:
```python
from typing import Optional, List
from sqlalchemy.orm import Session
from src import models, schemas

def get_document_by_celex(
    db: Session,
    celex: str,
    include_impact: bool = False
) -> Optional[models.LegalDocument]:
    """
    Retrieve a legal document by CELEX identifier.

    Args:
        db: Database session
        celex: CELEX identifier (e.g., "32015L0849")
        include_impact: Whether to include impact assessment

    Returns:
        LegalDocument if found, None otherwise

    Raises:
        ValueError: If CELEX format is invalid
    """
    if not is_valid_celex(celex):
        raise ValueError(f"Invalid CELEX format: {celex}")

    query = db.query(models.LegalDocument).filter(
        models.LegalDocument.celex == celex
    )

    if include_impact:
        query = query.options(joinedload(models.LegalDocument.impact_assessment))

    return query.first()
```

#### Imports Order

1. Standard library
2. Third-party packages
3. Local imports

```python
import os
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from src.database import get_db
from src import models, schemas
from src.services.rule_engine import RuleEngine
```

#### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Module | `snake_case` | `rule_engine.py` |
| Class | `PascalCase` | `RuleEngine` |
| Function | `snake_case` | `evaluate_condition()` |
| Variable | `snake_case` | `user_id` |
| Constant | `UPPER_SNAKE_CASE` | `MAX_RETRY_ATTEMPTS` |
| Private | `_leading_underscore` | `_internal_method()` |

#### Error Handling

**DO**:
```python
import logging

logger = logging.getLogger(__name__)

def process_transaction(transaction_id: str) -> bool:
    try:
        transaction = fetch_transaction(transaction_id)
        validate_transaction(transaction)
        return True
    except TransactionNotFoundError as e:
        logger.warning(f"Transaction not found: {transaction_id}")
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        logger.error(f"Validation failed: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error processing transaction: {transaction_id}")
        raise HTTPException(status_code=500, detail="Internal server error")
```

**DON'T**:
```python
# ❌ Generic exception handling
try:
    process()
except Exception:
    return False  # Silent failure

# ❌ Print statements in production
try:
    process()
except Exception as e:
    print(f"Error: {e}")  # Use logger instead

# ❌ Bare except clause
try:
    process()
except:  # Never do this
    pass
```

#### Database Queries

**DO**:
```python
from sqlalchemy.orm import joinedload

# Use ORM, not raw SQL
documents = db.query(models.LegalDocument)\
    .filter(models.LegalDocument.compliance_domain == "AML")\
    .limit(10)\
    .all()

# Eager loading for relationships
documents = db.query(models.LegalDocument)\
    .options(joinedload(models.LegalDocument.impact_assessment))\
    .all()

# Pagination
documents = db.query(models.LegalDocument)\
    .offset((page - 1) * page_size)\
    .limit(page_size)\
    .all()
```

**DON'T**:
```python
# ❌ Raw SQL (unless absolutely necessary)
db.execute("SELECT * FROM legal_documents WHERE celex = ?", (celex,))

# ❌ N+1 query problem
for doc in documents:
    impact = doc.impact_assessment  # Triggers separate query per doc

# ❌ Loading all records
all_documents = db.query(models.LegalDocument).all()  # No limit
```

#### Tools

```bash
# Linting
flake8 src/

# Formatting
black src/
isort src/

# Type checking
mypy src/

# Run all checks
flake8 src/ && black --check src/ && mypy src/
```

---

### Frontend (TypeScript/React)

#### Style Guide

- **TypeScript strict mode** enabled
- **Functional components** with hooks (no class components)
- **No `any` types** unless absolutely necessary
- **Props interfaces** for all components
- **CSS modules** or **Tailwind classes** (no inline styles)

**Example**:
```typescript
import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface AlertCardProps {
  alertId: string;
  onResolve?: (id: string) => void;
  className?: string;
}

export function AlertCard({ alertId, onResolve, className }: AlertCardProps) {
  const [loading, setLoading] = useState(false);
  const [alert, setAlert] = useState<Alert | null>(null);

  useEffect(() => {
    fetchAlert(alertId).then(setAlert);
  }, [alertId]);

  const handleResolve = async () => {
    setLoading(true);
    try {
      await resolveAlert(alertId);
      onResolve?.(alertId);
    } catch (error) {
      console.error('Failed to resolve alert:', error);
    } finally {
      setLoading(false);
    }
  };

  if (!alert) return <Skeleton className={className} />;

  return (
    <div className={cn('rounded-lg border p-4', className)}>
      <h3 className="font-semibold">{alert.title}</h3>
      <p className="text-sm text-muted-foreground">{alert.description}</p>
      <Button onClick={handleResolve} disabled={loading}>
        {loading ? 'Resolving...' : 'Resolve'}
      </Button>
    </div>
  );
}
```

#### Component Structure

```typescript
// 1. Imports
import { useState } from 'react';
import { Button } from '@/components/ui/button';

// 2. Types/Interfaces
interface Props {
  title: string;
}

// 3. Constants (outside component)
const MAX_ITEMS = 10;

// 4. Helper functions (outside component)
function formatDate(date: Date): string {
  return date.toLocaleDateString();
}

// 5. Component
export function MyComponent({ title }: Props) {
  // 5a. Hooks
  const [count, setCount] = useState(0);

  // 5b. Derived state
  const isMaxed = count >= MAX_ITEMS;

  // 5c. Event handlers
  const handleClick = () => {
    setCount(prev => prev + 1);
  };

  // 5d. Effects
  useEffect(() => {
    // ...
  }, [count]);

  // 5e. Render
  return (
    <div>
      <h1>{title}</h1>
      <Button onClick={handleClick} disabled={isMaxed}>
        Count: {count}
      </Button>
    </div>
  );
}
```

#### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Component | `PascalCase` | `AlertCard.tsx` |
| Hook | `camelCase` with `use` prefix | `useAlert()` |
| Function | `camelCase` | `fetchAlerts()` |
| Variable | `camelCase` | `alertCount` |
| Constant | `UPPER_SNAKE_CASE` | `API_BASE_URL` |
| Type/Interface | `PascalCase` | `AlertCardProps` |
| Enum | `PascalCase` | `AlertStatus` |

#### React Best Practices

**DO**:
```typescript
// ✅ Typed props
interface Props {
  title: string;
  onClose: () => void;
}

// ✅ Memoized components (when needed)
const ExpensiveComponent = memo(({ data }: Props) => {
  // ...
});

// ✅ Custom hooks for reusable logic
function useAlert(alertId: string) {
  const [alert, setAlert] = useState<Alert | null>(null);
  useEffect(() => {
    fetchAlert(alertId).then(setAlert);
  }, [alertId]);
  return alert;
}

// ✅ Error boundaries
<ErrorBoundary fallback={<ErrorFallback />}>
  <MyComponent />
</ErrorBoundary>
```

**DON'T**:
```typescript
// ❌ Props without types
function MyComponent({ title, onClose }) {  // No types
  // ...
}

// ❌ Inline component definitions
function Parent() {
  const Child = () => <div>Child</div>;  // Recreated every render
  return <Child />;
}

// ❌ Mutating state directly
const [items, setItems] = useState([]);
items.push(newItem);  // ❌ Mutates state
setItems([...items, newItem]);  // ✅ Creates new array
```

#### API Client Pattern

**Centralized client**:
```typescript
// lib/api.ts
import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add error interceptor
apiClient.interceptors.response.use(
  response => response,
  error => {
    console.error('API Error:', error);
    return Promise.reject(error);
  }
);

// Feature-specific endpoints
export const getAlerts = async (): Promise<Alert[]> => {
  const response = await apiClient.get<Alert[]>('/api/v1/alerts');
  return response.data;
};

export const resolveAlert = async (id: string): Promise<void> => {
  await apiClient.patch(`/api/v1/alerts/${id}/status`, { status: 'resolved' });
};
```

#### Tools

```bash
# Linting
npm run lint

# Type checking
npm run type-check

# Formatting
npm run format

# Run all checks
npm run lint && npm run type-check
```

---

## Architecture Guidelines

### Backend Layered Architecture

**Never violate layer boundaries**:

```
API Layer (routers)
    ↓ calls
Services Layer
    ↓ calls
Models + Schemas
    ↓ interacts
Database
```

**DO**:
```python
# api/alerts.py (API Layer)
@router.get("/alerts/{id}")
def get_alert(id: str, db: Session = Depends(get_db)):
    alert = alert_service.get_alert_by_id(db, id)  # ✅ Call service
    if not alert:
        raise HTTPException(status_code=404)
    return alert

# services/alert_service.py (Service Layer)
def get_alert_by_id(db: Session, id: str) -> Optional[models.Alert]:
    return db.query(models.Alert).filter(models.Alert.id == id).first()
```

**DON'T**:
```python
# ❌ API layer directly queries database
@router.get("/alerts/{id}")
def get_alert(id: str, db: Session = Depends(get_db)):
    alert = db.query(models.Alert).filter(models.Alert.id == id).first()
    # Business logic in API layer - BAD!
    if alert.risk_score > 80:
        send_email_notification(alert)
    return alert
```

### Frontend Component Organization

```
components/
├── ui/                     # Reusable primitives (no business logic)
│   ├── button.tsx
│   ├── dialog.tsx
│   └── ...
├── [domain]/              # Domain-specific components
│   ├── compliance/
│   └── network/
└── [feature-components]    # Top-level features
    ├── sidebar.tsx
    └── header.tsx
```

**DO**:
```typescript
// components/ui/button.tsx - Generic, reusable
export function Button({ children, ...props }: ButtonProps) {
  return <button {...props}>{children}</button>;
}

// components/compliance/RiskBadge.tsx - Domain-specific
export function RiskBadge({ level }: { level: RiskLevel }) {
  return <Badge variant={getRiskVariant(level)}>{level}</Badge>;
}
```

**DON'T**:
```typescript
// ❌ Business logic in UI component
// components/ui/button.tsx
export function Button({ onClick }: ButtonProps) {
  const handleClick = async () => {
    await saveToDatabase();  // ❌ Business logic in UI primitive
    onClick();
  };
  return <button onClick={handleClick}>Save</button>;
}
```

---

## Git Workflow

### Branch Naming

```
main                    # Production-ready code
develop                 # Integration branch
feature/<name>         # New features
bugfix/<name>          # Bug fixes
hotfix/<name>          # Urgent production fixes
refactor/<name>        # Code refactoring
docs/<name>            # Documentation updates
```

**Examples**:
```
feature/sanctions-screening
bugfix/alert-status-update
hotfix/critical-search-bug
refactor/consolidate-risk-badges
docs/api-endpoint-documentation
```

### Commit Messages

Follow **Conventional Commits**:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code formatting (no logic change)
- `refactor`: Code restructuring (no behavior change)
- `perf`: Performance improvement
- `test`: Adding/updating tests
- `chore`: Maintenance tasks

**Examples**:
```
feat(api): Add sanctions screening endpoint

- Integrate OFAC and EU sanctions lists
- Implement fuzzy name matching with 85% threshold
- Add Redis caching for sanctions data (TTL: 24h)

Closes #123
```

```
fix(frontend): Resolve duplicate RiskBadge imports

Consolidate three separate RiskBadge implementations into
single ui/risk-badge.tsx component. Update all imports.

Fixes #145
```

```
refactor(backend): Extract database queries to service layer

Move query logic from api/alerts.py to services/alert_service.py
to maintain proper layered architecture.

No behavior changes.
```

### Development Workflow

1. **Create feature branch**
   ```bash
   git checkout develop
   git pull upstream develop
   git checkout -b feature/my-feature
   ```

2. **Make changes**
   ```bash
   # Edit files
   git add .
   git commit -m "feat(scope): description"
   ```

3. **Keep branch updated**
   ```bash
   git fetch upstream
   git rebase upstream/develop
   ```

4. **Push to your fork**
   ```bash
   git push origin feature/my-feature
   ```

5. **Create Pull Request** on GitHub

### Commit Best Practices

**DO**:
```bash
# ✅ Small, focused commits
git commit -m "feat(api): Add alert resolution endpoint"
git commit -m "test(api): Add tests for alert resolution"
git commit -m "docs(api): Document alert resolution endpoint"

# ✅ Descriptive messages
git commit -m "fix(frontend): Resolve N+1 query in AlertsList component

Load alerts with eager loading to prevent multiple database
queries. Reduces page load time from 2s to 200ms."
```

**DON'T**:
```bash
# ❌ Vague messages
git commit -m "fix bug"
git commit -m "wip"
git commit -m "update"

# ❌ Massive commits
git commit -m "feat: Complete entire AML Officer feature

- Add 20 new endpoints
- Create 15 new components
- Update 30 files
- Add tests
- Update docs"
```

---

## Testing

### Backend Tests

**Structure**:
```
apps/api/tests/
├── test_api/
│   ├── test_alerts.py
│   └── test_compliance.py
├── test_services/
│   ├── test_rule_engine.py
│   └── test_risk_scoring.py
└── conftest.py  # Pytest fixtures
```

**Example Test**:
```python
# apps/api/tests/test_services/test_rule_engine.py
import pytest
from src.services.rule_engine import RuleEngine

def test_evaluate_simple_condition():
    """Test evaluation of simple equality condition."""
    data = {"amount": 1000, "currency": "USD"}
    condition = {"field": "amount", "operator": "==", "value": 1000}

    result = RuleEngine.evaluate_condition(condition, data)

    assert result is True

def test_evaluate_and_logic():
    """Test evaluation of AND logic group."""
    data = {"amount": 1500, "currency": "USD"}
    conditions = {
        "logic": "AND",
        "conditions": [
            {"field": "amount", "operator": ">", "value": 1000},
            {"field": "currency", "operator": "==", "value": "USD"}
        ]
    }

    result = RuleEngine.evaluate_condition(conditions, data)

    assert result is True

def test_invalid_operator_raises_error():
    """Test that invalid operator raises ValueError."""
    data = {"amount": 1000}
    condition = {"field": "amount", "operator": "invalid", "value": 1000}

    with pytest.raises(ValueError, match="Unsupported operator"):
        RuleEngine.evaluate_condition(condition, data)
```

**Run Tests**:
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_services/test_rule_engine.py

# Run with coverage
pytest --cov=src --cov-report=html

# Run verbose
pytest -v
```

### Frontend Tests

(To be implemented - use Jest + React Testing Library)

```typescript
// __tests__/components/AlertCard.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { AlertCard } from '@/components/AlertCard';

describe('AlertCard', () => {
  it('renders alert title', () => {
    const alert = { id: '1', title: 'Test Alert', description: 'Test' };
    render(<AlertCard alert={alert} />);
    expect(screen.getByText('Test Alert')).toBeInTheDocument();
  });

  it('calls onResolve when button clicked', () => {
    const alert = { id: '1', title: 'Test Alert', description: 'Test' };
    const onResolve = jest.fn();

    render(<AlertCard alert={alert} onResolve={onResolve} />);
    fireEvent.click(screen.getByText('Resolve'));

    expect(onResolve).toHaveBeenCalledWith('1');
  });
});
```

---

## Documentation

### Code Documentation

#### Python Docstrings (Google Style)

```python
def calculate_risk_score(
    transaction: models.Transaction,
    user_profile: models.RiskProfile,
    historical_data: List[models.Transaction]
) -> float:
    """
    Calculate risk score for a transaction.

    Uses weighted scoring across multiple risk factors:
    - Transaction amount relative to user history
    - Geographic risk (sender/receiver countries)
    - Velocity (number of transactions in time window)
    - Network analysis (graph-based risk propagation)

    Args:
        transaction: The transaction to score
        user_profile: User's risk profile and history
        historical_data: Recent transactions for velocity analysis

    Returns:
        Risk score between 0.0 and 100.0

    Raises:
        ValueError: If transaction amount is negative
        InsufficientDataError: If user_profile lacks required fields

    Examples:
        >>> transaction = Transaction(amount=10000, currency="USD")
        >>> profile = RiskProfile(user_id="123", avg_amount=1000)
        >>> calculate_risk_score(transaction, profile, [])
        78.5
    """
    if transaction.amount < 0:
        raise ValueError("Transaction amount cannot be negative")

    # Implementation...
```

#### TypeScript JSDoc

```typescript
/**
 * Fetch alerts from the API with optional filters.
 *
 * @param filters - Optional filters (status, risk_level, date_range)
 * @param page - Page number (1-indexed)
 * @param pageSize - Number of results per page
 * @returns Promise resolving to paginated alerts
 * @throws {APIError} If API request fails
 *
 * @example
 * ```typescript
 * const alerts = await getAlerts({ status: 'open' }, 1, 20);
 * console.log(alerts.results);
 * ```
 */
export async function getAlerts(
  filters?: AlertFilters,
  page: number = 1,
  pageSize: number = 20
): Promise<PaginatedResponse<Alert>> {
  // Implementation...
}
```

### API Documentation

- All endpoints automatically documented in **Swagger UI**: http://localhost:8000/api/docs
- Use Pydantic response models to ensure accurate docs
- Add descriptions to `APIRouter`:

```python
router = APIRouter(
    prefix="/api/v1/alerts",
    tags=["Alerts"],
    responses={404: {"description": "Alert not found"}}
)

@router.get(
    "/{alert_id}",
    response_model=schemas.AlertRead,
    summary="Get alert by ID",
    description="Retrieve a single alert with full details including transaction data and risk assessment."
)
def get_alert(alert_id: str, db: Session = Depends(get_db)):
    """
    Retrieve alert by ID.

    - **alert_id**: UUID of the alert
    """
    # Implementation...
```

---

## Pull Request Process

### Before Submitting

1. **Sync with upstream**
   ```bash
   git fetch upstream
   git rebase upstream/develop
   ```

2. **Run all checks**
   ```bash
   # Backend
   cd apps/api
   pytest
   flake8 src/
   black --check src/
   mypy src/

   # Frontend
   cd apps/web
   npm run lint
   npm run type-check
   ```

3. **Test locally**
   - Manual testing in browser/API
   - Verify no console errors
   - Test on different screen sizes (frontend)

### PR Template

```markdown
## Description
<!-- Brief description of changes -->

## Type of Change
- [ ] Bug fix (non-breaking change fixing an issue)
- [ ] New feature (non-breaking change adding functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Refactoring (no behavior change)
- [ ] Documentation update

## Related Issue
Closes #<issue_number>

## Changes Made
- Change 1
- Change 2
- Change 3

## Testing
<!-- How did you test this? -->
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed

## Screenshots (if applicable)
<!-- Add screenshots for UI changes -->

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review performed
- [ ] Comments added for complex logic
- [ ] Documentation updated
- [ ] No new warnings generated
- [ ] Tests pass locally
- [ ] Dependent changes merged

## Additional Notes
<!-- Any other information for reviewers -->
```

### PR Review Process

1. **Automated Checks** (CI/CD runs linting, tests, type checking)
2. **Code Review** (at least 1 approval required)
3. **QA Review** (for features affecting user-facing functionality)
4. **Merge to `develop`**
5. **Deploy to staging** (automated)
6. **Smoke tests** on staging
7. **Merge to `main`** (for production release)

---

## Code Review Guidelines

### For Authors

- **Keep PRs small** (<400 lines of code when possible)
- **Add context** in PR description
- **Respond promptly** to feedback
- **Don't take feedback personally**
- **Mark resolved comments** after addressing them

### For Reviewers

#### What to Look For

1. **Correctness**: Does the code do what it's supposed to?
2. **Architecture**: Does it follow our layered architecture?
3. **Security**: Any SQL injection, XSS, or other vulnerabilities?
4. **Performance**: Any N+1 queries, unnecessary re-renders, or inefficient algorithms?
5. **Tests**: Are critical paths covered by tests?
6. **Documentation**: Are complex functions documented?
7. **Style**: Does it follow our coding standards?
8. **Error Handling**: Are errors properly caught and logged?

#### Review Comments

**DO**:
```
✅ "Consider using `joinedload()` here to prevent N+1 queries.
Example: query.options(joinedload(Alert.transaction))"

✅ "This looks good! The error handling is comprehensive."

✅ "Minor: Can we extract this 50-line function into smaller helpers
for better readability?"
```

**DON'T**:
```
❌ "This is wrong." (Not helpful - explain why)

❌ "Just use a different approach." (Suggest specific alternative)

❌ "This code is terrible." (Be constructive)
```

#### Approval Criteria

**Approve** if:
- Code is correct and follows standards
- Tests are adequate
- Documentation is sufficient
- Minor issues are noted but don't block merge

**Request Changes** if:
- Critical bugs or security issues
- Architecture violations
- Missing tests for critical paths
- Major style violations

---

## Troubleshooting

### Common Issues

#### Docker Issues

**Problem**: `docker-compose up` fails with "port already in use"
```bash
# Find process using port
lsof -i :8000  # or :3000, :5432, etc.

# Kill process
kill -9 <PID>

# Or use different ports in docker-compose.yml
```

**Problem**: Changes not reflected in container
```bash
# Rebuild containers
docker-compose up --build

# Clear volumes (⚠️ deletes data)
docker-compose down -v
docker-compose up --build
```

#### Backend Issues

**Problem**: `ModuleNotFoundError: No module named 'src'`
```bash
# Ensure you're in backend/ directory
cd apps/api

# Install dependencies
pip install -r requirements.txt

# Run with Python module syntax
python -m src.main
```

**Problem**: Database connection error
```bash
# Check PostgreSQL is running
docker-compose ps

# Check DATABASE_URL in .env
echo $DATABASE_URL

# Run migrations
alembic upgrade head
```

**Problem**: OpenSearch connection refused
```bash
# Check OpenSearch health
curl http://localhost:9200/_cluster/health

# Restart OpenSearch
docker-compose restart opensearch
```

#### Frontend Issues

**Problem**: Module not found
```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

**Problem**: API requests failing (CORS error)
```bash
# Check ALLOWED_ORIGINS in backend .env
# Must include http://localhost:3000

# Verify NEXT_PUBLIC_API_URL in frontend .env.local
```

**Problem**: Type errors
```bash
# Regenerate type definitions (if using OpenAPI generator)
npm run generate-types

# Check TypeScript version
npm list typescript
```

---

## Getting Help

- **Documentation**: See [ARCHITECTURE.md](./ARCHITECTURE.md) for system overview
- **GitHub Issues**: Open an issue for bugs or feature requests
- **Discussions**: Use GitHub Discussions for questions
- **Slack/Discord**: [Link to team communication channel if available]

---

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (see [LICENSE](./LICENSE)).

---

**Thank you for contributing to Yufeed!** 🎉
