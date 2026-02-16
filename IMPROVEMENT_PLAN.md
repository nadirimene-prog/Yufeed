# Yufeed Improvement Implementation Plan

**Based on findings from 2026-02-16 Audit**

---

## Phase 1: Critical Fixes (P1) - Day 1

### 1.1 Fix Broken Script Reference

**File**: `apps/api/scripts/verify_monitoring.py`

**Issue**: References non-existent `rule_engine.py`

**Fix Options**:
- **Option A**: Update script to use `RulesEngine` from `rules_engine.py`
- **Option B**: Remove the script if no longer needed

**Recommended Fix (Option A)**:
```python
# Change line 8 from:
from src.services.rule_engine import RuleEngine
# To:
from src.services.rules_engine import RulesEngine

# Update usage accordingly
```

---

### 1.2 Fix Test Failures

#### Test 1: `test_api_versioning.py`

**Issue**: API root returns different format than expected

**Check**: `src/api/auth.py:162-188` vs test expectations

#### Test 2: `test_auth.py` failures

**Issue**: Database state conflicts between tests

**Fix**: Add proper test isolation with `transaction=True` fixture or use `pytest-asyncio` cleanup.

```python
# In conftest.py, ensure:
@pytest.fixture(autouse=True)
async def cleanup_db():
    yield
    # Clean up test data after each test
```

#### Test 3: `test_transactions_api.py`

**Issue**: `RuntimeError` in tenant middleware

**Investigation needed**: Check `src/tenancy/middleware.py:89`

---

### 1.3 Add Missing Dependency

**Already done during audit**, but verify:

```bash
cd apps/api
pip install numpy pandas scikit-learn
pip freeze | grep -E "numpy|pandas|scikit" >> requirements.txt
```

---

## Phase 2: Documentation (P2) - Day 2

### 2.1 Update Architecture Documentation

**File**: `docs/architecture/architecture.md`

**Sections to update**:

#### Remove/Update "Known Issues & Technical Debt"

Current (lines 1049-1095) lists resolved issues:

```markdown
### Critical (P0)
1. ~~Missing `re` import~~ ✅ FIXED
2. ~~No database connection error handling~~ ✅ FIXED (has connection pooling)
3. ~~CORS validation missing~~ ✅ FIXED (configured in main.py)

### High Priority (P1)
4. ~~Duplicate rule engines~~ ✅ FIXED (only rules_engine.py exists)
5. ~~Duplicate RiskBadge components~~ VERIFY (may be resolved)
6. ~~Mixed Pydantic v1/v2~~ ✅ FIXED (using from_attributes everywhere)
7. ~~Print statements~~ ✅ FIXED (using structlog)
8. ~~Missing database indexes~~ ✅ FIXED (256+ index operations)
9. ~~No authentication~~ ✅ FIXED (full JWT auth implemented)

### Medium Priority (P2)
10. ~~Type safety issues~~ ✅ FIXED (TypeScript strict mode, 0 errors)
11. ~~Missing error boundaries~~ ✅ FIXED (implemented)
12. Mock data in production code - VERIFY
...
```

### 2.2 Add OpenAPI Security Documentation

**File**: `apps/api/src/main.py`

**Add after line 88**:

```python
from fastapi.security import OAuth2PasswordBearer

# OAuth2 scheme for Swagger UI
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/token",
    scopes={
        "read": "Read access",
        "write": "Write access",
        "admin": "Admin access"
    }
)

# Update FastAPI initialization
app = FastAPI(
    title="EU Legal Monitoring MVP",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
    # Add security scheme
    security=[{"bearerAuth": []}],
)

# Add security scheme to OpenAPI schema
@app.on_event("startup")
async def add_security_scheme():
    if app.openapi_schema:
        app.openapi_schema["components"]["securitySchemes"] = {
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT"
            }
        }
```

**Alternative**: Add to each protected router:

```python
# In router files (e.g., api/alerts.py)
from fastapi import Depends
from src.auth.dependencies import get_current_user

router = APIRouter(
    prefix="/api/alerts",
    tags=["Alerts"],
    dependencies=[Depends(get_current_user)],  # Already there
    # Add for Swagger documentation:
    # responses={401: {"description": "Unauthorized"}}
)
```

---

## Phase 3: Code Quality (P3) - Day 3

### 3.1 Consolidate Error Boundaries (Optional)

**Current State**:
- `error-boundary.tsx`: Full-page error UI
- `ErrorBoundary.tsx`: Section-level error UI

**Decision**: Keep both - they serve different purposes.

**Action**: Just add documentation comments explaining when to use each:

```typescript
// error-boundary.tsx - Add header comment:
/**
 * FULL-PAGE ERROR BOUNDARY
 * Use this at the top level of your application (e.g., in layout.tsx)
 * Provides full-page error UI with home navigation.
 */

// ErrorBoundary.tsx - Add header comment:
/**
 * SECTION ERROR BOUNDARY
 * Use this to wrap specific feature sections.
 * Supports custom fallback UI and error callbacks.
 * Example: <ErrorBoundary fallback={<CustomError />}><Feature /></ErrorBoundary>
 */
```

### 3.2 Add More Frontend Tests

**Current**: 61 tests covering utilities  
**Gap**: No component-level tests

**Add**: Create `apps/web/src/components/__tests__/error-boundary.test.tsx`

```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { ErrorBoundary } from '../error-boundary';

// Test component that throws
const ThrowError = ({ shouldThrow }: { shouldThrow: boolean }) => {
  if (shouldThrow) throw new Error('Test error');
  return <div>No error</div>;
};

describe('ErrorBoundary', () => {
  it('renders children when no error', () => {
    render(
      <ErrorBoundary>
        <div>Test content</div>
      </ErrorBoundary>
    );
    expect(screen.getByText('Test content')).toBeInTheDocument();
  });

  it('renders error UI when error occurs', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
  });
});
```

---

## Phase 4: Testing Infrastructure (Ongoing)

### 4.1 Improve Test Isolation

**File**: `apps/api/tests/conftest.py`

**Add**:
```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database import Base

# Use SQLite in-memory for unit tests
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    yield session
    
    session.close()
    Base.metadata.drop_all(bind=engine)
```

### 4.2 Mock External Services

**File**: `apps/api/tests/conftest.py`

**Add**:
```python
import pytest
from unittest.mock import Mock, patch

@pytest.fixture
def mock_anthropic():
    """Mock Anthropic API calls."""
    with patch('src.ai.client.Anthropic') as mock:
        mock.return_value.messages.create.return_value = Mock(
            content=[Mock(text='{"result": "mocked"}')]
        )
        yield mock

@pytest.fixture
def mock_email_service():
    """Mock email sending."""
    with patch('src.services.email.EmailService') as mock:
        mock.send_email.return_value = True
        yield mock
```

---

## Implementation Checklist

### Day 1: Critical Fixes
- [ ] Fix `scripts/verify_monitoring.py` import
- [ ] Fix `test_api_versioning.py` assertions
- [ ] Fix `test_auth.py` database isolation
- [ ] Fix `test_transactions_api.py` tenant middleware issue
- [ ] Verify `numpy` in requirements.txt

### Day 2: Documentation
- [ ] Update architecture.md "Known Issues" section
- [ ] Add OpenAPI security scheme to main.py
- [ ] Verify all protected endpoints show lock icon in Swagger
- [ ] Update test coverage statistics in docs

### Day 3: Quality
- [ ] Add JSDoc comments to error boundaries
- [ ] Create component test examples
- [ ] Add test isolation fixtures
- [ ] Add external service mocks

### Day 4: Verification
- [ ] Run full test suite: `pytest --cov=src`
- [ ] Run frontend tests: `npm test`
- [ ] Run type-check: `npm run type-check`
- [ ] Verify Swagger UI shows auth requirements
- [ ] Update AUDIT_FINDINGS.md with completion status

---

## Verification Commands

```bash
# Backend tests
cd apps/api
.venv/bin/python -m pytest --cov=src --cov-report=term

# Frontend tests
cd apps/web
npm test

# Type checking
npm run type-check

# Integration test (manual)
docker-compose up -d
pytest tests/integration/

# Security verification
curl http://localhost:8000/api/protected-endpoint
# Should return 401 without token
```

---

## Success Criteria

- [ ] All tests pass (or failures documented as expected)
- [ ] Test coverage remains above 80%
- [ ] TypeScript type-check passes with 0 errors
- [ ] Swagger UI shows authentication requirements
- [ ] Architecture documentation is accurate
- [ ] No broken script references

---

*Plan created: 2026-02-16*
*Estimated duration: 3-4 days*
